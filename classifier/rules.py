"""규칙 기반 분류·추출 함수 모음. 입력: 공지 제목·본문 문자열 / 출력: 값과 근거 문장.

파일 읽기·쓰기 없이 순수 함수만 둔다. 원문에 있는 글자만 뽑으므로 숫자를 지어내지 않는다.
못 찾으면 None을 돌려주고, 그 필드는 사람이 검수에서 채운다.
"""

import re
from datetime import date, timedelta

from config import (
    AMOUNT_AFTER_SKIP,
    AMOUNT_BEFORE_SKIP,
    AMOUNT_LINE_SKIP,
    AMOUNT_LINE_WORDS,
    CLOSED_WORDS,
    COND_AFTER_SKIP,
    COND_BEFORE_SKIP,
    CONDITION_BLOCK_MAX,
    CONDITION_HEAD_WORDS,
    CONDITION_LIST_MAX,
    CONDITION_MAX,
    CONDITION_NOT_WORDS,
    CONTEXT_AFTER,
    CONTEXT_BEFORE,
    CONTINUATION_MARKS,
    DEADLINE_LINE_WORDS,
    DEADLINE_SKIP_WORDS,
    DEPARTMENT_LINE_WORDS,
    DOCUMENT_HEAD_WORDS,
    DOCUMENT_SKIP_WORDS,
    DOCUMENT_WORDS,
    ELIGIBILITY_LINE_WORDS,
    EVIDENCE_MAX,
    EXCLUDE_AFTER_WORDS,
    EXTERNAL_WORDS,
    FORM_ATTACHMENT_WORDS,
    IGNORED_ATTACHMENT_WORDS,
    INCOME_WORDS,
    INFO_WORDS,
    INTERVIEW_AFTER,
    INTERVIEW_NEG_WORDS,
    LINE_HEAD_SKIP,
    MULTI_AMOUNT_WORDS,
    NO_LIMIT_WORDS,
    NOT_CONDITION_WORDS,
    NOTICE_ATTACHMENT_WORDS,
    PREFERENCE_HEAD_WORDS,
    PREFERENCE_TAGS,
    RECRUIT_WORDS,
    RESIDENCE_WORDS,
    RESULT_WORDS,
    ROLLING_SKIP_WORDS,
    ROLLING_WORDS,
    SCHOLARSHIP_WORDS,
    SUMMARY_MAX,
    SUMMARY_SKIP_STARTS,
    WORK_BNUMS,
    WORK_WORDS,
)
from dictionary import COLLEGES, DEPARTMENTS, FIELDS, NOT_REGION, SIDO


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _has_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def _short(text: str, limit: int = EVIDENCE_MAX) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _context_skip(line: str, start: int, end: int, before_words: list[str], after_words: list[str]) -> str | None:
    """line[start:end]에서 찾은 값의 앞뒤 몇 글자를 보고, 쓰면 안 되는 값이면 이유를 돌려준다.

    학년·성적·소득·금액이 같이 쓴다. 학과·거주지는 같은 생각을 _skip_reason에서 더 넓은 창으로 한다.
    """
    before = line[max(0, start - CONTEXT_BEFORE) : start]
    after = line[end : end + CONTEXT_AFTER]
    for word in before_words:
        if word in before:
            return f"앞에 '{word}'"
    for word in after_words:
        if word in after:
            return f"뒤에 '{word}'"
    return None


def _head_skip(line: str) -> bool:
    """'우대사항: …', '1순위: …'처럼 콜론 앞 이름표가 자격이 아닌 줄인지."""
    head, sep, _ = line.partition(":")
    return bool(sep) and _has_any(head, LINE_HEAD_SKIP)


def _after_colon(line: str) -> str:
    """'다. 지원금액: 300만원' → '300만원'. 콜론이 없으면 줄 그대로."""
    parts = re.split(r"[:：]", line, maxsplit=1)
    return parts[1].strip() if len(parts) == 2 and parts[1].strip() else line


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
    """한 줄에서 금액을 찾는다. 등록금 비율 → 시급 → 만원 → 원 순서로 본다.

    소득 단어("차상위", "소득")보다 뒤에 나오는 금액은 소득 기준일 수 있어서 쓰지 않는다.
    예: "수업료 100% 면제(단, 차상위~5구간 … 50%만 면제)" → 100%를 쓴다.
    """
    income_at = min((line.find(w) for w in INCOME_WORDS if w in line), default=len(line))

    def first(pattern: re.Pattern) -> re.Match | None:
        # 소득 단어 뒤의 금액, "총 예산 …", "작년 지급액 …", "100만원 미만" 같은 금액은 건너뛴다
        ok = [m for m in pattern.finditer(line)
              if m.start() < income_at
              and not _context_skip(line, m.start(), m.end(), AMOUNT_BEFORE_SKIP, AMOUNT_AFTER_SKIP)]
        # "고등학생 50만원, 대학생 최대 100만원"처럼 대상별 금액이면 대학생 금액을 고른다
        for m in ok:
            if "대학" in line[max(0, m.start() - CONTEXT_BEFORE) : m.start()]:
                return m
        return ok[0] if ok else None

    if m := first(_TUITION_FULL):
        return {"type": "tuition_ratio", "value": 100, "text": m.group(0)}
    if m := first(_TUITION_RATIO):
        return {"type": "tuition_ratio", "value": int(m.group(2)), "text": m.group(0)}
    if m := first(_HOURLY):
        return {"type": "hourly", "value": _num(m.group(1)), "text": m.group(0)}
    if m := first(_MANWON):
        return {"type": "lump_sum", "value": _num(m.group(1)) * 10000, "text": m.group(0)}
    if m := first(_WON):
        return {"type": "lump_sum", "value": _num(m.group(1)), "text": m.group(0)}
    return None


def extract_amount(body: str) -> tuple[dict, str | None]:
    """반환: (amount, 근거 문장). 못 찾으면 type='unknown'."""
    lines = _lines(body)
    # 1) 금액 단어가 있는 줄을 먼저 본다 (소득 기준 같은 다른 숫자를 피하려고)
    for line in lines:
        if _has_any(line, AMOUNT_LINE_WORDS) and not _has_any(line, AMOUNT_LINE_SKIP):
            if found := _amount_from_line(line):
                # "등록금 전액 또는 학기당 350만원 (택1)"처럼 고르는 금액이면 값은 첫 금액, 표시는 줄 전체로 한다
                if _has_any(line, MULTI_AMOUNT_WORDS):
                    found["text"] = _short(_after_colon(line), 60)
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
            return dates[-1].isoformat(), _short(_after_colon(line), 60), _short(line)
    # 날짜 없이 "선발 완료시까지"인 상시 모집: 마감일은 없지만 원문 표기는 남긴다
    for line in _lines(body):
        if (_has_any(line, ROLLING_WORDS) and _has_any(line, DEADLINE_LINE_WORDS + ["지원기간", "지원 기간"])
                and not _has_any(line, ROLLING_SKIP_WORDS)):
            return None, "상시 모집 (" + _short(_after_colon(line), 40) + ")", _short(line)
    return None, None, None


# ── 대상 조건 ──

# 앞에 숫자·한글이 붙으면 학년이 아니다: "2026학년도"의 6, "중1학년"의 1
_GRADE_RANGE = re.compile(r"(?<![\d가-힣])(\d)\s*[~\-]\s*(\d)\s*학년")
_GRADE_LIST = re.compile(r"(?<![\d.가-힣])((?:\d\s*,\s*)*\d)\s*학년(?!도)")
_GPA = re.compile(r"(\d\.\d{1,2})\s*(?:/\s*4\.[35])?\s*(?:점\s*)?이상")
# 100점 만점 성적: "백분율 성적 85점 이상", "C0(70점/100점 만점) 이상"
_SCORE = re.compile(r"(?<!\d)(\d{2})\s*점[^\n]{0,15}?이상")
_INCOME = re.compile(r"(?:(\d{1,2})\s*[~\-]\s*)?(\d{1,2})\s*(?:구간|분위)")


def extract_eligibility(body: str) -> dict:
    """학년, 최소 평점, 소득 구간 상한을 찾는다. 확실하지 않은 조건은 unclear에 이름을 넣는다."""
    result: dict = {
        "grades": None,
        "departments": None,
        "gpa_min": None,  # 4.5 만점 평점
        "score_min": None,  # 100점 만점 성적 (백분율)
        "income_max": None,
        "residence": None,
        "unclear": [],
    }
    # "우대사항: …", "1순위: …"처럼 이름표부터 자격이 아닌 줄은 통째로 뺀다
    lines = [line for line in _lines(body) if _has_any(line, ELIGIBILITY_LINE_WORDS) and not _head_skip(line)]

    def ok_matches(pattern: re.Pattern, line: str) -> list[re.Match]:
        # 같은 줄에 진짜 조건과 우대·순위가 섞여 있으면 ("3학년 재학생 (2학년 우대)") 우대 쪽 값만 버린다
        return [m for m in pattern.finditer(line)
                if not _context_skip(line, m.start(), m.end(), COND_BEFORE_SKIP, COND_AFTER_SKIP)]

    for line in lines:
        if result["grades"] is None:
            if ranges := ok_matches(_GRADE_RANGE, line):
                lo, hi = int(ranges[0].group(1)), int(ranges[0].group(2))
                if 1 <= lo <= hi <= 6:
                    result["grades"] = list(range(lo, hi + 1))
            elif singles := ok_matches(_GRADE_LIST, line):
                m = singles[0]
                grades = sorted({int(g) for g in re.findall(r"\d", m.group(1))})
                tail = line[m.end() : m.end() + 4]
                if len(grades) == 1 and "이상" in tail:  # "3학년 이상" → 3~4학년
                    grades = list(range(grades[0], 5))
                elif len(grades) == 1 and "이하" in tail:  # "2학년 이하" → 1~2학년
                    grades = list(range(1, grades[0] + 1))
                if all(1 <= g <= 6 for g in grades):
                    result["grades"] = grades
        if _has_any(line, ["성적", "평점", "학점"]):
            if result["gpa_min"] is None and (found := ok_matches(_GPA, line)):
                result["gpa_min"] = float(found[0].group(1))
            if result["score_min"] is None:
                scores = [m for m in ok_matches(_SCORE, line) if 40 <= int(m.group(1)) <= 100]
                if scores:
                    result["score_min"] = int(scores[0].group(1))
        if result["income_max"] is None and _has_any(line, ["구간", "분위"]):
            if found := ok_matches(_INCOME, line):
                result["income_max"] = int(found[0].group(2))
    if result["income_max"] is None and _has_any(body, INCOME_WORDS):
        result["unclear"].append("income_max")
    return result


# ── 학과·거주지 ──
# 흐름: 사전·패턴으로 이름을 찾는다 → 이름 앞뒤 몇 글자를 보고 조건이 아닌 문맥(우대, 문의, 제외 …)이면 거른다.

_BEFORE_WINDOW = 25  # 이름 앞 몇 글자까지 거르는 단어를 볼지
_AFTER_WINDOW = 12  # 이름 뒤 몇 글자까지 볼지
_REGION_TAIL = r"(?=[^가-힣]|에|의|내|민|지역|거주|출신|장학|$)"  # 지역 이름 바로 뒤에 올 수 있는 말
_SIGUNGU = re.compile(r"(?<![가-힣])([가-힣]{1,4}(?:시|군|구))" + _REGION_TAIL)
_SIDO = re.compile(r"(?<![가-힣])(" + "|".join(sorted(SIDO, key=len, reverse=True)) + r")" + _REGION_TAIL)
# 제목에서 지역 이름 바로 뒤에 이 말이 오면 거주 조건이 확실하다: "은평구민", "거창군 지역출신"
_TITLE_RESIDENT = re.compile(r"^\s*(민|지역\s*출신|출신)")


def _skip_reason(lines: list[str], i: int, start: int, end: int) -> str | None:
    """lines[i]의 start~end에 있는 학과·지역 이름이 조건이 아니면 그 이유를 돌려준다."""
    line = lines[i]
    before = line[max(0, start - _BEFORE_WINDOW) : start]
    after = line[end : end + _AFTER_WINDOW]
    for word in NOT_CONDITION_WORDS:
        if word in before or word in after:
            return f"앞뒤에 '{word}'"
    for word in NO_LIMIT_WORDS:
        if word in after:
            return f"뒤에 '{word}' (제한 없음)"
    for word in EXCLUDE_AFTER_WORDS:
        if word in after:
            return f"뒤에 '{word}' (제외 조건)"
    if line.startswith(CONTINUATION_MARKS) and i > 0:
        for word in NOT_CONDITION_WORDS:
            if word in lines[i - 1]:
                return f"앞 줄의 '{word}'에 이어지는 설명"
    return None


def _organizer(line: str, end: int) -> bool:
    """'컴퓨터공학과에서는 …', '정보통신대학 컴퓨터공학과에서 …'처럼 학과가 공지를 낸 주체인지.

    이름 바로 뒤(다른 학과·단과대 이름만 건너뛰고)에 '에서'가 오면 주체다.
    '산업공학과 동문회에서는'처럼 사이에 다른 말이 있으면 주체로 보지 않는다.
    """
    rest = line[end:].lstrip()
    names = sorted(DEPARTMENTS + COLLEGES, key=len, reverse=True)
    moved = True
    while moved:
        moved = False
        for name in names:
            if rest.startswith(name):
                rest = rest[len(name) :].lstrip()
                moved = True
                break
    return rest.startswith("에서")


def _find_names(line: str, names: list[str]) -> list[tuple[str, int, int]]:
    """사전의 이름을 긴 것부터 찾는다. '벤처경영학과' 안의 '경영학과'처럼 겹치는 짧은 이름은 버린다."""
    taken: list[tuple[int, int]] = []
    found = []
    for name in sorted(names, key=len, reverse=True):
        for m in re.finditer(re.escape(name), line):
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            found.append((name, m.start(), m.end()))
    return sorted(found, key=lambda x: x[1])


def _find_regions(line: str) -> list[tuple[str, int, int]]:
    found = [(m.group(1), m.start(1), m.end(1)) for m in _SIDO.finditer(line)]
    for m in _SIGUNGU.finditer(line):
        name = m.group(1)
        if name in NOT_REGION or any(s <= m.start(1) < e for _, s, e in found):
            continue
        found.append((name, m.start(1), m.end(1)))
    return sorted(found, key=lambda x: x[1])


def extract_departments(body: str) -> tuple[list[str] | None, bool, str | None, list[dict]]:
    """반환: (학과 목록 또는 None, 확인 필요 여부, 근거 문장, 걸러낸 것 목록)."""
    lines = _lines(body)
    departments: list[str] = []
    evidence = None
    unclear = False
    filtered: list[dict] = []
    for i, line in enumerate(lines):
        if not _has_any(line, DEPARTMENT_LINE_WORDS) and not line.startswith(CONTINUATION_MARKS):
            continue
        for name, start, end in _find_names(line, DEPARTMENTS + COLLEGES + FIELDS):
            reason = _skip_reason(lines, i, start, end)
            if reason is None and _organizer(line, end):
                reason = "뒤에 '에서' (공지를 낸 학과)"
            if reason:
                filtered.append({"field": "departments", "text": name, "reason": reason, "line": _short(line, 80)})
                unclear = unclear or "제외" in reason
                continue
            if not _has_any(line, DEPARTMENT_LINE_WORDS):
                continue  # 이어 쓴 줄인데 앞 줄도 조건 줄이 아니면 쓰지 않는다
            if name not in departments:
                departments.append(name)
            evidence = evidence or _short(line)
            if name in COLLEGES or name in FIELDS:
                unclear = True  # 단과대·계열은 어느 학과까지인지 공지마다 다르다
    return (departments or None), unclear, evidence, filtered


def extract_residence(title: str, body: str) -> tuple[str | None, bool, str | None, list[dict]]:
    """반환: (거주지 또는 None, 확인 필요 여부, 근거 문장, 걸러낸 것 목록).

    1) 본문에서 '거주·주민등록·출신·구민' 같은 말이 있는 줄의 지역 이름 (가장 확실)
    2) 없으면 제목의 지역 이름. '은평구민', '거창군 지역출신'이면 확실, '통영시 …장학금'처럼 이름만 있으면 확인 필요
    """
    lines = _lines(body)
    regions: list[str] = []
    evidence = None
    filtered: list[dict] = []
    mentioned = False
    for i, line in enumerate(lines):
        if not _has_any(line, RESIDENCE_WORDS):
            continue
        line_regions = _find_regions(line)
        if not line_regions:
            # 지역 이름 없이 '거주'만 나온 줄 (예: "학교인근 거주자 우대")
            word = next(w for w in RESIDENCE_WORDS if w in line)
            at = line.find(word)
            if reason := _skip_reason(lines, i, at, at + len(word)):
                filtered.append({"field": "residence", "text": word, "reason": reason, "line": _short(line, 80)})
            else:
                mentioned = True
            continue
        for name, start, end in line_regions:
            if reason := _skip_reason(lines, i, start, end):
                filtered.append({"field": "residence", "text": name, "reason": reason, "line": _short(line, 80)})
                continue
            if name not in regions:
                regions.append(name)
            evidence = evidence or _short(line)
    if regions:
        return ", ".join(regions), False, evidence, filtered

    name = extract_name(title)
    title_regions = _find_regions(name)
    if title_regions:
        region = title_regions[0][0]
        sure = bool(_TITLE_RESIDENT.match(name[title_regions[0][2] :]))
        return region, not sure, _short(title), filtered
    return None, mentioned, None, filtered


# ── 그 외 조건 (문장형) ──
# 학년·성적·소득·학과·거주지처럼 값으로 바꿀 수 없는 조건("징계사실이 없는 자", "북한이탈청소년")은
# 해석하지 않고 원문 문장을 그대로 목록에 담는다. 화면에서는 필터에 쓰지 않고 읽기용으로 보여 준다.

_COND_LEVEL_DIGIT = re.compile(r"^\s*\d+\s*[.)]\s*")  # "4. 지원자격"
_COND_LEVEL_LETTER = re.compile(r"^\s*[가-하]\s*[.):]\s*")  # "나. 자격조건:"
_COND_MARK = re.compile(r"^\s*(\d+\s*\)|[-•○▶►·※*★☆]|[①-⑳])\s*")  # "○ …", "- …", "1) …"
_RANK_HEAD = re.compile(r"^\d+\s*순위")  # "1순위: …"는 이름표를 떼지 않는다 (순서가 내용이다)
_TRIVIAL_PART = re.compile(r"^(본교\s*)?(학부\s*)?(재학생|재학 중인 (대)?학생|대학생)(으로서)?$")
_STRUCTURED = [_GRADE_RANGE, _GRADE_LIST, _GPA, _SCORE, _INCOME]
_TIME_OR_DATE = re.compile(r"\d{1,2}:\d{2}|^\s*\d{1,2}\s*[./]\s*\d{1,2}\s*\(")  # "09:00", "11.10(화)" 일정 줄


def _level(line: str) -> int:
    """번호 단계: 1. → 1, 가. → 2, ○·-·※ → 3, 없음 → 4."""
    if _COND_LEVEL_DIGIT.match(line) and not re.match(r"^\s*\d+\s*\)", line):
        return 1
    if _COND_LEVEL_LETTER.match(line):
        return 2
    if _COND_MARK.match(line):
        return 3
    return 4


def _clean_condition(line: str) -> str:
    text = _COND_LEVEL_DIGIT.sub("", line)
    text = _COND_LEVEL_LETTER.sub("", text)
    text = _COND_MARK.sub("", text)
    head, sep, rest = text.partition(":")
    # "대상 : …", "성적기준 : …"의 앞 이름표를 뗀다
    if sep and len(head) <= 12 and rest.strip() and not _RANK_HEAD.match(head.strip()):
        text = rest
    return text.strip(" ,")


def _only_structured(text: str) -> bool:
    """쉼표로 나눈 조각이 모두 학년·평점·점수·소득처럼 이미 값으로 뽑는 조건이면 True."""
    parts = [p.strip() for p in re.split(r"[,，]", text) if p.strip()]
    return all(_TRIVIAL_PART.match(p) or any(r.search(p) for r in _STRUCTURED) for p in parts)


def _preference_tag(line: str) -> str | None:
    """우대·가산점·우선순위 줄이면 그 이름표를 돌려준다. 자격 조건 줄이면 None."""
    for tag, words in PREFERENCE_TAGS.items():
        if _has_any(line, words):
            return tag
    return None


def extract_other_conditions(body: str) -> list[str]:
    """'지원자격', '선발대상', '우대사항' 같은 제목 아래 문단에서 값으로 못 바꾸는 조건 문장을 뽑는다.

    자격 조건은 문장 그대로, 우대·가산점·우선순위는 "우대: …", "가산점: …", "우선순위: 1순위: …"처럼
    앞에 이름표를 붙여 같은 목록에 담는다. 이름표가 없는 문장만 꼭 갖춰야 하는 조건이다.
    """
    lines = _lines(body)
    results: list[str] = []
    heads = CONDITION_HEAD_WORDS + PREFERENCE_HEAD_WORDS
    i = 0
    while i < len(lines):
        line = lines[i]
        # 긴 안내 문장 속 "선발기준에 적합한 학생은…"과 "제출서류(가산점 증빙서류 외 …)"는 문단 제목이 아니다
        if (not _has_any(line, heads) or (":" not in line and len(line) > 40)
                or _has_any(line, CONDITION_NOT_WORDS)):
            i += 1
            continue
        block_tag = _preference_tag(line) if _has_any(line, PREFERENCE_HEAD_WORDS) else None
        head_level = _level(line)
        block = [line]
        j = i + 1
        while j < len(lines) and len(block) < CONDITION_BLOCK_MAX:
            nxt = lines[j]
            lv = _level(nxt)
            # 제목과 같거나 더 높은 단계의 번호가 나오면 다음 항목이다. (○·- 단계 제목이면 다음 ○·-에서 끝)
            if lv <= head_level and not (head_level == 4 and lv == 4):
                break
            if _has_any(nxt, heads) and lv <= 2:
                break
            block.append(nxt)
            j += 1
        # 쉼표로 끝난 줄은 다음 줄과 한 문장이다 ("…북한이탈청소년으로," + "2027년 … 대학생")
        merged: list[str] = []
        for raw in block:
            if merged and merged[-1].endswith(",") and _level(raw) == 4:
                merged[-1] = merged[-1] + " " + raw
            else:
                merged.append(raw)
        prev_tag: str | None = None
        for raw in merged:
            # 이 줄의 이름표: 줄에 우대·가산·순위 말이 있으면 그것, 번호 없이 앞 줄에 이어 쓴 줄이면 앞 줄 것,
            # 아니면 문단 제목의 이름표 ("우대사항" 문단 아래 줄은 모두 우대)
            tag = _preference_tag(raw) or (prev_tag if _level(raw) == 4 else None) or block_tag
            prev_tag = tag
            # 문단 제목만 있는 줄 ("4. (재단)지원자격", "- 우대 사항:", "신청대상 및 제출서류")
            if _has_any(raw, heads) and not _clean_condition(raw).strip(":"):
                continue
            if _has_any(raw, heads) and ":" not in raw and not tag:
                continue
            # 신청 방법·서류·일정 안내 줄
            if _has_any(raw, CONDITION_NOT_WORDS) or _TIME_OR_DATE.search(raw):
                continue
            if raw.startswith(("►", "▶")) and len(raw) < 15:  # "► 일반(대학생)" 같은 구분 이름표
                continue
            text = _clean_condition(raw)
            if ":" in raw and "제외" in raw.split(":")[0] and not text.startswith("제외"):
                text = "제외: " + text  # "제외 대상 : …"
            if len(text) < 6 or (not tag and ("아래" in text or _only_structured(text))):
                continue
            if tag and _has_any(text, PREFERENCE_HEAD_WORDS) and text.endswith((")", ":")) and len(text) < 40:
                continue  # "교내 선발우선순위(지원자가 선발인원보다 많을 경우)" 같은 문단 제목
            if tag and not text.startswith(tag):
                text = f"{tag}: {text}"
            text = _short(text, CONDITION_MAX)
            if text not in results:
                results.append(text)
        i = j
    return results[:CONDITION_LIST_MAX]


# ── 첨부 텍스트 ──
# 크롤러가 넣어 준 attachments[].text를 본문과 같은 규칙에 넣을 수 있게 다듬는다.

_SPACED = re.compile(r"(?<![가-힣])((?:[가-힣] ){1,}[가-힣])(?![가-힣])")  # PDF의 "선 발 대 상"
_TABLE_RULE = re.compile(r"^\s*\|(\s*:?-+:?\s*\|)+\s*$")  # 마크다운 표의 "| --- | --- |" 줄


def is_form_attachment(name: str) -> bool:
    """신청서·동의서 같은 양식 첨부인지. 이름에 '공고·안내'가 있으면 공고문으로 본다."""
    return _has_any(name, FORM_ATTACHMENT_WORDS) and not _has_any(name, NOTICE_ATTACHMENT_WORDS)


def is_ignored_attachment(name: str) -> bool:
    """자주 묻는 질문·매뉴얼처럼 예시 숫자가 많아 값을 뽑으면 안 되는 첨부인지."""
    return _has_any(name, IGNORED_ATTACHMENT_WORDS)


def prepare_attachment_text(text: str) -> str:
    """'선 발 대 상' → '선발대상', 표 구분선 줄 삭제, 표 칸 '|'는 줄 안의 구분으로 둔다."""
    # 일부 PDF는 띄어쓰기를 \x00으로, 한글 문서는 전각·줄바꿈 없는 공백으로 넣는다
    text = re.sub(r"[\x00 　 -​]", " ", text)
    lines = []
    for line in text.splitlines():
        if _TABLE_RULE.match(line):
            continue
        line = _SPACED.sub(lambda m: m.group(1).replace(" ", ""), line)
        line = line.strip().strip("|").strip()
        lines.append(line)
    return "\n".join(lines)


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
    """'면접'이 나오고 바로 뒤에 '없음, 생략, 실시하지 않음'이 없으면 면접 있음."""
    if not body.strip():
        return None
    for m in re.finditer("면접", body):
        after = body[m.end() : m.end() + INTERVIEW_AFTER].split("\n")[0]
        if not _has_any(after, INTERVIEW_NEG_WORDS):
            return True
    return False


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
    # 목록 기호로 시작하는 줄, 구분선, "선발 완료" 같은 상태 알림 줄은 요약으로 쓰지 않는다
    lines = [line for line in _lines(body)
             if len(line) >= 10 and not line.startswith(SUMMARY_SKIP_STARTS) and "---" not in line]
    if lines:
        preferred = [line for line in lines if _has_any(line, ["선발", "모집", "지원", "장학"])]
        return _short((preferred or lines)[0], SUMMARY_MAX)
    if has_images:
        return "본문 없이 포스터 이미지로 안내된 공지입니다. 원문을 확인하세요."
    if attachment_count:
        return "내용이 첨부파일에 있습니다. 원문을 확인하세요."
    return "본문이 없습니다. 원문을 확인하세요."
