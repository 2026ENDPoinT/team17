"""data/raw/{bidx}.json을 읽어 규칙으로 분류·추출하고 data/extracted/{bidx}.json에 쓴다.

실행: uv run python classifier/extract.py  (규칙 시험: --raw data/raw_test --out 저장소 밖 폴더)
입력 형식: data/raw/_sample.json (본문 body_text + 첨부 attachments[].text) / 출력 형식: data/scholarships.sample.json의 items 한 건 + 분류용 필드
"""

import argparse
import json
import time
from datetime import date
from pathlib import Path

from config import EXTRACTED_DIR, HQ_SITE, RAW_DIR
from parser import NOT_VALUE_KINDS, Document, other_conditions, parse
from rules import (
    OPEN_END_NOTE,
    YEAR_FIX_NOTE,
    classify_category,
    classify_kind,
    classify_label,
    extract_amount,
    extract_deadline,
    extract_departments,
    extract_documents,
    extract_duplicate_restriction,
    extract_eligibility,
    extract_name,
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


# ── 의미 분석: 문단(Document) → 필드 값 ──
# 컴파일러의 의미 분석 단계처럼, 구문 분석(parser.py)이 나눈 문단을 보고 값을 정한다.
# 필드마다 "그 필드의 문단"을 먼저 보고, 없으면 값을 틀리게 만드는 문단(우대·일정·방법·서류)을 뺀 나머지를 본다.
# 문단 제목이 없는 짧은 공지는 문단이 intro 하나뿐이라 예전처럼 텍스트 전체를 읽는 것과 같다.


def pass_amount(doc: Document):
    found = extract_amount(doc.text(["amount"]))
    if found[0]["type"] != "unknown":
        return found
    return extract_amount(doc.text_except(NOT_VALUE_KINDS + ["period"]))


def pass_deadline(doc: Document, title: str, posted: date):
    """기간 문단을 먼저 보고, 없으면 전체를 본다.

    다른 필드와 달리 문단을 빼지 않는다. 실제 공지는 마감을 "4. 지원방법: … 6.19.(금) 18시까지 이메일 제출"처럼
    신청방법 문단에 같이 쓰는 경우가 많았다 (raw_test에서 문단을 빼서 놓친 마감 12건, 2026-11-14).
    발표일·면접일 줄은 DEADLINE_SKIP_WORDS가 줄 단위로 거른다.
    """
    found = extract_deadline(title, doc.text(["period"]), posted)
    if found[0] is not None or found[1] is not None:
        return found
    return extract_deadline(title, doc.full(), posted)


def pass_eligibility(doc: Document) -> dict:
    """학년·평점·점수·소득: 자격 문단 값을 두고, 빈 것만 나머지 문단(우대·일정·금액 제외)에서 채운다."""
    result = extract_eligibility(doc.text(["eligibility"]))
    rest = extract_eligibility(doc.text_except(NOT_VALUE_KINDS + ["amount", "period"]))
    for key in ["grades", "gpa_min", "score_min", "income_max"]:
        if result[key] is None:
            result[key] = rest[key]
    result["unclear"] = rest["unclear"] if result["income_max"] is None else []
    return result


def pass_departments(doc: Document):
    found = extract_departments(doc.text(["eligibility"]))
    if found[0] is not None:
        return found
    return extract_departments(doc.text_except(["preference", "method", "schedule"]))


def pass_residence(doc: Document):
    found = extract_residence("", doc.text(["eligibility"]))
    if found[0] is not None:
        return found
    return extract_residence("", doc.text_except(["preference", "method", "schedule"]))


def pass_documents(doc: Document) -> list[str]:
    return extract_documents(doc.text(["documents"])) or extract_documents(doc.full())


def extract_one(raw: dict) -> dict:
    """공지 원본 1건 → 추출 결과 1건.

    단계: 전처리(첨부 다듬기) → 구문 분석(문단 나누기) → 의미 분석(필드마다 pass_*) → 중간 표현(이 dict).
    본문을 먼저 읽고, 본문에서 못 찾은 값만 첨부 공고문에서 찾는다 (연장 공지처럼 본문이 더 최신일 수 있다).
    신청서 양식 첨부는 빈칸이 많아서 제출서류 목록에만 쓴다.
    """
    title = raw["title"]
    body = raw.get("body_text") or ""
    posted = date.fromisoformat(raw["posted_date"])
    notices, forms = attachment_texts(raw)
    # 구문 분석: 본문과 첨부를 각각 문단으로 나눈다
    sources: list[tuple[str | None, Document]] = [(None, parse(body))] + [(n, parse(t)) for n, t in notices]
    form_docs: list[tuple[str | None, Document]] = [(n, parse(t)) for n, t in forms]
    body_doc = sources[0][1]
    from_attachment: list[str] = []  # 첨부에서 채운 필드 이름 (검수용)

    def first(func, found):
        """본문 → 공고문 순서로 func(문서)를 돌려, found(결과)가 참인 첫 결과와 출처를 돌려준다."""
        for source, doc in sources:
            result = func(doc)
            if found(result):
                return result, source
        return func(body_doc), None

    def mark(field: str, source: str | None) -> None:
        if source:
            from_attachment.append(field)

    kind, kind_reason = classify_kind(title)

    (amount, amount_evidence), src = first(pass_amount, lambda r: r[0]["type"] != "unknown")
    amount_evidence = tag_source(amount_evidence, src)
    mark("amount", src)

    (deadline, deadline_text, deadline_evidence), src = first(
        lambda d: pass_deadline(d, title, posted), lambda r: r[0] is not None or r[1] is not None)
    deadline_evidence = tag_source(deadline_evidence, src)
    mark("deadline", src)

    (duplicate, duplicate_evidence), src = first(
        lambda d: extract_duplicate_restriction(d.full()), lambda r: r[0] is not None)
    duplicate_evidence = tag_source(duplicate_evidence, src)
    mark("duplicate_restriction", src)

    # 학년·평점·점수·소득: 본문 값을 두고, 빈 것만 공고문에서 채운다
    eligibility = pass_eligibility(body_doc)
    for _, doc in sources[1:]:
        extra = pass_eligibility(doc)
        for key in ["grades", "gpa_min", "score_min", "income_max"]:
            if eligibility[key] is None and extra[key] is not None:
                eligibility[key] = extra[key]
                from_attachment.append(key)
    if eligibility["income_max"] is not None and "income_max" in eligibility["unclear"]:
        eligibility["unclear"].remove("income_max")

    (departments, dept_unclear, dept_evidence, dept_filtered), src = first(pass_departments, lambda r: r[0] is not None)
    dept_evidence = tag_source(dept_evidence, src)
    mark("departments", src)

    # 거주지: 본문 → 공고문 → 제목 순서 (제목의 "○○시"는 이름만 있어 가장 약한 근거)
    (residence, res_unclear, res_evidence, res_filtered), src = first(pass_residence, lambda r: r[0] is not None)
    if residence is None:
        residence, res_unclear, res_evidence, title_filtered = extract_residence(title, "")
        res_filtered = res_filtered + title_filtered
        src = None
    res_evidence = tag_source(res_evidence, src)
    mark("residence", src)

    conditions, src = first(other_conditions, bool)
    mark("other_conditions", src)

    eligibility["departments"] = departments
    eligibility["residence"] = residence
    eligibility["other_conditions"] = conditions  # 값으로 못 바꾸는 조건 문장 (읽기용)
    if dept_unclear:
        eligibility["unclear"].append("departments")
    if res_unclear:
        eligibility["unclear"].append("residence")

    # 제출서류: 본문 → 공고문 → 양식 (양식의 "□ 장학금 신청서 1부" 목록도 쓸 만하다)
    documents: list[str] = []
    for source, doc in sources + form_docs:
        documents = pass_documents(doc)
        if documents:
            mark("documents", source)
            break

    # 면접: 어디든 "면접 있음"이 있으면 있음 (일정 문단의 "면접심사: 11.28"도 면접이 있다는 뜻이다)
    interviews = [has_interview(doc.full()) for _, doc in sources]
    interview = True if True in interviews else (False if False in interviews else None)

    # 사람이 꼭 확인해야 하는 항목. 화면에서 "확인 필요"로 보여 줄 수 있다.
    needs_check = []
    if amount["type"] == "unknown":
        needs_check.append("amount")
    if deadline is None and deadline_text is None:  # 상시 모집은 deadline_text만 있다
        needs_check.append("deadline")
    elif deadline_text and (YEAR_FIX_NOTE in deadline_text or OPEN_END_NOTE in deadline_text):  # 연도를 고쳤거나 끝 날짜가 없으면 사람이 확인
        needs_check.append("deadline")
    if not documents:
        needs_check.append("documents")
    if len(body.strip()) < 100:
        needs_check.append("poster_only" if raw.get("has_images") else "body_short")

    label, label_reason = classify_label(title, kind)

    return {
        "id": str(raw["bidx"]),
        "notice_kind": kind,  # 모집 / 결과 / 안내 / 확인필요. 빌드할 때 '모집'만 남긴다
        "notice_kind_reason": kind_reason,
        "label": label,  # 모집 / 수정 / 완료 / None. 이벤트 묶기 단계가 장학금 상태를 정할 때 쓴다
        "label_reason": label_reason,
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


def write_json(path: Path, data: dict) -> None:
    """JSON 파일 쓰기. OneDrive가 동기화 중인 파일은 잠깐 못 쓸 때가 있어서 몇 번 다시 시도한다."""
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    for attempt in range(5):
        try:
            path.write_text(text, encoding="utf-8", newline="\n")
            return
        except OSError:
            if attempt == 4:
                raise
            time.sleep(1)


def split_by_deadline(items: dict[str, dict], sites: dict[str, str]) -> list[str]:
    """크롤러가 제목으로 묶은 재게시 그룹을 마감일로 다시 나눈다. 나눈 글의 id 목록을 돌려준다.

    크롤러는 제목의 괄호 "(~11/6(금))"를 지우고 비교해서, 같은 제목에 마감일만 다른 공지
    (같은 이름의 다른 차수 모집)도 한 그룹으로 묶을 수 있다. 분류는 공지마다 마감일을 뽑았으니
    그룹 안에서 마감일이 다르면 따로 둔다.
    - 마감일을 모르는 글은 대표 글 쪽에 남긴다 (다르다는 근거가 없다).
    - 제목에 "연장"이 있는 글은 같은 공지의 기간 연장이라 나누지 않는다.
    - 나뉜 쪽에서는 크롤러와 같은 순서(본부 글 > 먼저 올라온 글 > bidx가 작은 글)로 새 대표를 고른다.
    """
    groups: dict[str, list[dict]] = {}
    for item in items.values():
        rep_id = item["duplicate_of"]
        if rep_id and rep_id in items:
            groups.setdefault(rep_id, [items[rep_id]]).append(item)

    def priority(item: dict) -> tuple:
        return (sites.get(item["id"]) != HQ_SITE, item["source"]["posted_at"], int(item["id"]))

    split: list[str] = []
    for rep_id, members in groups.items():
        rep_deadline = items[rep_id]["deadline"]
        by_deadline: dict[str, list[dict]] = {}
        for item in members[1:]:
            if item["deadline"] and rep_deadline and item["deadline"] != rep_deadline and "연장" not in item["title"]:
                by_deadline.setdefault(item["deadline"], []).append(item)
        for deadline, others in by_deadline.items():
            new_rep = min(others, key=priority)
            for item in others:
                item["duplicate_of"] = None if item is new_rep else new_rep["id"]
                item["duplicate_split"] = (f"대표 글 {rep_id}와 마감일이 달라 따로 둠 "
                                           f"({rep_deadline} / {deadline})")
                split.append(item["id"])
    return split


def main() -> None:
    cli = argparse.ArgumentParser(description="data/raw → data/extracted")
    cli.add_argument("--raw", type=Path, default=RAW_DIR, help="입력 폴더 (규칙 시험: data/raw_test)")
    cli.add_argument("--out", type=Path, default=EXTRACTED_DIR, help="출력 폴더 (시험할 때는 저장소 밖 폴더)")
    args = cli.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    items: dict[str, dict] = {}
    sites: dict[str, str] = {}
    for path in sorted(args.raw.glob("*.json")):
        if path.name.startswith("_"):  # _sample.json 등은 건너뛴다
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("_sample"):
            continue
        item = extract_one(raw)
        items[item["id"]] = item
        sites[item["id"]] = raw.get("site", "")

    # 크롤러가 제목으로 묶은 재게시 그룹을 마감일로 한 번 더 나눈다
    split = split_by_deadline(items, sites)

    # 다시 올린 글을 대표 글의 also_posted_bidx에 모은다. 다시 올린 글 파일도 남겨 두고, 빌드할 때 뺀다.
    for item in items.values():
        rep = items.get(item["duplicate_of"] or "")
        if rep is not None:
            rep["also_posted_bidx"].append(item["id"])

    counts: dict[str, int] = {}
    labels: dict[str, int] = {}
    for item in items.values():
        write_json(args.out / f"{item['id']}.json", item)
        counts[item["notice_kind"]] = counts.get(item["notice_kind"], 0) + 1
        labels[str(item["label"])] = labels.get(str(item["label"]), 0) + 1
    duplicates = sum(1 for i in items.values() if i["duplicate_of"])
    summary = ", ".join(f"{k} {v}" for k, v in sorted(counts.items()))
    label_summary = ", ".join(f"{k} {v}" for k, v in sorted(labels.items()))
    print(f"{len(items)}건 추출 → {args.out} ({summary}, 재게시 {duplicates}, 마감일이 달라 나눈 글 {len(split)})")
    print(f"라벨: {label_summary}")


if __name__ == "__main__":
    main()
