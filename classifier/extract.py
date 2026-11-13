"""data/raw/{bidx}.json을 읽어 규칙으로 분류·추출하고 data/extracted/{bidx}.json에 쓴다.

실행: uv run python classifier/extract.py
입력 형식: data/raw/_sample.json (본문 body_text + 첨부 attachments[].text) / 출력 형식: data/scholarships.sample.json의 items 한 건 + 분류용 필드
"""

import json
from datetime import date

from config import EXTRACTED_DIR, RAW_DIR
from rules import (
    classify_category,
    classify_kind,
    extract_amount,
    extract_deadline,
    extract_departments,
    extract_documents,
    extract_duplicate_restriction,
    extract_eligibility,
    extract_name,
    extract_other_conditions,
    extract_residence,
    has_interview,
    is_closed,
    is_form_attachment,
    is_ignored_attachment,
    make_summary,
    prepare_attachment_text,
)


def attachment_texts(raw: dict) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """텍스트를 뽑은 첨부를 (공고문, 양식)으로 나눈다. 각 항목은 (파일 이름, 다듬은 텍스트)."""
    notices: list[tuple[str, str]] = []
    forms: list[tuple[str, str]] = []
    for att in raw.get("attachments", []):
        if att.get("text_status") != "ok" or not att.get("text") or is_ignored_attachment(att["name"]):
            continue
        item = (att["name"], prepare_attachment_text(att["text"]))
        (forms if is_form_attachment(att["name"]) else notices).append(item)
    return notices, forms


def tag_source(evidence: str | None, source: str | None) -> str | None:
    """첨부에서 찾은 값의 근거 문장 앞에 '[첨부: 파일 이름]'을 붙인다."""
    if evidence is None or source is None:
        return evidence
    return f"[첨부: {source}] {evidence}"


def extract_one(raw: dict) -> dict:
    """공지 원본 1건 → 추출 결과 1건.

    본문을 먼저 읽고, 본문에서 못 찾은 값만 첨부 공고문에서 찾는다 (연장 공지처럼 본문이 더 최신일 수 있다).
    신청서 양식 첨부는 빈칸이 많아서 제출서류 목록에만 쓴다.
    """
    title = raw["title"]
    body = raw.get("body_text") or ""
    posted = date.fromisoformat(raw["posted_date"])
    notices, forms = attachment_texts(raw)
    sources: list[tuple[str | None, str]] = [(None, body)] + [(n, t) for n, t in notices]
    from_attachment: list[str] = []  # 첨부에서 채운 필드 이름 (검수용)

    def first(func, found):
        """본문 → 공고문 순서로 func를 돌려, found(결과)가 참인 첫 결과와 출처를 돌려준다."""
        for source, text in sources:
            result = func(text)
            if found(result):
                return result, source
        return func(body), None

    kind, kind_reason = classify_kind(title)

    (amount, amount_evidence), src = first(extract_amount, lambda r: r[0]["type"] != "unknown")
    amount_evidence = tag_source(amount_evidence, src)
    if src:
        from_attachment.append("amount")

    (deadline, deadline_text, deadline_evidence), src = first(
        lambda t: extract_deadline(title, t, posted), lambda r: r[0] is not None or r[1] is not None)
    deadline_evidence = tag_source(deadline_evidence, src)
    if src:
        from_attachment.append("deadline")

    (duplicate, duplicate_evidence), src = first(extract_duplicate_restriction, lambda r: r[0] is not None)
    duplicate_evidence = tag_source(duplicate_evidence, src)
    if src:
        from_attachment.append("duplicate_restriction")

    # 학년·평점·점수·소득: 본문 값을 두고, 빈 것만 공고문에서 채운다
    eligibility = extract_eligibility(body)
    for name, text in notices:
        extra = extract_eligibility(text)
        for key in ["grades", "gpa_min", "score_min", "income_max"]:
            if eligibility[key] is None and extra[key] is not None:
                eligibility[key] = extra[key]
                from_attachment.append(key)
    if eligibility["income_max"] is not None and "income_max" in eligibility["unclear"]:
        eligibility["unclear"].remove("income_max")

    (departments, dept_unclear, dept_evidence, dept_filtered), src = first(
        extract_departments, lambda r: r[0] is not None)
    dept_evidence = tag_source(dept_evidence, src)
    if src:
        from_attachment.append("departments")

    # 거주지: 본문 → 공고문 → 제목 순서 (제목의 "○○시"는 이름만 있어 가장 약한 근거)
    (residence, res_unclear, res_evidence, res_filtered), src = first(
        lambda t: extract_residence("", t), lambda r: r[0] is not None)
    if residence is None:
        residence, res_unclear, res_evidence, title_filtered = extract_residence(title, "")
        res_filtered = res_filtered + title_filtered
        src = None
    res_evidence = tag_source(res_evidence, src)
    if src:
        from_attachment.append("residence")

    other_conditions, src = first(extract_other_conditions, bool)
    if src:
        from_attachment.append("other_conditions")

    eligibility["departments"] = departments
    eligibility["residence"] = residence
    eligibility["other_conditions"] = other_conditions  # 값으로 못 바꾸는 조건 문장 (읽기용)
    if dept_unclear:
        eligibility["unclear"].append("departments")
    if res_unclear:
        eligibility["unclear"].append("residence")

    # 제출서류: 본문 → 공고문 → 양식 (양식의 "□ 장학금 신청서 1부" 목록도 쓸 만하다)
    documents = []
    for source, text in sources + list(forms):
        documents = extract_documents(text)
        if documents:
            if source:
                from_attachment.append("documents")
            break

    # 면접: 어디든 "면접 있음"이 있으면 있음
    interviews = [has_interview(text) for _, text in sources]
    interview = True if True in interviews else (False if False in interviews else None)

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
        "burden": {"documents": documents, "interview": interview},
        "duplicate_restriction": duplicate,
        "source": {"board": raw.get("board"), "url": raw["url"], "posted_at": raw["posted_date"]},
        # 재게시 묶기는 크롤러가 한다 (crawler/README.md "재게시 묶기"). 다시 올린 글이면 대표 글 bidx, 아니면 None
        "duplicate_of": str(raw["duplicate_of"]) if raw.get("duplicate_of") else None,
        "also_posted_bidx": [],  # 대표 글에만 채운다 (main에서 duplicate_of를 모아서)
        "evidence": {
            "amount": amount_evidence,
            "deadline": deadline_evidence,
            "duplicate_restriction": duplicate_evidence,
            "departments": dept_evidence,
            "residence": res_evidence,
        },
        # 학과·지역 이름이 나왔지만 조건이 아니라고 보고 거른 것 (우대, 문의, 제외 …). 검수할 때 확인용
        "filtered_conditions": dept_filtered + res_filtered,
        # 본문에 없어서 첨부 공고문(또는 양식)에서 채운 필드. 검수할 때 첨부 원문과 맞는지 본다
        "from_attachment": sorted(set(from_attachment)),
        "needs_check": needs_check,
        "content_hash": raw.get("content_hash"),  # 원본이 바뀌었는지 비교용
        "reviewed": False,
    }


def main() -> None:
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    items: dict[str, dict] = {}
    for path in sorted(RAW_DIR.glob("*.json")):
        if path.name.startswith("_"):  # _sample.json 등은 건너뛴다
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("_sample"):
            continue
        item = extract_one(raw)
        items[item["id"]] = item

    # 다시 올린 글을 대표 글의 also_posted_bidx에 모은다. 다시 올린 글 파일도 남겨 두고, 빌드할 때 뺀다.
    for item in items.values():
        rep = items.get(item["duplicate_of"] or "")
        if rep is not None:
            rep["also_posted_bidx"].append(item["id"])

    counts: dict[str, int] = {}
    for item in items.values():
        out = EXTRACTED_DIR / f"{item['id']}.json"
        out.write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
        counts[item["notice_kind"]] = counts.get(item["notice_kind"], 0) + 1
    duplicates = sum(1 for i in items.values() if i["duplicate_of"])
    summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
    print(f"{len(items)}건 추출 → {EXTRACTED_DIR.relative_to(EXTRACTED_DIR.parents[1])} ({summary}, 재게시 {duplicates})")


if __name__ == "__main__":
    main()
