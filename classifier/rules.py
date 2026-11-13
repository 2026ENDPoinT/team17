"""규칙 기반 분류·추출 함수 모음. 입력: 공지 제목·본문 문자열 / 출력: 값과 근거 문장.

파일 읽기·쓰기 없이 순수 함수만 둔다. 원문에 있는 글자만 뽑으므로 숫자를 지어내지 않는다.
못 찾으면 None을 돌려주고, 그 필드는 사람이 검수에서 채운다.
"""

import re
from datetime import date, timedelta

from config import (
    AMOUNT_LINE_WORDS,
    CLOSED_WORDS,
    DEADLINE_LINE_WORDS,
    DEADLINE_SKIP_WORDS,
    DOCUMENT_HEAD_WORDS,
    DOCUMENT_SKIP_WORDS,
    DOCUMENT_WORDS,
    ELIGIBILITY_LINE_WORDS,
    EVIDENCE_MAX,
    EXTERNAL_WORDS,
    INCOME_WORDS,
    INFO_WORDS,
    RECRUIT_WORDS,
    RESIDENCE_WORDS,
    RESULT_WORDS,
    SCHOLARSHIP_WORDS,
    SUMMARY_MAX,
    WORK_BNUMS,
    WORK_WORDS,
)


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _has_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def _short(text: str, limit: int = EVIDENCE_MAX) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


# ── 공지 종류 ──


def classify_kind(title: str) -> tuple[str, str]:
    """제목으로 공지 종류를 정한다. 반환: (종류, 이유). 종류는 모집/결과/안내/확인필요."""
    for word in RESULT_WORDS:
        if word in title:
            return "결과", f"제목에 '{word}'"
    for word in INFO_WORDS:
        if word in title:
            return "안내", f"제목에 '{word}'"
    recruit = next((w for w in RECRUIT_WORDS if w in title), None)
    scholarship = next((w for w in SCHOLARSHIP_WORDS if w in title), None)
    if recruit and scholarship:
        return "모집", f"제목에 '{scholarship}', '{recruit}'"
    if recruit:
        return "확인필요", f"제목에 '{recruit}'는 있지만 장학 관련 단어가 없음"
    return "확인필요", "모집·결과 단어가 없음"


def is_closed(title: str) -> bool:
    return _has_any(title, CLOSED_WORDS)


# ── 유형 ──


def classify_category(title: str, bnum: int) -> str:
    """교내 / 교외 / 근로."""
    if bnum in WORK_BNUMS or _has_any(title, WORK_WORDS):
        return "근로"
    if _has_any(title, EXTERNAL_WORDS):
        return "교외"
    return "교내"


# ── 장학금 이름 ──

_LEAD_TAG = re.compile(r"^\s*(\([^)]*\)|\[[^\]]*\])\s*")
_TAIL_PAREN = re.compile(r"\s*\((?:[^()]|\([^()]*\))*\)\s*$")
_TAIL_WORDS = re.compile(r"\s*(선발\s*안내|모집\s*안내|신청\s*안내|선발\s*공고|모집\s*공고|신청안내|안내)\s*$")


def extract_name(title: str) -> str:
    """제목 앞의 (홍보)·[부서] 표시와 끝의 (마감)·(~11/11까지), '선발 안내'를 떼어 장학금 이름을 만든다."""
    name = title
    while _LEAD_TAG.match(name):
        name = _LEAD_TAG.sub("", name, count=1)
    while _TAIL_PAREN.search(name):
        name = _TAIL_PAREN.sub("", name)
    name = _TAIL_WORDS.sub("", name)
    return name.strip() or title.strip()


# ── 금액 ──

_TUITION_FULL = re.compile(r"(등록금|수업료)\s*(전액|100\s*%)")
_TUITION_RATIO = re.compile(r"(등록금|수업료)[^0-9\n]{0,10}(\d{1,3})\s*%")
_HOURLY = re.compile(r"(?:시급|시간당)[^0-9\n]{0,10}(\d{1,3}(?:,\d{3})+|\d{4,6})\s*원")
_MANWON = re.compile(r"(\d{1,3}(?:,\d{3})*|\d+)\s*만\s*원")
_WON = re.compile(r"(\d{1,3}(?:,\d{3})+)\s*원")


def _num(text: str) -> int:
    return int(text.replace(",", ""))


def _amount_from_line(line: str) -> dict | None:
    """한 줄에서 금액을 찾는다. 등록금 비율 → 시급 → 만원 → 원 순서로 본다."""
    if m := _TUITION_FULL.search(line):
        return {"type": "tuition_ratio", "value": 100, "text": m.group(0)}
    if m := _TUITION_RATIO.search(line):
        return {"type": "tuition_ratio", "value": int(m.group(2)), "text": m.group(0)}
    if m := _HOURLY.search(line):
        return {"type": "hourly", "value": _num(m.group(1)), "text": m.group(0)}
    if m := _MANWON.search(line):
        return {"type": "lump_sum", "value": _num(m.group(1)) * 10000, "text": m.group(0)}
    if m := _WON.search(line):
        return {"type": "lump_sum", "value": _num(m.group(1)), "text": m.group(0)}
    return None


def extract_amount(body: str) -> tuple[dict, str | None]:
    """반환: (amount, 근거 문장). 못 찾으면 type='unknown'."""
    lines = _lines(body)
    # 1) 금액 단어가 있는 줄을 먼저 본다 (소득 기준 같은 다른 숫자를 피하려고)
    for line in lines:
        if _has_any(line, AMOUNT_LINE_WORDS) and not _has_any(line, INCOME_WORDS):
            if found := _amount_from_line(line):
                return found, _short(line)
    # 2) 근로 공지는 시급이 금액 단어 없이 나오기도 한다
    for line in lines:
        if m := _HOURLY.search(line):
            return {"type": "hourly", "value": _num(m.group(1)), "text": m.group(0)}, _short(line)
    return {"type": "unknown", "value": None, "text": None}, None


# ── 마감일 ──

# 2026. 11. 9. / 26. 11. 24. / 2026년 10월 26일 / 10월 26일 / 11/12 / 11. 6.
_DATE = re.compile(r"(?<!\d)(?:(\d{4}|\d{2})\s*[.년\-]\s*)?(\d{1,2})\s*[.월/\-]\s*(\d{1,2})(?!\d)")


def _dates_in(line: str, posted: date) -> list[date]:
    """한 줄의 날짜를 모두 찾는다. 연도가 없으면 앞 날짜의 연도, 그것도 없으면 게시일 기준으로 정한다."""
    found: list[date] = []
    year: int | None = None
    for m in _DATE.finditer(line):
        y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
        if not (1 <= mo <= 12 and 1 <= d <= 31):
            continue
        if y:
            year = int(y) + 2000 if len(y) == 2 else int(y)
        use_year = year or posted.year
        try:
            value = date(use_year, mo, d)
        except ValueError:
            continue
        if year is None and value < posted - timedelta(days=60):
            value = value.replace(year=use_year + 1)  # 12월에 올라온 "~1/10" 같은 경우
        found.append(value)
    return found


def extract_deadline(title: str, body: str, posted: date) -> tuple[str | None, str | None, str | None]:
    """반환: (마감일 YYYY-MM-DD, 원문 표기, 근거 문장). 제목을 먼저 본다 (연장되면 제목이 바뀌므로)."""
    if "~" in title or "까지" in title:
        dates = _dates_in(title, posted)
        if dates:
            return dates[-1].isoformat(), title, _short(title)
    for line in _lines(body):
        if not _has_any(line, DEADLINE_LINE_WORDS) or _has_any(line, DEADLINE_SKIP_WORDS):
            continue
        dates = _dates_in(line, posted)
        if dates:
            text = line.split(":", 1)[-1].strip() if ":" in line else line
            return dates[-1].isoformat(), _short(text, 60), _short(line)
    return None, None, None


# ── 대상 조건 ──

# (?<!\d): "2026학년도"의 6을 6학년으로 읽지 않게 한다
_GRADE_RANGE = re.compile(r"(?<!\d)(\d)\s*[~\-]\s*(\d)\s*학년")
_GRADE_LIST = re.compile(r"(?<![\d.])((?:\d\s*,\s*)*\d)\s*학년(?!도)")
_GPA = re.compile(r"(\d\.\d{1,2})\s*(?:/\s*4\.[35])?\s*(?:점\s*)?이상")
_INCOME = re.compile(r"(?:(\d{1,2})\s*[~\-]\s*)?(\d{1,2})\s*(?:구간|분위)")


def extract_eligibility(body: str) -> dict:
    """학년, 최소 평점, 소득 구간 상한을 찾는다. 확실하지 않은 조건은 unclear에 이름을 넣는다."""
    result: dict = {
        "grades": None,
        "departments": None,
        "gpa_min": None,
        "income_max": None,
        "residence": None,
        "unclear": [],
    }
    # "우대사항: 2학년 이하"처럼 우대·가산점 줄은 자격 조건이 아니므로 뺀다
    lines = [line for line in _lines(body)
             if _has_any(line, ELIGIBILITY_LINE_WORDS) and not _has_any(line, ["우대", "가산"])]
    for line in lines:
        if result["grades"] is None:
            if m := _GRADE_RANGE.search(line):
                lo, hi = int(m.group(1)), int(m.group(2))
                if 1 <= lo <= hi <= 6:
                    result["grades"] = list(range(lo, hi + 1))
            elif m := _GRADE_LIST.search(line):
                grades = sorted({int(g) for g in re.findall(r"\d", m.group(1))})
                if all(1 <= g <= 6 for g in grades):
                    result["grades"] = grades
        if result["gpa_min"] is None and _has_any(line, ["성적", "평점", "학점"]):
            if m := _GPA.search(line):
                result["gpa_min"] = float(m.group(1))
        if result["income_max"] is None and _has_any(line, ["구간", "분위"]):
            if m := _INCOME.search(line):
                result["income_max"] = int(m.group(2))
    if _has_any(body, RESIDENCE_WORDS):
        result["unclear"].append("residence")
    if result["income_max"] is None and _has_any(body, INCOME_WORDS):
        result["unclear"].append("income_max")
    return result


# ── 준비 부담 ──

_ITEM_MARK = re.compile(r"^\s*(\d+\s*[).]|[-•○▶►·※*]|[①-⑳])\s*")
_SECTION_HEAD = re.compile(r"^\s*([가-하]\s*[.):]|\d+\s*\.\s*\S+\s*[:：])")
_COUNT = re.compile(r"\s*\d+\s*부\b.*$")


def _clean_doc(text: str) -> str:
    text = _ITEM_MARK.sub("", text)
    text = re.sub(r"^\(필수\)\s*", "", text)
    text = _COUNT.sub("", text)
    text = re.sub(r"\s*각$", "", text)
    return text.strip(" .,:：")[:40]


def _looks_like_doc(text: str) -> bool:
    """서류 이름처럼 보이는지. 설명 문장('~할 경우', '업무: ...')은 뺀다."""
    if not text or ":" in text or "http" in text or _has_any(text, DOCUMENT_SKIP_WORDS):
        return False
    return _has_any(text, DOCUMENT_WORDS)


def extract_documents(body: str) -> list[str]:
    """'제출서류' 다음에 오는 목록을 뽑는다. 같은 줄에 쉼표로 나열된 경우도 처리한다."""
    lines = _lines(body)
    for i, line in enumerate(lines):
        if not _has_any(line, DOCUMENT_HEAD_WORDS):
            continue
        docs: list[str] = []
        after = re.split(r"[:：]", line, maxsplit=1)
        if len(after) == 2 and after[1].strip():
            docs = [_clean_doc(p) for p in re.split(r"[,，、]", after[1])]
        else:
            for nxt in lines[i + 1 : i + 15]:
                if _SECTION_HEAD.match(nxt) and not _ITEM_MARK.match(nxt):
                    break
                if not _ITEM_MARK.match(nxt):
                    break
                docs.append(_clean_doc(nxt))
        docs = [d for d in docs if _looks_like_doc(d)]
        if docs:
            return docs
    return []


def has_interview(body: str) -> bool | None:
    if not body.strip():
        return None
    return "면접" in body


_DUP_NO = re.compile(r"중복\s*(수혜|지원|선발)\s*(불가|제한|금지)|타\s*(기관|장학)[^\n]{0,30}수혜[^\n]{0,15}(제외|불가)"
                     r"|제외\s*대상[^\n]{0,40}장학금\s*수혜")
_DUP_OK = re.compile(r"중복\s*(수혜|지원)\s*가능")


def extract_duplicate_restriction(body: str) -> tuple[bool | None, str | None]:
    for line in _lines(body):
        if _DUP_OK.search(line):
            return False, _short(line)
        if _DUP_NO.search(line):
            return True, _short(line)
    return None, None


# ── 요약 ──


def make_summary(body: str, has_images: bool, attachment_count: int) -> str:
    """본문 첫 문장을 짧게 자른다. 본문이 없으면 어디를 봐야 하는지 적는다."""
    lines = [line for line in _lines(body) if len(line) >= 10 and not line.startswith("-")]
    if lines:
        return _short(lines[0], SUMMARY_MAX)
    if has_images:
        return "본문 없이 포스터 이미지로 안내된 공지입니다. 원문을 확인하세요."
    if attachment_count:
        return "내용이 첨부파일에 있습니다. 원문을 확인하세요."
    return "본문이 없습니다. 원문을 확인하세요."
