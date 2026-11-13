"""검수할 공지 목록을 만든다. 사람이 data/reviewed/{bidx}.json을 쓸 때 보는 체크리스트다.

입력: web/public/events.json (이벤트 묶기 결과), data/extracted/{bidx}.json, data/raw/{bidx}.json
출력: data/reviewed/CHECKLIST.md (빌드는 .json만 읽으므로 이 파일은 결과에 영향이 없다)

대상: 완료되지 않은 이벤트 중 needs_check가 있는 것. 이벤트의 값은 가장 최근 모집·수정 공지에서 오므로
그 공지의 bidx로 검수 파일을 만든다.
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS = ROOT / "web" / "public" / "events.json"
EXTRACTED_DIR = ROOT / "data" / "extracted"
RAW_DIR = ROOT / "data" / "raw"
OUT = ROOT / "data" / "reviewed" / "CHECKLIST.md"

REASONS = {
    "poster_only": "본문 없이 포스터 이미지만 있음 → 이미지를 보고 금액·마감·조건을 채운다",
    "body_short": "본문이 100자 미만 → 첨부·이미지를 확인한다",
    "amount": "금액을 못 찾음",
    "deadline": "마감일을 못 찾았거나 고친 값",
    "documents": "제출서류를 못 찾음",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def target_bidx(event: dict) -> str:
    """이벤트 값이 나온 공지: 완료가 아닌 가장 최근 공지 (없으면 마지막 공지)."""
    notices = event["notices"]
    active = [n for n in notices if n.get("label") != "완료"]
    return str((active or notices)[-1]["bidx"])


def template(event: dict) -> dict:
    """검수 파일 뼈대. 확인한 값만 남기고 나머지 줄은 지운다."""
    t: dict = {"_comment": "검수자 이름 · 무엇을 보고 고쳤는지"}
    checks = event.get("needs_check") or []
    if "amount" in checks or "poster_only" in checks or event["amount"]["value"] is None:
        t["amount"] = {"type": "lump_sum | tuition_ratio | hourly", "value": 0, "text": "원문 표기"}
    if "deadline" in checks or event.get("deadline") is None:
        t["deadline"] = "YYYY-MM-DD"
    if "documents" in checks:
        t["burden"] = {"documents": ["서류 이름"]}
    t["needs_check"] = []
    return t


def item_md(no: int, event: dict) -> str:
    bidx = target_bidx(event)
    ext = _load(EXTRACTED_DIR / f"{bidx}.json")
    raw = _load(RAW_DIR / f"{bidx}.json")
    checks = event.get("needs_check") or []
    amount = event["amount"]
    lines = [
        f"### {no}. {event['name']}",
        "",
        f"- [ ] 검수 파일: `data/reviewed/{bidx}.json`",
        f"- 원문: {event['source']['url']}",
        f"- 상태: {event['status']} · 분류: {event['category']} · 게시: {event['source']['posted_at']}",
        f"- 확인할 것: {', '.join(f'`{c}`' for c in checks)}",
    ]
    lines += [f"  - `{c}`: {REASONS.get(c, '')}" for c in checks]
    lines.append(f"- 지금 값: 금액 `{amount['text'] or amount['value'] or '없음'}` · "
                 f"마감 `{event.get('deadline') or '없음'}` · "
                 f"서류 {len(event['burden'].get('documents') or [])}개")
    evidence = event.get("evidence") or {}
    if event.get("deadline_text"):
        lines.append(f"- 마감 근거: {event['deadline_text']}")
    if evidence.get("amount"):
        lines.append(f"- 금액 근거: {evidence['amount']}")
    if ext.get("from_attachment"):
        lines.append(f"- 첨부에서 채운 값: {', '.join(ext['from_attachment'])} (첨부 원문과 맞는지 먼저 본다)")
    files = [a.get("name", "") for a in raw.get("attachments") or []]
    if files:
        lines.append(f"- 첨부: {' / '.join(files)}")
    if raw.get("has_images"):
        lines.append("- 본문에 이미지 있음")
    lines += ["", "```json", json.dumps(template(event), ensure_ascii=False, indent=2), "```", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    events = _load(EVENTS).get("items", [])
    todo = [e for e in events if e["status"] != "완료" and e.get("needs_check") and not e.get("reviewed")]
    # 데모에서 보일 순서: 마감이 늦은 것(아직 모집 중일 가능성이 큰 것) 먼저, 마감 없는 것은 맨 앞
    todo.sort(key=lambda e: e.get("deadline") or "9999", reverse=True)

    head = [
        "# 검수 체크리스트",
        "",
        "`uv run python classifier/review_list.py`로 다시 만든다. 직접 고치지 않는다 (체크 표시는 검수 파일이 생기면 목록에서 빠진다).",
        "",
        "**검수 방법**",
        "",
        "1. 원문 링크를 열어 포스터·첨부를 확인한다.",
        "2. 아래 JSON 뼈대를 `data/reviewed/{bidx}.json`으로 저장하고, **확인한 값만 남긴다.** 모르는 값은 줄째 지운다.",
        "3. `\"needs_check\": []`를 꼭 남긴다. 남아 있으면 화면이 그 장학금을 필터에서 뺀다.",
        "4. 장학금 모집이 아니면 내용 대신 `{\"exclude\": true}`만 적는다.",
        "5. `uv run python events/build.py`로 화면용 파일을 다시 만든다.",
        "",
        "금액 유형: `lump_sum`(원) / `tuition_ratio`(등록금 %) / `hourly`(시급 원). 같은 유형끼리만 금액순으로 비교된다.",
        "",
        f"대상 {len(todo)}건 (완료되지 않은 이벤트 중 확인 필요가 있고 아직 검수하지 않은 것)",
        "",
    ]
    body = [item_md(i, e) for i, e in enumerate(todo, 1)]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(head + body), encoding="utf-8")
    print(f"검수 대상 {len(todo)}건 → {args.out}")


if __name__ == "__main__":
    main()
