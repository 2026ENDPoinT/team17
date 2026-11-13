"""의미 분석의 속성 계산 (L-attributed SDD). 입력: 한 줄 글자 + 게시일 / 출력: 속성이 붙은 기간 구·금액 구.

lexer.py가 토큰을, phrases.py가 구(문법 트리의 마디)를 만들면, 이 파일이 구마다 속성을 계산한다.
  상속 속성 (↓): 왼쪽 형제나 부모에서 받는 값.   예: 연도 없는 날짜는 왼쪽 날짜의 연도를 받는다.
  합성 속성 (↑): 자기 자식에서 올라오는 값.     예: 기간의 마감일은 끝 날짜에서 올라온다.
상속 속성이 모두 왼쪽에서만 오므로(L-attributed) 줄을 왼쪽에서 오른쪽으로 한 번 읽으면 모든 속성이 정해진다.
오른쪽 값을 기다려야 하는 속성은 두지 않는다.

기간 (마감일)   줄 → 항목+     항목 → 앞이름표 기간 뒷이름표?     기간 → 시작날짜? ~ 끝날짜
  항목.label    ↓  앞 기간이 끝난 곳부터 이 기간 시작까지의 글자 ("대출실행기간: ")
  항목.post     ↑  기간 바로 뒤부터 구분 기호(, ; | ( [)까지의 이름표 토큰 ("7. 20. 발표", "10. 1. 이후 발급").
                   구분 기호보다 다음 기간이 먼저 오면 그 말은 다음 항목의 앞이름표라서 쓰지 않는다
                   ("7. 30. 면접 8. 3."의 "면접"은 8/3의 이름표). 어느 항목에 붙는지는 구문이 정하는 일이라 L-attributed를 깨지 않는다
  항목.applies  ↑  신청 기간으로 쓸 수 있는지. 순서대로 본다
                   1) 앞이름표에 APPLY·OTHER 토큰이 있으면 가장 가까운 것 (APPLY면 True: "합격자 발표 후 서류 제출: 8.20")
                   2) 앞이름표에 (요일 "(수)"를 빼고) 한글이 있으면 True, 한글이 없으면 앞 항목의 값을 이어받는다 (↓)
                   3) 뒷이름표: REF("이후·이전·기준")면 False. 앞이름표 토큰이 없을 때만 OTHER면 False, APPLY면 True
  날짜.year     ↓  적힌 연도(오타면 게시 연도) → 왼쪽 날짜의 연도 → 게시 연도 (게시일보다 60일 넘게 앞이면 다음 해)
  날짜.prev     ↓  바로 왼쪽 날짜. 왼쪽에 연도가 적혀 있고 연도 없는 날짜가 그보다 180일 넘게 앞이면 해를 넘긴 것이다
                   ("2026. 12. 20. ~ 1. 5.")
  날짜.fixed    ↓  이 날짜, 또는 연도를 물려준 왼쪽 날짜의 연도 오타를 고쳤는지
  일만 쓴 끝    ↓  "8. 13. ~ 14."의 14는 시작 날짜의 달·연도를 받는다 (시작보다 작으면 다음 달)
  기간.date     ↑  끝 날짜 (끝이 없으면 그 날짜 하나)
  줄.deadline   ↑  applies인 항목 중 마지막 기간. 하나도 없으면 이 줄에는 마감이 없다

금액   항목 → 앞말 금액 뒷말
  금액.pre      ↓  금액 앞 CONTEXT_BEFORE자. 앞 금액이 그 안에서 끝나면 앞 금액이 끝난 곳부터 ("예산 500만원, 1인 100만원")
  금액.income   ↓  왼쪽에 소득 말("소득", "차상위" …)이 나왔는지. 나왔으면 뒤 금액은 소득 기준일 수 있다
  금액.counted  ↓  표 행("|")이고 왼쪽에 "10명"처럼 인원이 있는지 ("인당"이 없을 때). 있으면 인원 전체 예산이다
  항목.post     ↑  금액 뒤 CONTEXT_AFTER자. "(", ",", "|"에서 끊는다 ("100만원(평점 3.0 이상)"의 "이상"은 금액 조건이 아니다)
  항목.role     ↑  위 속성으로 정한 쓰임: "지급"이면 1인당 장학금, 아니면 쓰지 않는 이유
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta

from config import (
    AMOUNT_AFTER_SKIP,
    AMOUNT_BEFORE_SKIP,
    AMOUNT_MAX_PER_PERSON,
    CONTEXT_AFTER,
    CONTEXT_BEFORE,
    DEADLINE_YEAR_GAP,
    INCOME_WORDS,
    PERIOD_OTHER_WORDS,
)
from lexer import Token, tokenize
from phrases import Amount, Period, amounts, periods

ROLLOVER_DAYS = 60  # 연도 없는 날짜가 게시일보다 이만큼 넘게 앞이면 다음 해다 (12월 글의 "~1/10")
BACKWARD_DAYS = 180  # 연도 없는 날짜가 왼쪽 날짜보다 이만큼 넘게 앞이면 다음 해다 ("2026. 12. 20. ~ 1. 5.")
_WEEKDAY = re.compile(r"\(\s*[월화수목금토일](?:요일)?\s*\)")  # 이름표에 남은 요일 "(수)"는 이름표 글자가 아니다
_POST_END = re.compile(r"[(（,，|]")  # 뒷말은 괄호·쉼표·표 칸에서 끊는다
_LABEL_STOP = re.compile(r"[(（\[,，;|‖]")  # 기간의 뒷이름표는 이 기호 앞까지
POST_LABEL_MAX = 10  # 기간 뒤 몇 글자까지 뒷이름표로 볼지
_LABEL_KINDS = ("APPLY", "OTHER")
MIN_HOURLY = 5_000  # 시급 최저값 (rules.py의 시급 대체 찾기도 쓴다)
_MIN_VALUE = {"lump_sum": 10_000, "hourly": MIN_HOURLY, "tuition_ratio": 1}  # "1원", "3원"처럼 금액일 수 없는 값
# 1인당 장학금으로 보기에 너무 큰 금액은 총 예산이다 ("우수장학금 | 대학생 | 115명 | 180백만원", raw_test 894772)
_MAX_VALUE = {"lump_sum": AMOUNT_MAX_PER_PERSON, "hourly": 100_000, "tuition_ratio": 100}


def _has_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def _has_hangul(text: str) -> bool:
    return any("가" <= ch <= "힣" for ch in text)


# ── 기간 ──


@dataclass
class DatedPeriod:
    """속성이 붙은 기간 구."""

    period: Period
    label: str  # ↓ 이름표
    applies: bool  # ↓ 신청 기간으로 쓸 수 있는지
    date: date | None  # ↑ 끝 날짜 (날짜를 못 만들면 None)
    fixed: bool  # ↓ 연도 오타를 고친 날짜인지
    apply_label: bool = False  # ↑ 앞뒤 이름표에 신청 말(APPLY)이 있어 신청 기간으로 정해졌는지


@dataclass
class _DateContext:
    """왼쪽에서 오른쪽으로 읽으며 넘겨주는 상속 속성."""

    year: int | None = None  # 왼쪽 날짜에 적힌 연도 (오타면 고친 연도)
    fixed: bool = False  # 그 연도가 오타를 고친 것인지
    applies: bool = True  # 앞 항목의 applies
    prev: date | None = None  # 바로 왼쪽 날짜
    prev_end: int = 0  # 앞 기간이 끝난 위치


def year_typo_fixed(value: date, posted: date) -> date | None:
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


def _date_of(token: Token, ctx: _DateContext, posted: date) -> tuple[date | None, bool]:
    """DATE 토큰의 날짜. ctx(왼쪽에서 받은 연도)를 쓰고, 적힌 연도가 있으면 ctx를 바꿔 오른쪽에 넘긴다."""
    y, month, day = token.value
    if y:
        ctx.year, ctx.fixed = y, False
    try:
        value = date(ctx.year or posted.year, month, day)
    except ValueError:
        return None, False
    if y and (fixed := year_typo_fixed(value, posted)):
        value = fixed
        ctx.year, ctx.fixed = fixed.year, True  # 오른쪽의 연도 없는 날짜도 고친 연도를 받는다
    if ctx.year is None and value < posted - timedelta(days=ROLLOVER_DAYS):
        value = value.replace(year=value.year + 1)
    elif not y and ctx.year is not None and ctx.prev and (ctx.prev - value).days > BACKWARD_DAYS:
        # 왼쪽에 연도가 적혀 있을 때만 쓴다. 연도가 없으면 게시일 기준 규칙이 해를 정한다
        # (번호 "2. 3."을 날짜로 잘못 읽어 다음 해가 되면, 오른쪽 진짜 날짜까지 다음 해로 밀리던 것을 막는다)
        value = _next_year(value) or value
    ctx.prev = value
    return value, ctx.fixed


def _next_year(value: date) -> date | None:
    try:
        return value.replace(year=value.year + 1)
    except ValueError:  # 2월 29일
        return None


def _day_end(begin: date, end: Token) -> date | None:
    """일만 쓴 끝 날짜 ("8. 13. ~ 14."의 14): 달은 구문 분석이 정했고, 연도는 시작 날짜에서 받는다."""
    _, month, day = end.value
    try:
        return date(begin.year + (1 if month < begin.month else 0), month, day)
    except ValueError:
        return None


def dated_periods(line: str, posted: date, tokens: list[Token] | None = None) -> list[DatedPeriod]:
    """줄의 기간 구마다 속성을 계산한다. 왼쪽에서 오른쪽으로 한 번 읽는다."""
    tokens = tokenize(line) if tokens is None else tokens
    ctx = _DateContext()
    result: list[DatedPeriod] = []
    found = periods(tokens)
    for i, p in enumerate(found):
        label = line[ctx.prev_end : p.first]
        # 앞이름표는 같은 표 칸 안에서만 찾는다 ("… 제출한 자격증 | … 2026. 3. 3."의 "제출"은 다른 칸의 말이다)
        cell_start = line.rfind("|", ctx.prev_end, p.first) + 1
        pre = [t for t in tokens if t.kind in _LABEL_KINDS and max(ctx.prev_end, cell_start) <= t.start < p.first]
        post, post_end = _post_labels(line, tokens, p, found[i + 1].first if i + 1 < len(found) else None)
        if pre:
            applies = pre[-1].kind == "APPLY"
        elif _has_hangul(_WEEKDAY.sub("", label)):
            applies = not _has_any(label, PERIOD_OTHER_WORDS)
        else:
            applies = ctx.applies
        if "REF" in post:
            applies = False
        elif not pre and "OTHER" in post:
            applies = False
        elif not pre and "APPLY" in post:
            applies = True
        begin, begin_fixed = _date_of(p.start, ctx, posted) if p.start is not None else (None, False)
        if p.end is None:  # "~ 선발완료 시까지"
            value, fixed = None, begin_fixed
        elif p.day_only:
            value, fixed = (_day_end(begin, p.end) if begin else None), begin_fixed
            ctx.prev = value or ctx.prev
        else:
            value, fixed = _date_of(p.end, ctx, posted)
        apply_label = applies and ((bool(pre) and pre[-1].kind == "APPLY") or (not pre and "APPLY" in post))
        result.append(DatedPeriod(p, label, applies, value, fixed or begin_fixed, apply_label))
        ctx.applies, ctx.prev_end = applies, post_end  # 뒷이름표로 쓴 말은 다음 항목의 이름표에 넣지 않는다
    return result


def _post_labels(line: str, tokens: list[Token], p: Period, next_first: int | None) -> tuple[list[str], int]:
    """항목.post: 기간 바로 뒤 이름표 토큰의 종류와, 뒷이름표가 끝난 위치. 구분 기호나 다음 기간 전까지만 본다."""
    end = min(p.last + POST_LABEL_MAX, len(line))
    stop = _LABEL_STOP.search(line, p.last, end)
    end = stop.start() if stop else end
    if next_first is not None and next_first <= end:  # 다음 기간이 먼저 온다: 뒤의 말은 다음 항목의 앞이름표다
        return [], p.last
    found = [t for t in tokens if t.kind in _LABEL_KINDS + ("REF",) and p.last <= t.start < end]
    return [t.kind for t in found], (found[-1].end if found else p.last)


def has_apply_period(line: str, posted: date) -> bool:
    """줄에 신청 말 이름표가 붙은 기간이 있는지 ("6. 제출 기간: 9. 22.", "(지원서 접수) 10. 5. ~ 10. 18.")."""
    return any(d.apply_label for d in dated_periods(line, posted))


def line_deadline(items: list[DatedPeriod], fallback: bool = False) -> DatedPeriod | None:
    """줄.deadline ↑: 신청 기간으로 쓸 수 있는 항목 중 마지막. 없으면 None (발표일·근무기간만 있는 줄).

    fallback: 하나도 없으면 마지막 기간을 쓴다. 제목에 쓴다. 제목의 "(~7/10까지)"는 이름표가
    "지급요청서 작성 요청"처럼 다른 일정 말을 품어도 마감이다 (891758, 894077).
    """
    applying = [d for d in items if d.applies]
    if applying:
        return applying[-1]
    return items[-1] if fallback and items else None


# ── 금액 ──


@dataclass
class RoledAmount:
    """속성이 붙은 금액 구."""

    amount: Amount
    pre: str  # ↓ 앞말
    post: str  # ↑ 뒷말
    role: str  # ↑ "지급" 또는 쓰지 않는 이유


def _role(a: Amount, pre: str, post: str, income: bool, counted: bool) -> str:
    """항목.role ↑. 앞말·뒷말·상속 속성으로 이 금액의 쓰임을 정한다."""
    if income:
        return "소득 기준 (왼쪽에 소득 말)"
    if not _MIN_VALUE[a.kind] <= a.value <= _MAX_VALUE[a.kind]:
        return "금액 범위 밖"
    if counted:
        return "인원 전체 예산 (표 행)"
    for word in AMOUNT_BEFORE_SKIP:
        if word in pre:
            return f"앞에 '{word}'"
    for word in AMOUNT_AFTER_SKIP:
        if word in post:
            return f"뒤에 '{word}'"
    return "지급"


def roled_amounts(line: str, tokens: list[Token] | None = None) -> list[RoledAmount]:
    """줄의 금액 구마다 속성을 계산한다. 왼쪽에서 오른쪽으로 한 번 읽는다."""
    tokens = tokenize(line) if tokens is None else tokens
    income_at = min((line.find(w) for w in INCOME_WORDS if w in line), default=len(line))
    is_table = any(t.kind == "CELL" for t in tokens) and "인당" not in line
    result: list[RoledAmount] = []
    prev_last = 0  # 앞 금액이 끝난 위치
    for a in amounts(tokens):
        pre = line[max(prev_last, a.first - CONTEXT_BEFORE) : a.first]
        post = _POST_END.split(line[a.last : a.last + CONTEXT_AFTER], maxsplit=1)[0]
        prev_last = a.last
        counted = is_table and re.search(r"\d+\s*명", line[: a.first]) is not None
        role = _role(a, pre, post, income=a.first >= income_at, counted=counted)
        result.append(RoledAmount(a, pre, post, role))
    return result


def show(line: str, posted: date | None = None) -> str:
    """디버그용: 줄의 기간·금액 속성을 사람이 읽을 수 있게 보여 준다."""
    posted = posted or date.today()
    out = []
    for d in dated_periods(line, posted):
        out.append(f"기간 {line[d.period.first : d.period.last]!r} label={d.label!r} applies={d.applies} "
                   f"date={d.date} fixed={d.fixed} rolling={d.period.rolling} open={d.period.open}")
    for r in roled_amounts(line):
        out.append(f"금액 {line[r.amount.first : r.amount.last]!r} {r.amount.kind}={r.amount.value} "
                   f"pre={r.pre!r} post={r.post!r} role={r.role}")
    return "\n".join(out)
