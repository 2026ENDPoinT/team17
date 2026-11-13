"""공지별 추출 결과를 장학금 이벤트로 묶어 화면용 events.json을 만든다 (최종 빌드).

실행: uv run python events/build.py [--out 경로] [--extracted 폴더 --no-review]  (뒤 두 개는 시험 데이터용)
입력: data/extracted/{bidx}.json (분류 담당), data/reviewed/{bidx}.json (공지별 검수값),
      data/reviewed/events.json (묶음 검수: 라벨 고치기, 묶기, 떼기)
출력: web/public/events.json (형식: data/events.sample.json). 항목 1개 = 장학금 이벤트 1개.

- 이벤트의 상세 값(금액·조건·서류 등)은 가장 최근 모집·수정 공지 것을 쓰고, 빈 값만 앞 공지로 채운다.
- 마감일은 마감일이 있는 가장 최근 모집·수정 공지 것, 상태(status)는 마지막 공지의 라벨이다.
- 크롤러가 duplicate_of를 붙인 글은 대표 글과 같은 글로 보고, 대표 글의 also_posted_bidx에 번호만 남긴다.
- 안전장치: 묶기가 실패하면 공지 1건 = 이벤트 1개로 그대로 내보낸다 (grouped_by: "single").
"""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from group import group_notices, has_details, notice_label

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "data" / "extracted"
REVIEWED_DIR = ROOT / "data" / "reviewed"
EVENT_REVIEW = REVIEWED_DIR / "events.json"
OUT = ROOT / "web" / "public" / "events.json"
KST = timezone(timedelta(hours=9))

# 화면에 넘기지 않는 필드. 앞줄은 분류 쪽 내부 필드로 classifier/build.py의 INTERNAL_KEYS와 같게 둔다
# (분류가 내부 필드를 늘리면 여기도 늘린다). 뒷줄은 묶기에만 쓰는 필드다.
INTERNAL_KEYS = ["notice_kind", "notice_kind_reason", "content_hash", "exclude", "filtered_conditions", "duplicate_of",
                 "from_attachment", "duplicate_split", "label", "label_reason",
                 "year", "semester", "round", "_label"]
# 최근 공지에 값이 없으면 앞 공지 값으로 채우는 필드
FILL_FIELDS = ["category", "summary", "amount", "eligibility", "burden", "duplicate_restriction"]


def merge(base: dict, patch: dict) -> dict:
    """patch의 값으로 base를 덮어쓴다. 둘 다 dict인 필드는 안쪽까지 합친다. '_'로 시작하는 키는 메모라 무시한다."""
    result = dict(base)
    for key, value in patch.items():
        if key.startswith("_"):
            continue
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = value
    return result


def load_notices(extracted_dir: Path = EXTRACTED_DIR, reviewed_dir: Path | None = REVIEWED_DIR) -> list[dict]:
    """extracted에 공지별 검수값을 덮어쓰고, 제외된 글을 빼고, 재게시 글을 대표 글에 붙인다.
    reviewed_dir가 None이면 검수값을 쓰지 않는다 (시험 데이터용)."""
    merged: dict[str, dict] = {}
    for path in sorted(extracted_dir.glob("*.json")):
        item = json.loads(path.read_text(encoding="utf-8"))
        reviewed_path = reviewed_dir / path.name if reviewed_dir else None
        if reviewed_path and reviewed_path.exists():
            item = merge(item, json.loads(reviewed_path.read_text(encoding="utf-8")))
            item["reviewed"] = True
        if not item.get("exclude"):
            merged[str(item["id"])] = item

    for item in merged.values():
        item["also_posted_bidx"] = []
    notices = []
    for item in merged.values():
        rep = merged.get(str(item.get("duplicate_of") or ""))
        if rep is not None and rep is not item:
            rep["also_posted_bidx"].append(str(item["id"]))
        else:
            notices.append(item)
    return notices


def load_event_review(path: Path | None = EVENT_REVIEW) -> dict:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def apply_review(groups: list[list[dict]], review: dict) -> tuple[list[list[dict]], set[int]]:
    """묶음 검수를 적용한다. split: 그 공지를 혼자 이벤트로 뗀다. merge: 적힌 공지들이 든 이벤트를 하나로 합친다.
    반환: (새 묶음, 검수로 바뀐 묶음의 번호)"""
    split = {str(b) for b in review.get("split", [])}
    result: list[list[dict]] = []
    for g in groups:
        rest = [n for n in g if str(n["id"]) not in split]
        result += [[n] for n in g if str(n["id"]) in split]
        if rest:
            result.append(rest)
    touched_ids: set[str] = set(split)

    for wanted in review.get("merge", []):
        wanted = {str(b) for b in wanted}
        hit = [g for g in result if any(str(n["id"]) in wanted for n in g)]
        if len(hit) < 2:
            continue
        result = [g for g in result if not any(g is h for h in hit)]
        result.append([n for g in hit for n in g])
        touched_ids |= wanted
    touched = {i for i, g in enumerate(result) if any(str(n["id"]) in touched_ids for n in g)}
    return result, touched


def _empty(field: str, value) -> bool:
    if value is None:
        return True
    return field == "amount" and isinstance(value, dict) and value.get("value") is None


def make_event(notices: list[dict], grouped_by: str) -> dict | None:
    """공지 묶음 하나 → 이벤트 하나. 상세가 있는 공지(모집·수정, 마감된 모집)가 없으면(결과 공지만 있으면) None."""
    notices = sorted(notices, key=lambda n: (n["source"].get("posted_at") or "", int(n["id"])))
    active = [n for n in notices if has_details(n)]
    if not active:
        return None
    latest = active[-1]
    detail = dict(latest)
    filled = set()
    for field in FILL_FIELDS:
        if _empty(field, detail.get(field)):
            for n in reversed(active[:-1]):
                if not _empty(field, n.get(field)):
                    detail[field] = n[field]
                    filled.add(field)
                    break

    # 마감일: 마감일이 있는 가장 최근 모집·수정 공지. 게시일보다 앞선 마감일은 잘못 뽑은 값이라 건너뛴다
    with_deadline = [n for n in active if n.get("deadline") and n["deadline"] >= (n["source"].get("posted_at") or "")]
    bad_deadline = len(with_deadline) < sum(1 for n in active if n.get("deadline"))
    if with_deadline:
        d = with_deadline[-1]
        detail["deadline"], detail["deadline_text"] = d["deadline"], d.get("deadline_text")
        detail["evidence"] = dict(detail.get("evidence") or {}, deadline=(d.get("evidence") or {}).get("deadline"))
        if d is not latest:
            filled.add("deadline")
    elif bad_deadline:
        detail["deadline"] = None  # 마감일 문장(deadline_text)은 남겨 사람이 보게 한다

    status = notices[-1]["_label"]
    detail["closed"] = status == "완료" or bool(latest.get("closed"))
    detail["needs_check"] = [c for c in latest.get("needs_check", []) if c not in filled]
    if bad_deadline and "deadline" not in detail["needs_check"]:
        detail["needs_check"].append("deadline")
    detail["also_posted_bidx"] = [b for n in notices for b in n.get("also_posted_bidx", [])]
    detail["reviewed"] = any(n.get("reviewed") for n in notices)
    for key in INTERNAL_KEYS + ["id"]:
        detail.pop(key, None)

    return {
        "id": f"event-{notices[0]['id']}",
        "status": status,
        "grouped_by": grouped_by,
        "notices": [
            {
                "bidx": str(n["id"]),
                "label": n["_label"],
                "title": n.get("title"),
                "board": n["source"].get("board"),
                "url": n["source"].get("url"),
                "posted_at": n["source"].get("posted_at"),
                "also_posted_bidx": n.get("also_posted_bidx", []),
            }
            for n in notices
        ],
        **detail,
    }


def single_events(notices: list[dict]) -> list[dict]:
    """안전장치: 묶지 않고 공지 1건 = 이벤트 1개."""
    return [e for e in (make_event([n], "single") for n in notices) if e is not None]


def build_events(notices: list[dict], review: dict) -> list[dict]:
    labels = {str(k): v for k, v in review.get("labels", {}).items()}
    labeled = []
    for n in notices:
        n["_label"] = labels[str(n["id"])] if str(n["id"]) in labels else notice_label(n)
        if n["_label"] in ("모집", "수정", "완료"):
            labeled.append(n)

    try:
        groups = group_notices(labeled)
        groups, touched = apply_review(groups, review)
    except Exception as e:  # 묶기 규칙이 깨져도 데모 화면은 나와야 한다
        print(f"경고: 이벤트 묶기 실패 → 공지 1건 = 이벤트 1개로 내보냄 ({e!r})", file=sys.stderr)
        return single_events(labeled)

    events = []
    for i, g in enumerate(groups):
        grouped_by = "reviewed" if i in touched else ("auto" if len(g) > 1 else "single")
        try:
            event = make_event(g, grouped_by)
        except Exception as e:
            print(f"경고: 이벤트 만들기 실패 {[n['id'] for n in g]} → 공지별로 내보냄 ({e!r})", file=sys.stderr)
            events += single_events(g)
            continue
        if event is not None:
            events.append(event)
    events.sort(key=lambda e: (e["notices"][0]["posted_at"] or "", int(e["notices"][0]["bidx"])))
    return events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--extracted", type=Path, default=EXTRACTED_DIR, help="입력 추출 결과 폴더 (시험 데이터용)")
    parser.add_argument("--no-review", action="store_true", help="data/reviewed/의 검수값을 쓰지 않는다 (시험 데이터용)")
    args = parser.parse_args()

    if args.no_review:
        events = build_events(load_notices(args.extracted, None), {})
    else:
        events = build_events(load_notices(args.extracted), load_event_review())
    data = {
        "version": 1,
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "items": events,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    grouped = sum(1 for e in events if len(e["notices"]) > 1)
    print(f"이벤트 {len(events)}개 (공지 2건 이상 묶인 것 {grouped}개) → {args.out}")


if __name__ == "__main__":
    main()
