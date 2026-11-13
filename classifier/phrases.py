"""구문 분석 (줄 안): 토큰 목록 → 구(phrase). 입력: lexer.tokenize()의 결과 / 출력: 기간 구, 금액 구.

parser.py가 공지를 문단으로 나눈다면, 이 파일은 한 줄 안의 토큰을 문법 규칙으로 묶는다.

  기간 구  :=  DATE TIME? (TILDE (DATE TIME? | ROLLING))? UNTIL?      "8. 24. ~ 8. 31. 18:00까지"
            |  TILDE DATE TIME? UNTIL?                                 "~ 2026.6.22.(월)"
  금액 구  :=  TUITION … (FULL | PERCENT)                              "수업료 100%", "등록금 전액"
            |  PER? MAX? MONEY                                          "학기당 250만원", "시간 당 10,320원"

여기서도 뜻은 정하지 않는다. 구에 속성(연도, 이름표, 쓰임)을 붙이는 것은 semantics.py, 마감일·금액을 고르는 것은 rules.py가 한다.
"""

from dataclasses import dataclass

from lexer import Token

_NEAR = 12  # 금액 앞의 PER("학기당")를 이 글자 수 안에서 찾는다
_TUITION_NEAR = 10  # "등록금" 뒤의 "전액"·"%"를 이 글자 수 안에서 찾는다


@dataclass
class Period:
    """기간 구. start·end는 DATE 토큰, rolling이면 끝이 "선발완료 시까지"처럼 정해지지 않았다."""

    start: Token | None
    end: Token | None
    rolling: bool
    first: int  # 줄 안에서 구가 시작하는 위치
    last: int  # 끝나는 위치
    # "6. 8.(월) 10:00 ~"처럼 "~" 뒤에 끝이 없다. 이 날짜가 마감일인지 시작일인지 원문만으로는 모른다.
    # "5. 22.(금) 09:00~18:00"처럼 "~" 바로 뒤가 시각이면 같은 날의 시간 범위라 open이 아니다
    open: bool = False
    # "8. 13.(목) ~ 14.(금)"의 14처럼 끝에 일만 적혀 있다. 끝 날짜의 연도는 semantics.py가 시작 날짜에서 물려준다
    day_only: bool = False


@dataclass
class Amount:
    """금액 구. kind는 tuition_ratio(값은 %) / hourly(원) / lump_sum(원). per는 "학기", "연", "월", "시간" 또는 None."""

    kind: str
    value: int
    per: str | None
    first: int
    last: int


def _skip_time(tokens: list[Token], i: int) -> int:
    """i부터 TIME·UNTIL을 건너뛴 다음 토큰 위치."""
    while i < len(tokens) and tokens[i].kind in ("TIME", "UNTIL"):
        i += 1
    return i


def periods(tokens: list[Token]) -> list[Period]:
    """토큰 목록에서 기간 구를 모두 찾는다 (줄에 나온 순서)."""
    found: list[Period] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.kind == "DATE":
            j = _skip_time(tokens, i + 1)
            if j < len(tokens) and tokens[j].kind == "TILDE":
                k = _skip_time(tokens, j + 1)
                nxt = tokens[k] if k < len(tokens) else None
                if nxt is not None and nxt.kind == "DATE":  # 시작 ~ 끝
                    end_i = _skip_time(tokens, k + 1)
                    found.append(Period(t, nxt, False, t.start, tokens[end_i - 1].end))
                    i = end_i
                    continue
                if nxt is not None and nxt.kind == "ROLLING":  # 시작 ~ 선발완료 시까지
                    found.append(Period(t, None, True, t.start, nxt.end))
                    i = k + 1
                    continue
                if nxt is not None and nxt.kind == "DAY":  # "8. 13.(목) ~ 14.(금)": 끝은 시작과 같은 달
                    year, month, start_day = t.value
                    if nxt.value < start_day:  # "8. 28. ~ 3.(목)"은 다음 달 3일
                        year, month = (year + 1 if year else None, 1) if month == 12 else (year, month + 1)
                    end = Token("DATE", nxt.text, (year, month, nxt.value), nxt.start, nxt.end)
                    end_i = _skip_time(tokens, k + 1)
                    found.append(Period(t, end, False, t.start, tokens[end_i - 1].end, day_only=True))
                    i = end_i
                    continue
                # "09:00~18:00"이나 "00시 ~ 당일 자정"은 같은 날의 시간 범위다
                time_range = j + 1 < len(tokens) and tokens[j + 1].kind in ("TIME", "SAMEDAY")
                found.append(Period(None, t, False, t.start, t.end, open=not time_range))  # "날짜 ~" 끝 없음
                i = j + 1
                continue
            found.append(Period(None, t, False, t.start, t.end))  # 날짜 하나
            i = j
            continue
        if t.kind == "TILDE":  # "~ 2026.6.22."처럼 시작 없이 끝만
            k = _skip_time(tokens, i + 1)
            if k < len(tokens) and tokens[k].kind == "DATE":
                found.append(Period(None, tokens[k], False, t.start, tokens[k].end))
                i = _skip_time(tokens, k + 1)
                continue
        i += 1
    return found


def amounts(tokens: list[Token]) -> list[Amount]:
    """토큰 목록에서 금액 구를 모두 찾는다 (줄에 나온 순서)."""
    found: list[Amount] = []
    for i, t in enumerate(tokens):
        if t.kind == "TUITION":
            for nxt in tokens[i + 1 : i + 3]:
                if nxt.start - t.end > _TUITION_NEAR:
                    break
                if nxt.kind == "FULL":
                    found.append(Amount("tuition_ratio", 100, None, t.start, nxt.end))
                    break
                if nxt.kind == "PERCENT":
                    found.append(Amount("tuition_ratio", nxt.value, None, t.start, nxt.end))
                    break
        elif t.kind == "MONEY":
            # 바로 앞의 "학기당", "시간 당", "최대", "시급:"을 붙인다. 앞 토큰과 _NEAR자 안에 이어져 있어야 하고,
            # PER는 가장 가까운 하나만 쓴다 ("월 48시간, 시간당 10,320원"의 "월"은 금액과 상관없다)
            per = None
            first = t.start
            for prev in reversed(tokens[:i]):
                if first - prev.end > _NEAR or prev.kind not in ("PER", "MAX", "COLON"):
                    break
                if prev.kind == "PER":
                    if per is not None:
                        break
                    per = prev.value
                if prev.kind != "COLON":
                    first = prev.start
            kind = "hourly" if per == "시간" else "lump_sum"
            found.append(Amount(kind, t.value, per, first, t.end))
    return sorted(found, key=lambda a: a.first)
