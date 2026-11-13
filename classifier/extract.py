"""data/raw/{bidx}.json을 읽어 규칙으로 분류·추출하고 data/extracted/{bidx}.json에 쓴다.

실행: uv run python classifier/extract.py
입력 형식: data/raw/_sample.json / 출력 형식: data/scholarships.sample.json의 items 한 건 + 분류용 필드
"""

import json
from datetime import date

from config import EXTRACTED_DIR, RAW_DIR
from rules import (
    classify_category,
    classify_kind,
    extract_amount,
    extract_deadline,
    extract_documents,
    extract_duplicate_restriction,
    extract_eligibility,
    extract_name,
    has_interview,
    is_closed,
    make_summary,
)


def extract_one(raw: dict) -> dict:
    """공지 원본 1건 → 추출 결과 1건."""
    title = raw["title"]
    body = raw.get("body_text") or ""
    posted = date.fromisoformat(raw["posted_date"])

    kind, kind_reason = classify_kind(title)
    amount, amount_evidence = extract_amount(body)
    deadline, deadline_text, deadline_evidence = extract_deadline(title, body, posted)
    duplicate, duplicate_evidence = extract_duplicate_restriction(body)
    eligibility = extract_eligibility(body)
    documents = extract_documents(body)

    # 사람이 꼭 확인해야 하는 항목. 화면에서 "확인 필요"로 보여 줄 수 있다.
    needs_check = []
    if amount["type"] == "unknown":
        needs_check.append("amount")
    if deadline is None and deadline_text is None:  # 상시 모집은 deadline_text만 있다
        needs_check.append("deadline")
    if not documents:
        needs_check.append("documents")
    if len(body.strip()) < 100:
        needs_check.append("poster_only" if raw.get("has_images") else "body_short")

    return {
        "id": str(raw["bidx"]),
        "notice_kind": kind,  # 모집 / 결과 / 안내 / 확인필요. 빌드할 때 '모집'만 남긴다
        "notice_kind_reason": kind_reason,
        "name": extract_name(title),
        "title": title,
        "category": classify_category(title, raw.get("bnum", 0)),
        "summary": make_summary(body, raw.get("has_images", False), len(raw.get("attachments", []))),
        "amount": amount,
        "deadline": deadline,
        "deadline_text": deadline_text,
        "closed": is_closed(title),
        "eligibility": eligibility,
        "burden": {"documents": documents, "interview": has_interview(body)},
        "duplicate_restriction": duplicate,
        "source": {"board": raw.get("board"), "url": raw["url"], "posted_at": raw["posted_date"]},
        "also_posted_bidx": [],  # 학과 재게시 묶기는 아직 정하지 않음 (crawler/README.md "정하지 않은 것")
        "evidence": {
            "amount": amount_evidence,
            "deadline": deadline_evidence,
            "duplicate_restriction": duplicate_evidence,
        },
        "needs_check": needs_check,
        "content_hash": raw.get("content_hash"),  # 원본이 바뀌었는지 비교용
        "reviewed": False,
    }


def main() -> None:
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for path in sorted(RAW_DIR.glob("*.json")):
        if path.name.startswith("_"):  # _sample.json 등은 건너뛴다
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("_sample"):
            continue
        item = extract_one(raw)
        out = EXTRACTED_DIR / f"{item['id']}.json"
        out.write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        counts[item["notice_kind"]] = counts.get(item["notice_kind"], 0) + 1
    total = sum(counts.values())
    summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
    print(f"{total}건 추출 → {EXTRACTED_DIR.relative_to(EXTRACTED_DIR.parents[1])} ({summary})")


if __name__ == "__main__":
    main()
