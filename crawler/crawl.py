"""장학금 공지 수집 실행 파일. 입력: config.BOARDS의 게시판 / 출력: data/raw/{bidx}.json (글 1건 = 파일 1개)

사용법 (저장소 루트에서)
  uv run python crawler/crawl.py --mode offline   # 저장된 HTML만 사용 (개발·테스트, 학교 서버 요청 없음)
  uv run python crawler/crawl.py --mode record    # 학교 서버에서 받고 HTML도 crawler/fixtures/에 저장
  uv run python crawler/crawl.py --mode live      # 학교 서버에서 받기만

흐름: 목록 ?page=N 읽기 → 제목 키워드로 거르기 → 처음 보는 bidx거나 최근 글이면 상세 읽기 → 개인정보 지우기 → 저장
      → 첨부 텍스트 뽑기(아직 안 뽑은 첨부만) → data/raw 전체에서 재게시 묶기(duplicate_of 표시)
"""

import argparse
import datetime
import hashlib
import json
import sys

import attachments
import dedup
import fetch
import privacy
from config import BOARDS, KEYWORDS, MAX_PAGES, RAW_DIR, RECHECK_DAYS, SINCE_DAYS
from parse import parse_detail, parse_list

KST = datetime.timezone(datetime.timedelta(hours=9))


def content_hash(title: str, body_text: str) -> str:
    return "sha256:" + hashlib.sha256((title + "\n" + body_text).encode("utf-8")).hexdigest()


def list_board(board: dict, mode: str, since: str) -> list[dict]:
    """목록을 page=1부터 읽어 since 이후 글을 모은다. 고정 공지가 아닌 글이 모두 since보다 오래되면 멈춘다."""
    found: dict[int, dict] = {}
    for page in range(1, MAX_PAGES + 1):
        url = f"{board['url']}?page={page}"
        try:
            rows = parse_list(fetch.get(url, mode), board["url"])
        except fetch.FixtureMissing:
            print(f"  fixture 없음, 목록 중단: {url}")
            break
        if not rows:
            break
        for r in rows:
            if r["posted_date"] and r["posted_date"] >= since:
                found.setdefault(r["bidx"], r)
        normal = [r for r in rows if not r["pinned"] and r["posted_date"]]
        if normal and all(r["posted_date"] < since for r in normal):
            break
    return list(found.values())


def matched(title: str, board: dict) -> list[str]:
    return [k for k in board.get("keywords", KEYWORDS) if k in title]


def build_record(board: dict, row: dict, detail: dict, old: dict | None, now: str) -> dict:
    title = privacy.scrub(detail["title"] or row["title"])
    body = privacy.scrub(detail["body_text"])
    return {
        "bidx": row["bidx"],
        "bnum": row["bnum"],
        "site": board["site"],
        "board": board["board"],
        "url": row["url"],
        "title": title,
        "posted_date": detail["posted_date"] or row["posted_date"],
        "pinned": row["pinned"],
        "duplicate_of": old.get("duplicate_of") if old else None,  # mark_duplicates()가 채운다
        "matched_keywords": matched(title, board),
        "body_text": body,
        "has_images": detail["has_images"],
        "attachments": detail["attachments"],
        "content_hash": content_hash(title, body),
        "first_seen": old["first_seen"] if old else now,
        "last_checked": now,
    }


def fill_attachments(mode: str):
    """data/raw 전체에서 text_status가 not_extracted인 첨부만 받아 텍스트를 채운다."""
    counts: dict[str, int] = {}
    for path in sorted(RAW_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        rec = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for att in rec["attachments"]:
            if att["text_status"] != "not_extracted":
                continue
            if attachments.is_result_notice(rec["title"]):
                status, text = "skipped_result", None
            else:
                status, text = attachments.extract(att["url"], att["ext"], mode)
            counts[status] = counts.get(status, 0) + 1
            if status != "not_extracted":
                att["text_status"], att["text"] = status, text
                changed = True
        if changed:
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("첨부 추출:", counts or "새로 뽑을 첨부 없음")


def mark_duplicates():
    """data/raw 전체를 다시 보고 duplicate_of를 채운다. 값이 바뀐 파일만 다시 쓴다."""
    paths = [p for p in RAW_DIR.glob("*.json") if not p.name.startswith("_")]
    records = {p: json.loads(p.read_text(encoding="utf-8")) for p in paths}
    result = dedup.assign_duplicates(list(records.values()))
    changed = 0
    for p, rec in records.items():
        new = result[rec["bidx"]]
        if "duplicate_of" not in rec or rec["duplicate_of"] != new:
            rec["duplicate_of"] = new
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
            changed += 1
    dups = sum(1 for v in result.values() if v is not None)
    print(f"재게시 묶기: 재게시 {dups}건, 표시가 바뀐 파일 {changed}개")


def run(mode: str) -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.date.today()
    since = (today - datetime.timedelta(days=SINCE_DAYS)).isoformat()
    recheck_since = (today - datetime.timedelta(days=RECHECK_DAYS)).isoformat()
    now = datetime.datetime.now(KST).replace(microsecond=0).isoformat()
    counts = {"new": 0, "changed": 0, "same": 0, "skipped": 0, "mirror": 0, "error": 0}
    seen: set[int] = set()  # 이번 실행에서 처리한 bidx (미러 게시판은 같은 bidx를 쓴다)

    for board in BOARDS:
        rows = list_board(board, mode, since)
        if board["filter_keywords"]:
            rows = [r for r in rows if matched(r["title"], board)]
        print(f"[{board['site']} {board['board']}] 대상 {len(rows)}건")

        for row in sorted(rows, key=lambda r: r["bidx"]):
            if row["bidx"] in seen:
                counts["mirror"] += 1  # 먼저 나온 게시판(BOARDS 순서) 것을 쓴다
                continue
            seen.add(row["bidx"])
            path = RAW_DIR / f"{row['bidx']}.json"
            old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            if old and (row["posted_date"] or "") < recheck_since:
                counts["skipped"] += 1  # 오래된 글은 다시 읽지 않는다
                continue
            try:
                detail = parse_detail(fetch.get(row["url"], mode), row["url"])
            except fetch.FixtureMissing:
                counts["skipped"] += 1
                continue
            except Exception as e:  # 한 글 실패로 전체를 멈추지 않는다
                print(f"  실패 {row['bidx']}: {e}")
                counts["error"] += 1
                continue
            if not detail["found_body"]:
                print(f"  본문 위치를 못 찾음 {row['bidx']}: {row['url']}")
            rec = build_record(board, row, detail, old, now)
            if old and old["content_hash"] == rec["content_hash"]:
                counts["same"] += 1
                old["last_checked"] = now
                rec = old
            else:
                counts["changed" if old else "new"] += 1
                if old:
                    print(f"  수정됨 {row['bidx']}: {old['title']} → {rec['title']}")
            path.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print("결과:", counts)
    fill_attachments(mode)
    mark_duplicates()
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="교내 게시판 장학금 공지 수집")
    ap.add_argument("--mode", choices=["offline", "record", "live"], default="offline")
    sys.exit(run(ap.parse_args().mode))
