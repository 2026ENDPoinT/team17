"""의미 분석의 속성 계산 (L-attributed SDD). 입력: 한 줄 글자 + 게시일 / 출력: 속성이 붙은 기간 구·금액 구.

lexer.py가 토큰을, phrases.py가 구(문법 트리의 마디)를 만들면, 이 파일이 구마다 속성을 계산한다.
  상속 속성 (↓): 왼쪽 형제나 부모에서 받는 값.   예: 연도 없는 날짜는 왼쪽 날짜의 연도를 받는다.
  합성 속성 (↑): 자기 자식에서 올라오는 값.     예: 기간의 마감일은 끝 날짜에서 올라온다.
상속 속성이 모두 왼쪽에서만 오므로(L-attributed) 줄을 왼쪽에서 오른쪽으로 한 번 읽으면 모든 속성이 정해진다.
오른쪽 값을 기다려야 하는 속성은 두지 않는다.

기간 (마감일)   줄 → 항목+     항목 → 이름표 기간     기간 → 시작날짜? ~ 끝날짜
  항목.label    ↓  앞 기간이 끝난 곳부터 이 기간 시작까지의 글자 ("대출실행기간: ")
  항목.applies  ↓  label에 한글이 있으면 "다른 기간 말(실행·발표·지급 …)이 없다", 한글이 없으면 앞 항목의 값을 이어받는다
  날짜.year     ↓  적힌 연도(오타면 게시 연도) → 왼쪽 날짜의 연도 → 게시 연도 (게시일보다 60일 넘게 앞이면 다음 해)
  날짜.fixed    ↓  이 날짜, 또는 연도를 물려준 왼쪽 날짜의 연도 오타를 고쳤는지
  일만 쓴 끝    ↓  "8. 13. ~ 14."의 14는 시작 날짜의 달·연도를 받는다 (시작보다 작으면 다음 달)
  기간.date     ↑  끝 날짜 (끝이 없으면 그 날짜 하나)
  줄.deadline   ↑  applies인 항목 중 마지막 기간 (하나도 없으면 마지막 기간)

금액   항목 → 앞말 금액 뒷말
  금액.pre      ↓  앞 금액이 끝난 곳(가까우면)부터 금액 시작까지, 최대 CONTEXT_BEFORE자
  금액.income   ↓  왼쪽에 소득 말("소득", "차상위" …)이 나왔는지. 나왔으면 뒤 금액은 소득 기준일 수 있다
  금액.counted  ↓  표 행("|")이고 왼쪽에 "10명"처럼 인원이 있는지 ("인당"이 없을 때). 있으면 인원 전체 예산이다
  항목.post     ↑  금액 뒤 CONTEXT_AFTER자
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


@dataclass
class _DateContext:
    """왼쪽에서 오른쪽으로 읽으며 넘겨주는 상속 속성."""

    year: int | None = None  # 왼쪽 날짜에 적힌 연도 (오타면 고친 연도)
    fixed: bool = False  # 그 연도가 오타를 고친 것인지
    applies: bool = True  # 앞 항목의 applies
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
    return value, ctx.fixed


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
    for p in periods(tokens):
        label = line[ctx.prev_end : p.first]
        applies = not _has_any(label, PERIOD_OTHER_WORDS) if _has_hangul(label) else ctx.applies
        begin, begin_fixed = _date_of(p.start, ctx, posted) if p.start is not None else (None, False)
        if p.end is None:  # "~ 선발완료 시까지"
            value, fixed = None, begin_fixed
        elif p.day_only:
            value, fixed = (_day_end(begin, p.end) if begin else None), begin_fixed
        else:
            value, fixed = _date_of(p.end, ctx, posted)
        result.append(DatedPeriod(p, label, applies, value, fixed or begin_fixed))
        ctx.applies, ctx.prev_end = applies, p.last
    return result


def line_deadline(items: list[DatedPeriod]) -> DatedPeriod | None:
    """줄.deadline ↑: 신청 기간으로 쓸 수 있는 항목 중 마지막."""
    if not items:
        return None
    return ([d for d in items if d.applies] or items)[-1]


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
    for a in amounts(tokens):
        pre = line[max(0, a.first - CONTEXT_BEFORE) : a.first]
        post = line[a.last : a.last + CONTEXT_AFTER]
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
