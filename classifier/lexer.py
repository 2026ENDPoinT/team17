"""어휘 분석: 공지 한 줄 → 토큰 목록. 입력: 문자열 한 줄 / 출력: list[Token].

컴파일러의 어휘 분석기처럼, 표현이 제각각인 날짜·시각·금액을 여기서 한 번만 정규화한다.
  "2026. 8. 28." / "2026년 8월 28일" / "8/28"       → DATE (2026|None, 8, 28)
  "2.5 이상" / "3.0/4.5"                            → NUMBER (평점 같은 소수. 날짜로 읽지 않는다)
  "15:00" / "18시" / "3:00 p.m."                    → TIME
  "250만원" / "5백만 원" / "2천만원" / "10,320원" / "1,000천원" → MONEY (정수 원)
  "시급" / "시간당" / "시간 당" / "학기당" / "연간"   → PER ("시간" / "학기" / "연" / "월")
이 파일은 뜻을 판단하지 않는다. "이 날짜가 마감일인가"는 phrases.py(구문)와 rules.py(의미)가 정한다.
"""

import re
from dataclasses import dataclass

from config import ROLLING_WORDS


@dataclass
class Token:
    kind: str  # NUMBER, DATE, TIME, TILDE, UNTIL, ROLLING, MONEY, PERCENT, PER, TUITION, FULL, MAX, COLON, CELL
    text: str  # 원문 그대로
    value: object  # 정규화한 값 (DATE: (연|None, 월, 일), MONEY: 원, PER: "시간"/"학기"/"연"/"월" …)
    start: int  # 줄 안에서의 위치
    end: int


_NOT_GRADE = r"(?!\s*(?:학년|학기|학점))"

# 순서가 중요하다: 앞의 규칙이 먼저 자리를 차지한다 (TIME이 DATE보다 먼저라서 "15:00"이 날짜가 되지 않는다)
_RULES: list[tuple[str, re.Pattern]] = [
    ("TIME", re.compile(r"(?<!\d)(\d{1,2})\s*:\s*(\d{2})(?:\s*[ap]\.?\s*m\.?)?|(?<!\d)(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?(?![가-힣])"
                        # "18시까지", "10시부터"처럼 조사가 붙은 시각. "2시간", "시기"는 시각이 아니다
                        r"|(?<!\d)(\d{1,2})\s*시(?:\s*(\d{1,2})\s*분)?(?=까지|부터|정각|이전|이후|전|후)")),
    ("NUMBER", re.compile(r"(?<![\d.])(\d\.\d{1,2})(?=\s*(?:/\s*\d\.\d|점|이상|이하|초과|미만|만점|기준|학점|평점))"
                          r"|(?<=/)\s*(\d\.\d{1,2})"
                          r"|(?<=평점|학점|성적)[\s:]*(\d\.\d{1,2})(?![\d.])")),  # 평점 "2.5 이상", "3.0/4.5", "평점 3.5" (날짜가 아니다)
    # 뒤에 "학년·학기·학점"이 오면 날짜가 아니다: "3/4학년", "3-4학년"
    ("DATE", re.compile(r"(?<!\d)(?:(\d{4}|\d{2})\s*[.년\-]\s*)?(\d{1,2})\s*[.월/\-]\s*(\d{1,2})(?!\d)\s*(?:일|\.)?"
                        + _NOT_GRADE)),
    # 위 규칙이 두 자리 연도로 읽다 실패한 자리를 연도 없이 한 번 더 읽는다.
    # "11. 17. 18시"는 "11년 17월 18일"로 먼저 읽혀 틀린 날짜가 되고, 그 글자를 다시 보지 않아 "11. 17."을 놓쳤다
    ("DATE", re.compile(r"(?<!\d)()(\d{1,2})\s*[.월/\-]\s*(\d{1,2})(?!\d)\s*(?:일|\.)?" + _NOT_GRADE)),
    # 기간의 끝에 일만 쓴 것: "8. 13.(목) ~ 14.(금)". 월은 구문 분석이 시작 날짜에서 가져온다
    ("DAY", re.compile(r"(?<![\d.])(\d{1,2})\s*(?:일|\.)?\s*(?=\((?:월|화|수|목|금|토|일)\))")),
    # "7월 1일 ~ 10일"처럼 "~" 바로 뒤에 "N일"만 쓴 것 (요일 없음)
    ("DAY", re.compile(r"(?<=[~∼～])\s*(\d{1,2})\s*일(?![가-힣])")),
    ("SAMEDAY", re.compile(r"당일")),  # "8월 24일 00시 ~ 당일 자정까지"
    # "천원"은 표의 단위로 자주 쓴다: "최대 1,000천원" = 100만원 (892400)
    ("MONEY", re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?\s*(억|천\s*만|백\s*만|십\s*만|만|천)?\s*원")),
    ("PERCENT", re.compile(r"(?<!\d)(\d{1,3})\s*%")),
    ("PER", re.compile(r"시급|시간\s*당|학기\s*당|학기별|연간|(?<![가-힣])월\s*(?=\d)|매월")),
    ("TUITION", re.compile(r"등록금|수업료")),
    ("FULL", re.compile(r"전액")),
    ("MAX", re.compile(r"최대|상한액?|한도")),
    ("TILDE", re.compile(r"[~∼～]")),
    ("UNTIL", re.compile(r"까지")),
    ("COLON", re.compile(r"(?<!\d)[:：]|[:：](?!\d)")),  # 이름표 콜론. 시각 "15:00"의 콜론은 TIME이 먼저 가져간다
    ("CELL", re.compile(r"\|")),
]
_ROLLING = re.compile("|".join(re.escape(w) for w in sorted(ROLLING_WORDS, key=len, reverse=True)))
_UNIT = {"억": 100_000_000, "천만": 10_000_000, "백만": 1_000_000, "십만": 100_000, "만": 10_000, "천": 1_000}
_PER = {"시급": "시간", "연간": "연", "매월": "월", "학기별": "학기"}


def _value(kind: str, m: re.Match) -> object:
    if kind == "DATE":
        y, mo, d = m.group(1), int(m.group(2)), int(m.group(3))
        year = (int(y) + 2000 if len(y) == 2 else int(y)) if y else None
        return (year, mo, d)
    if kind == "TIME":
        hour = int(m.group(1) or m.group(3) or m.group(5))
        minute = int(m.group(2) or m.group(4) or m.group(6) or 0)
        if "p" in m.group(0).lower() and hour < 12:
            hour += 12
        return (hour, minute)
    if kind == "MONEY":
        number = int(m.group(1).replace(",", ""))
        fraction = m.group(2)
        unit = _UNIT[re.sub(r"\s", "", m.group(3))] if m.group(3) else 1
        if fraction:  # "1.5만원"
            return int((number + float("0." + fraction)) * unit)
        return number * unit
    if kind == "PERCENT":
        return int(m.group(1))
    if kind == "NUMBER":
        return float(m.group(1) or m.group(2) or m.group(3))
    if kind == "DAY":
        return int(m.group(1))
    if kind == "PER":
        word = re.sub(r"\s", "", m.group(0))
        return _PER.get(word, word.replace("당", ""))
    return m.group(0)


def _valid(kind: str, value: object) -> bool:
    if kind == "DAY":
        return 1 <= value <= 31
    if kind == "DATE":
        _, mo, d = value
        return 1 <= mo <= 12 and 1 <= d <= 31
    if kind == "TIME":
        hour, minute = value
        return hour <= 24 and minute < 60
    return True


def tokenize(line: str) -> list[Token]:
    """한 줄을 토큰 목록으로 바꾼다. 알아보는 말만 토큰이 되고, 나머지 글자는 건너뛴다 (위치로 원문을 다시 볼 수 있다)."""
    taken = [False] * len(line)
    tokens: list[Token] = []

    def add(kind: str, m: re.Match, value: object) -> None:
        if any(taken[m.start() : m.end()]) or not _valid(kind, value):
            return
        for i in range(m.start(), m.end()):
            taken[i] = True
        tokens.append(Token(kind, m.group(0), value, m.start(), m.end()))

    for m in _ROLLING.finditer(line):  # "선발완료 시"의 "시"가 TIME이 되지 않게 먼저 잡는다
        add("ROLLING", m, m.group(0))
    for kind, pattern in _RULES:
        for m in pattern.finditer(line):
            add(kind, m, _value(kind, m))
    return sorted(tokens, key=lambda t: t.start)


def show(line: str) -> str:
    """토큰 열을 사람이 읽게 보여 준다 (디버깅·발표용). 예: [DATE 2026-08-28] [TILDE] [DATE ?-09-04]"""
    parts = []
    for t in tokenize(line):
        if t.kind == "DATE":
            y, mo, d = t.value
            parts.append(f"[DATE {y or '?'}-{mo:02d}-{d:02d}]")
        elif t.kind == "TIME":
            parts.append(f"[TIME {t.value[0]:02d}:{t.value[1]:02d}]")
        elif t.kind in ("MONEY", "PERCENT", "PER", "NUMBER"):
            parts.append(f"[{t.kind} {t.value}]")
        else:
            parts.append(f"[{t.kind}]")
    return " ".join(parts)
