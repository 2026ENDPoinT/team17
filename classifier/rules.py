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
    AMOUNT_MAX_PER_PERSON,
    CLOSED_WORDS,
    COND_AFTER_SKIP,
    COND_BEFORE_SKIP,
    CONDITION_BLOCK_MAX,
    CONDITION_HEAD_WORDS,
    CONDITION_MAX,
    CONDITION_NOT_WORDS,
    CONTEXT_AFTER,
    CONTEXT_BEFORE,
    CONTINUATION_MARKS,
    DEADLINE_LINE_WORDS,
    DEADLINE_SKIP_WORDS,
    DEADLINE_YEAR_GAP,
    DEPARTMENT_LINE_WORDS,
    DOCUMENT_HEAD_WORDS,
    DOCUMENT_SKIP_WORDS,
    DOCUMENT_WORDS,
    ELIGIBILITY_LINE_WORDS,
    EVIDENCE_MAX,
    EXCLUDE_AFTER_WORDS,
    EXTERNAL_WORDS,
    FORM_ATTACHMENT_WORDS,
    GRADE_SYSTEM_WINDOW,
    IGNORED_ATTACHMENT_WORDS,
    INCOME_WORDS,
    INFO_WORDS,
    INTERVIEW_AFTER,
    INTERVIEW_NEG_WORDS,
    LINE_HEAD_SKIP,
    MAX_GRADE,
    MULTI_AMOUNT_WORDS,
    NO_LIMIT_WORDS,
    NOT_CONDITION_WORDS,
    NOTICE_ATTACHMENT_WORDS,
    PERIOD_OTHER_WORDS,
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
    UPDATE_WORDS,
    WORK_BNUMS,
    WORK_WORDS,
)
from dictionary import COLLEGES, DEPARTMENTS, FIELDS, NOT_REGION, SIDO, SIGUNGU
from lexer import Token, tokenize
from phrases import amounts, periods


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


# 이름표 뒤의 콜론. 시각의 콜론("15:00")은 이름표가 아니라서 숫자 사이의 콜론은 건너뛴다
_LABEL_COLON = re.compile(r"(?<!\d)[:：]|[:：](?!\d)")


def _after_colon(line: str) -> str:
    """'다. 지원금액: 300만원' → '300만원'. 콜론이 없으면 줄 그대로.

    "2026. 9. 24.(목) 15:00까지"처럼 시각의 콜론만 있으면 자르지 않는다 (예전에는 "00까지"가 됐다).
    """
    parts = _LABEL_COLON.split(line, maxsplit=1)
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


def classify_label(title: str, notice_kind: str) -> tuple[str | None, str]:
    """공지 하나의 라벨: 모집 / 수정 / 완료. 반환: (라벨, 이유). 장학금 공지가 아니면 (None, 이유).

    이벤트 묶기 단계가 같은 장학금의 공지들(모집 → 수정 → 완료)을 묶고 "마지막 공지"로 상태를 정한다.
    그래서 공지 하나에 여러 신호가 있으면 더 나중 상태를 고른다: 완료 > 수정 > 모집.
    예: "(신청기간 연장) … 선발 안내(선발완료)"는 연장도 있지만 지금 상태는 완료다.
    """
    if notice_kind == "결과":  # 지급완료, 선발 결과, 합격자 …
        return "완료", "결과 공지"
    if notice_kind != "모집":  # 안내(서약서·지급 일정 …), 확인필요(장학금인지 모름)
        return None, f"공지 종류가 '{notice_kind}'"
    if word := next((w for w in CLOSED_WORDS if w in title), None):
        return "완료", f"제목에 '{word}'"
    if word := next((w for w in UPDATE_WORDS if w in title), None):
        return "수정", f"제목에 '{word}'"
    return "모집", "모집 공지"


# ── 유형 ──


def classify_category(title: str, bnum: int) -> str:
    """교내 / 교외 / 근로."""
    if bnum in WORK_BNUMS or _has_any(title, WORK_WORDS):
        return "근로"
    if _has_any(title, EXTERNAL_WORDS):
        return "교외"
    return "교내"


# ── 장학금 이름 ──

_LEAD_TAG = re.compile(r"^\s*(\([^)]*\)|\[[^\]]*\]|[☆★※◆■□▶►·•]+)\s*")  # 앞의 (홍보), [부서], ☆
_TAIL_PAREN = re.compile(r"\s*\((?:[^()]|\([^()]*\))*\)\s*$")  # 끝의 (마감), (~11/11(수)까지)
_TAIL_DONE = re.compile(r"\s*[_\-]\s*(모집완료|선발완료|마감)\s*$")  # 끝의 "_모집완료"
_TAIL_OPEN = re.compile(r"\s*\([^()]*$")  # 목록에서 잘린 제목의 닫히지 않은 괄호 "… 안내(8/24"
# 꼬리 말을 지운 뒤에 드러난 괄호는 상태·날짜일 때만 지운다. "모집(교체선발)"은 지우고 "장학생(ST근로)"는 둔다
_TAIL_STATUS_PAREN = re.compile(r"\s*\([^()]*(마감|완료|~|까지|\d+\s*/\s*\d+|교체|선발|모집|신규|추가)[^()]*\)\s*$")
# 끝의 공지 말. 하나 지우면 또 남을 수 있어서 ("모집 공고 안내") 더 지울 게 없을 때까지 반복한다
_TAIL_WORDS = re.compile(r"\s*((선발|모집|신청|접수)\s*(안내|공고)|신청\s*(기간|절차)|안내|공고|모집|선발|신청|접수)\s*$")
_NAME_MIN = 4  # 이름이 이보다 짧아지면 더 지우지 않는다 ("장학생 모집"을 "장학생"보다 짧게 만들지 않게)


def extract_name(title: str) -> str:
    """제목 앞의 (홍보)·[부서]·☆ 표시와 끝의 (마감)·(~11/11까지)·_모집완료·"모집 공고 안내"를 떼어 장학금 이름을 만든다.

    예: "(홍보) 포스코청암재단 비전장학생 모집 공고 안내(마감)" → "포스코청암재단 비전장학생"
    """
    name = title
    while _LEAD_TAG.match(name):
        name = _LEAD_TAG.sub("", name, count=1)
    # 1) 원래 제목 끝의 괄호는 모두 지운다 ("(마감)", "(~11/11(수)까지)", "(학습도우미, 마감)")
    name = _TAIL_OPEN.sub("", name)
    while _TAIL_PAREN.search(name):
        name = _TAIL_PAREN.sub("", name)
    # 2) 꼬리 말을 하나씩 지운다. 지운 뒤 드러난 괄호는 상태·날짜일 때만 지운다
    while True:
        before = name
        name = _TAIL_STATUS_PAREN.sub("", name)
        name = _TAIL_DONE.sub("", name)
        shorter = _TAIL_WORDS.sub("", name)
        if len(shorter.strip()) >= _NAME_MIN:
            name = shorter
        if name == before:
            break
    return name.strip() or title.strip()


# ── 금액 (의미 분석) ──
# 어휘 분석(lexer.py)이 "5백만 원", "시간 당 10,320원", "수업료 100%"를 토큰으로, 구문 분석(phrases.py)이 금액 구로 만든다.
# 여기서는 "이 금액 구가 1인당 장학금인가"를 정한다: 소득 기준·예산·계산 예시·기준 금액을 거르고, 대상별이면 대학생 것을 고른다.

_KIND_ORDER = {"tuition_ratio": 0, "hourly": 1, "lump_sum": 2}  # 한 줄에 여러 종류면 등록금 비율 → 시급 → 금액 순으로 본다
_MIN_VALUE = {"lump_sum": 10_000, "hourly": 5_000, "tuition_ratio": 1}  # "1원", "3원"처럼 금액일 수 없는 값은 버린다
# 1인당 장학금으로 보기에 너무 큰 금액은 총 예산이다 ("우수장학금 | 대학생 | 115명 | 180백만원", raw_test 894772)
_MAX_VALUE = {"lump_sum": AMOUNT_MAX_PER_PERSON, "hourly": 100_000, "tuition_ratio": 100}


def _amount_from_line(line: str) -> dict | None:
    """한 줄의 금액 구 중 장학금 금액을 고른다.

    소득 단어("차상위", "소득")보다 뒤에 나오는 금액은 소득 기준일 수 있어서 쓰지 않는다.
    예: "수업료 100% 면제(단, 차상위~5구간 … 50%만 면제)" → 100%를 쓴다.
    """
    income_at = min((line.find(w) for w in INCOME_WORDS if w in line), default=len(line))
    tokens = tokenize(line)

    def table_total(a) -> bool:
        # 표 행 "재능장학금 | 대학생 | 10명 | 10백만원"의 금액은 인원 전체의 예산이다 ("인당"이 있으면 1인당)
        return (any(t.kind == "CELL" for t in tokens) and "인당" not in line
                and re.search(r"\d+\s*명", line[: a.first]) is not None)

    ok = [a for a in amounts(tokens)
          if a.first < income_at and _MIN_VALUE[a.kind] <= a.value <= _MAX_VALUE[a.kind]
          and not table_total(a)
          and not _context_skip(line, a.first, a.last, AMOUNT_BEFORE_SKIP, AMOUNT_AFTER_SKIP)]
    if not ok:
        return None
    kind = min((a.kind for a in ok), key=_KIND_ORDER.__getitem__)
    same = [a for a in ok if a.kind == kind]
    # "고등학생 50만원, 대학생 최대 100만원"이면 대학생 금액, "연간 최대 5백만 원 (학기당 250만원)"이면 학기당 금액
    pick = (next((a for a in same if "대학" in line[max(0, a.first - CONTEXT_BEFORE) : a.first]), None)
            or next((a for a in same if a.per == "학기"), None)
            or same[0])
    return {"type": pick.kind, "value": pick.value, "text": line[pick.first : pick.last].strip()}


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
    # 2) 근로 공지는 시급이 금액 단어 없이 나오기도 한다 ("1일 최대 8시간 (… 시간 당 10,320원)")
    for line in lines:
        hourly = [a for a in amounts(tokenize(line)) if a.kind == "hourly" and a.value >= _MIN_VALUE["hourly"]]
        if hourly:
            a = hourly[0]
            return {"type": "hourly", "value": a.value, "text": line[a.first : a.last].strip()}, _short(line)
    return {"type": "unknown", "value": None, "text": None}, None


# ── 마감일 (의미 분석) ──
# 어휘 분석(lexer.py)이 날짜·시각·"~"·"선발완료 시"를 토큰으로 만들고, 구문 분석(phrases.py)이 기간 구로 묶는다.
# 여기서는 "어느 줄의 어느 기간이 신청 마감인가"와 "연도가 없는 날짜의 연도"만 정한다.

YEAR_FIX_NOTE = "원문 연도를 게시 연도로 고침"  # deadline_text에 붙는 표시. extract.py가 보고 확인 필요로 표시한다
OPEN_END_NOTE = "끝 날짜가 적혀 있지 않음"  # "6. 8.(월) 10:00 ~": 시작일일 수 있다


def _year_typo_fixed(value: date, posted: date) -> date | None:
    """원문에 적힌 연도가 오타로 보이면 게시 연도로 고친 날짜를, 아니면 None을 돌려준다.

    예: 2026년 9월 게시글의 "신청기간 : 2025. 9. 30. ~ 10. 5." (896003), 2026년 8월 게시글의 "2027. 8. 24." (894168).
    적힌 연도로는 게시일과 180일 넘게 떨어져 있고, 게시 연도로 바꾸면 게시일 30일 전 ~ 120일 뒤에 들어오면 오타로 본다.
    """
    if abs((value - posted).days) <= DEADLINE_YEAR_GAP:
        return None
    try:
        fixed = value.replace(year=posted.year)
    except ValueError:  # 2월 29일
        return None
    return fixed if -30 <= (fixed - posted).days <= 120 else None


def _resolve_dates(tokens: list[Token], posted: date) -> tuple[dict[int, date], bool]:
    """줄의 DATE 토큰마다 실제 날짜를 정한다. 반환: ({토큰 위치: 날짜}, 연도 오타를 고쳤는지).

    연도가 없으면 앞 날짜의 연도, 그것도 없으면 게시일 기준으로 정한다 (12월 글의 "~1/10"은 다음 해).
    """
    resolved: dict[int, date] = {}
    year: int | None = None
    fixed_any = False
    for t in tokens:
        if t.kind != "DATE":
            continue
        y, mo, d = t.value
        if y:
            year = y
        use_year = year or posted.year
        try:
            value = date(use_year, mo, d)
        except ValueError:
            continue
        if y and (fixed := _year_typo_fixed(value, posted)):
            value, year, fixed_any = fixed, fixed.year, True  # 뒤에 오는 연도 없는 날짜도 고친 연도를 쓴다
        if year is None and value < posted - timedelta(days=60):
            value = value.replace(year=use_year + 1)
        resolved[t.start] = value
    return resolved, fixed_any


def _pick_period(line: str, found: list) -> object:
    """한 줄에 기간 구가 여러 개면 신청 마감에 해당하는 것을 고른다.

    각 기간 앞의 이름표(앞 기간이 끝난 곳부터 이 기간 시작까지의 글자)를 본다. 이름표에 "실행·발표·지급 …"이 있는 기간은
    신청 기간이 아니라서 뺀다. 남은 것 중 마지막을 쓴다.
      "대출신청기간: 7. 1. ~ 11. 17., 대출실행기간: 7. 1. ~ 11. 18." → 11/17 (실행기간은 뺌)
      "모집기간: 7. 3. ~ 7. 9. 7/13(월)까지 기한 연장!" → 7/13 (뒤 기간은 이름표가 없어 같은 이름표가 이어진다)
    """
    keep = []
    prev_end = 0
    for p in found:
        label = line[prev_end : p.first]
        if not _has_any(label, PERIOD_OTHER_WORDS):
            keep.append(p)
        prev_end = p.last
    return (keep or found)[-1]


def _deadline_in(line: str, posted: date) -> tuple[str, date | None, bool, bool] | None:
    """한 줄의 기간 구로 마감을 정한다.

    반환: ("date", 날짜, 연도 고침, 끝 날짜 없음) / ("rolling", None, False, False) / None.
    "8. 24. ~ 8. 31."은 끝(8/31), "~ 2026.6.22."는 그 날짜, "8. 24. ~ 선발완료 시까지"는 상시 모집이다.
    "6. 8.(월) 10:00 ~"처럼 "~" 뒤에 끝이 없으면 그 날짜를 쓰되 확인 필요로 표시한다 (시작일일 수 있다).
    """
    tokens = tokenize(line)
    found = periods(tokens)
    if not found:
        return None
    chosen = _pick_period(line, found)
    if chosen.rolling:
        return None if _has_any(line, ROLLING_SKIP_WORDS) else ("rolling", None, False, False)
    resolved, fixed = _resolve_dates(tokens, posted)
    value = resolved.get(chosen.end.start)
    if value is None and chosen.start is not None and chosen.start.start in resolved:
        # 구문 분석이 만든 끝 날짜 ("8. 13.(목) ~ 14.(금)"의 14일): 연도는 시작 날짜에서 가져온다
        begin = resolved[chosen.start.start]
        _, month, day = chosen.end.value
        try:
            value = date(begin.year + (1 if month < begin.month else 0), month, day)
        except ValueError:
            value = None
    return ("date", value, fixed, chosen.open) if value else None


def extract_deadline(title: str, body: str, posted: date) -> tuple[str | None, str | None, str | None]:
    """반환: (마감일 YYYY-MM-DD, 원문 표기, 근거 문장). 제목을 먼저 본다 (연장되면 제목이 바뀌므로).

    원문 연도 오타를 고쳤으면 원문 표기 끝에 "(원문 연도를 게시 연도로 고침)"을,
    "6. 8.(월) 10:00 ~"처럼 끝 날짜가 없으면 "(끝 날짜가 적혀 있지 않음)"을 붙인다. 둘 다 extract.py가 확인 필요로 표시한다.
    상시 모집이면 마감일은 None, 원문 표기는 "상시 모집 (…)"이다.
    """
    def note(text: str, found: tuple) -> str:
        notes = [n for n, on in [(YEAR_FIX_NOTE, found[2]), (OPEN_END_NOTE, found[3])] if on]
        return f"{text} ({', '.join(notes)})" if notes else text

    if "~" in title or "까지" in title:
        found = _deadline_in(title, posted)
        if found and found[0] == "date":
            return found[1].isoformat(), note(title, found), _short(title)
    for line in _lines(body):
        if not _has_any(line, DEADLINE_LINE_WORDS) or _has_any(line, DEADLINE_SKIP_WORDS):
            continue
        found = _deadline_in(line, posted)
        if found is None:
            continue
        if found[0] == "rolling":  # "모집기간: 2026. 8. 24. (월) ~ 선발완료 시 까지" (893917)
            return None, "상시 모집 (" + _short(_after_colon(line), 40) + ")", _short(line)
        return found[1].isoformat(), note(_short(_after_colon(line), 60), found), _short(line)
    # 날짜 없이 "선발 완료시까지"인 상시 모집: 마감일은 없지만 원문 표기는 남긴다
    for line in _lines(body):
        if (_has_any(line, ROLLING_WORDS) and _has_any(line, DEADLINE_LINE_WORDS + ["지원기간", "지원 기간"])
                and not _has_any(line, ROLLING_SKIP_WORDS)):
            return None, "상시 모집 (" + _short(_after_colon(line), 40) + ")", _short(line)
    return None, None, None


# ── 대상 조건 ──

# 앞에 숫자·한글이 붙으면 학년이 아니다: "2026학년도"의 6, "중1학년"의 1
_GRADE_RANGE = re.compile(r"(?<![\d가-힣])(\d)\s*[~\-]\s*(\d)\s*학년")
# "2, 3, 4학년", "5·6학년", "3/4학년"
_GRADE_LIST = re.compile(r"(?<![\d.가-힣])((?:\d\s*[,·/]\s*)*\d)\s*학년(?!도)")
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

    def school_grade(line: str, m: re.Match) -> bool:
        # "6년제 5·6학년, 5년제 4·5학년"처럼 다른 학제의 학년이면 쓰지 않는다 (897009). "4년제 3·4학년"은 쓴다
        before = line[max(0, m.start() - GRADE_SYSTEM_WINDOW) : m.start()]
        if _has_any(before, ["고등학교", "고교", "중학교", "초등"]):  # "고등학교 1~2학년, 대학교 1~3학년" (894206)
            return False
        system = re.search(r"(\d)\s*년제", before)
        return system is None or system.group(1) == "4"

    for line in lines:
        if result["grades"] is None:
            ranges = [m for m in ok_matches(_GRADE_RANGE, line) if school_grade(line, m)]
            singles = [m for m in ok_matches(_GRADE_LIST, line) if school_grade(line, m)]
            if ranges:
                lo, hi = int(ranges[0].group(1)), int(ranges[0].group(2))
                if 1 <= lo <= hi <= MAX_GRADE:
                    result["grades"] = list(range(lo, hi + 1))
            elif singles:
                m = singles[0]
                grades = sorted({int(g) for g in re.findall(r"\d", m.group(1))})
                tail = line[m.end() : m.end() + 4]
                if len(grades) == 1 and "이상" in tail:  # "3학년 이상" → 3~4학년
                    grades = list(range(grades[0], 5))
                elif len(grades) == 1 and "이하" in tail:  # "2학년 이하" → 1~2학년
                    grades = list(range(1, grades[0] + 1))
                if all(1 <= g <= MAX_GRADE for g in grades):
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
        # 실제 시·군·구 이름만 지역으로 본다 ("반드시", "명시", "가구"는 목록에 없다)
        if name not in SIGUNGU or name in NOT_REGION or any(s <= m.start(1) < e for _, s, e in found):
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
_COND_MARK = re.compile(r"^\s*(\d+\s*\)|[-•○◦▶►·※*★☆■□▪◆◇❍❑⦁]|[①-⑳])\s*")  # "○ …", "- …", "◦ …", "1) …"
_RANK_HEAD = re.compile(r"^\d+\s*순위")  # "1순위: …"는 이름표를 떼지 않는다 (순서가 내용이다)
_TRIVIAL_PART = re.compile(r"^(본교\s*)?(학부\s*)?(재학생|재학 중인 (대)?학생|대학생)(으로서)?$")
_STRUCTURED = [_GRADE_RANGE, _GRADE_LIST, _GPA, _SCORE, _INCOME]
_TIME_OR_DATE = re.compile(r"\d{1,2}:\d{2}|^\s*\d{1,2}\s*[./]\s*\d{1,2}\s*\(")  # "09:00", "11.10(화)" 일정 줄


LEVEL_NONE = 6  # 번호·기호가 없는 줄 (앞 줄에 이어 쓴 줄일 때가 많다)


def _level(line: str) -> int:
    """번호 단계. 한국 공문서 순서를 따른다: 1. → 1, 가. → 2, 1) → 3, 가) → 4, ○·-·※ → 5, 없음 → 6."""
    if re.match(r"^\s*\d+\s*\.", line):
        return 1
    if re.match(r"^\s*[가-하]\s*[.:]", line):
        return 2
    if re.match(r"^\s*(\d+\s*\)|[①-⑳])", line):
        return 3
    if re.match(r"^\s*[가-하]\s*\)", line):
        return 4
    if _COND_MARK.match(line):
        return 5
    return LEVEL_NONE


def strip_marks(line: str) -> str:
    """줄 앞의 번호·기호("4.", "나.", "○", "-", "1)")를 뗀다."""
    text = _COND_LEVEL_DIGIT.sub("", line)
    text = _COND_LEVEL_LETTER.sub("", text)
    return _COND_MARK.sub("", text)


# parser.py가 쓰는 이름 (rules.py 안에서는 밑줄 붙은 이름을 쓴다)
def level(line: str) -> int:
    return _level(line)


def lines_of(text: str) -> list[str]:
    return _lines(text)


def _clean_condition(line: str) -> str:
    text = strip_marks(line)
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


def conditions_from_block(block: list[str], block_tag: str | None) -> list[str]:
    """자격·우대 문단 하나(parser.py가 나눈 Section의 줄)에서 값으로 못 바꾸는 조건 문장을 뽑는다.

    자격 조건은 문장 그대로, 우대·가산점·우선순위는 "우대: …", "가산점: …", "우선순위: 1순위: …"처럼
    앞에 이름표를 붙인다. 이름표가 없는 문장만 꼭 갖춰야 하는 조건이다.
    block_tag: 우대·우선순위 문단이면 그 이름표 (문단 안 줄에 기본으로 붙는다), 자격 문단이면 None.
    """
    results: list[str] = []
    heads = CONDITION_HEAD_WORDS + PREFERENCE_HEAD_WORDS
    # 쉼표로 끝난 줄은 다음 줄과 한 문장이다 ("…북한이탈청소년으로," + "2027년 … 대학생")
    merged: list[str] = []
    for raw in block[:CONDITION_BLOCK_MAX]:
        if merged and merged[-1].endswith(",") and _level(raw) == LEVEL_NONE:
            merged[-1] = merged[-1] + " " + raw
        else:
            merged.append(raw)
    prev_tag: str | None = None
    for raw in merged:
        # 이 줄의 이름표: 줄에 우대·가산·순위 말이 있으면 그것, 번호 없이 앞 줄에 이어 쓴 줄이면 앞 줄 것,
        # 아니면 문단 제목의 이름표 ("우대사항" 문단 아래 줄은 모두 우대)
        tag = _preference_tag(raw) or (prev_tag if _level(raw) == LEVEL_NONE else None) or block_tag
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
    return results


def preference_tag(line: str) -> str | None:
    return _preference_tag(line)


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
