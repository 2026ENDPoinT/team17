"""이벤트 묶기 규칙 (순수 함수). 입력: 공지 목록(extracted + 검수값) / 출력: 이벤트별 공지 목록

같은 장학금에 대한 공지들(모집 → 수정(기한 연장·일정 변경) → 완료(마감·결과))을 이벤트 하나로 묶는다.
잘못 묶으면 장학금 하나가 화면에서 숨으므로, 애매하면 묶지 않는다 (크롤러 재게시 표시와 같은 원칙).

분류 담당이 공지마다 label, year, semester, round를 넣어 주면 그것을 쓴다.
아직 없으면 notice_kind와 제목으로 대신 읽는다 (아래 notice_label, scholarship_key).
"""

import datetime
import re

LABELS = ("모집", "수정", "완료")
MAX_DAYS = 120  # 이벤트 첫 공지와 이 일수보다 멀면 다른 이벤트 (같은 이름의 다음 해 모집)
MIN_NAME = 4  # 정리한 이름이 이보다 짧으면 같은 장학금인지 판단하지 않는다

# 분류 라벨이 없을 때: 모집 공지 제목에 이 말이 있으면 '수정' 공지로 본다
CHANGE_WORDS = ["연장", "수정", "변경", "추가 선발", "추가선발", "추가 모집", "추가모집", "재공지", "재공고"]

# 괄호 안 내용을 세 층으로 나눈다. 기준은 crawler/README.md "재게시 표시 > 제목 정규화" 절과 crawler/dedup.py이다.
# 크롤러 함수를 import하지 않고 목록만 맞춘다 (2026-11-14 팀 결정: 역할 사이에는 JSON으로만 주고받는다).
# 크롤러 목록을 고치면 여기도 같이 고친다. 원본 제목은 그대로 두고 비교할 때 만드는 임시 사본에만 쓴다.
_INNER_BRACKET = re.compile(r"\(([^()]*)\)|\[([^\[\]]*)\]|【([^】]*)】|<([^<>]*)>")
# [항상 지움] 날짜·기한, 상태 꼬리표("수정 3차"도 상태), 게시판 분류 표시(한 글자 괄호, 정확히 "장학"·"발전기금")
_DATE_LIKE = re.compile(r"\d.*(~|/|\.|:|까지|시|예정|월)|^(~|까지)|^[월화수목금토일]$")
_BRACKET_STATUS = re.compile(r"마감|홍보|완료|수정|필독|필수|중요|연장|안내|공지|교체|추가|신규|타과생")
_BOARD_LABEL = re.compile(r"^(.|장학|발전기금)$")
#   대상 표시 (누구에게 보이는 글인지): 같은 장학금 공지에 붙었다 안 붙었다 한다
#   ("[학부] … 대림수암장학문화재단 장학생"과 "[대림수암장학문화재단] … 장학생")
_AUDIENCE = re.compile(r"^(학부|대학원|일반대학원|재학생|학부생|학부 재학생)$")
# [목적에 따라 다름] 학교 부서 (공지를 낸 곳): 이벤트 묶기는 남긴다 (크롤러의 drop_units=False와 같음).
#   "[도서관] 국가근로장학생 모집"과 "[생활협동조합] …"은 다른 모집이다. 재게시는 duplicate_of로 이미 걸러졌다.
# [항상 남김] 재단·장학회·협회 이름(상태 꼬리표와 같이 있어도), 희망사다리·유형·N차·금액, 모르는 내용
_ORG_NAME = re.compile(r"재단|장학회|협회|사랑의열매")
_IDENTIFIER = re.compile(r"희망사다리|유형|\d+차|^\d[\d,]*만?원$")
# "2026학년도", "2026년", "2026.", "2026-2학기", "26년". 두 자리는 '년'이 붙을 때만 ("11.13"을 연도로 읽지 않게)
_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)\s*(?:학년도|년도|년|\.|-)?|(?<!\d)(\d{2})\s*(?:학년도|년도|년)")
_SEMESTER = re.compile(r"([12])\s*학기|(상|하)반기")
_ROUND = re.compile(r"(\d+)\s*차|제\s*(\d+)\s*(?:기|회)")
_REVISION = re.compile(r"수정\s*\d+\s*차")  # "(수정 3차)"는 차수가 아니라 몇 번째 수정인지다
# 괄호 밖에서도 지우는 말: 공지 종류·상태를 나타내는 말이라 같은 장학금의 공지마다 다르다
_KIND_WORDS = ["선발", "모집", "신청", "결과", "알림", "안내", "공고", "발표", "대상자", "기간", "추가", "연장",
                 "수정", "변경", "마감", "완료", "후지급", "지급", "재공지", "홍보", "학년도", "년도"]


def notice_label(item: dict) -> str | None:
    """공지 라벨: '모집' / '수정' / '완료' / None(장학금 공지가 아님, 이벤트에 넣지 않음).
    분류가 label 필드를 주면(값이 null이어도) 그대로 쓴다. label 필드가 없는 옛 추출 결과만 notice_kind로 대신 정한다."""
    if "label" in item:
        return item["label"] if item["label"] in LABELS else None
    kind = item.get("notice_kind")
    if kind == "결과":
        return "완료"
    if kind == "모집":
        title = item.get("title") or ""
        return "수정" if any(w in title for w in CHANGE_WORDS) else "모집"
    return None


def _year(text: str) -> int | None:
    m = _YEAR.search(text)
    if not m:
        return None
    return int(m.group(1)) if m.group(1) else 2000 + int(m.group(2))


def _semester(text: str) -> int | None:
    m = _SEMESTER.search(text)
    if not m:
        return None
    if m.group(1):
        return int(m.group(1))
    return 1 if m.group(2) == "상" else 2


def _round(text: str) -> int | None:
    m = _ROUND.search(_REVISION.sub(" ", text))
    if not m:
        return None
    return int(m.group(1) or m.group(2))


def bracket_kept(inner: str) -> str:
    """괄호 안 내용을 남길지 정한다. 남기면 괄호 기호만 빼고 내용을 돌려준다. 판정 순서는 크롤러와 같다:
    빈 값·분류 표시·날짜 → 지움 / 기관 이름 → 남김 / 상태 꼬리표 → 지움 / 차수·유형·금액 → 남김 / 나머지 → 남김"""
    s = inner.strip()
    if not s or _BOARD_LABEL.match(s) or _AUDIENCE.match(s) or _DATE_LIKE.search(s.replace(" ", "")):
        return " "
    if _ORG_NAME.search(s):
        return f" {s} "
    if _BRACKET_STATUS.search(s):
        return " "
    if _IDENTIFIER.search(s):
        return f" {s} "
    return f" {s} "  # 학교 부서(이벤트 묶기는 남김), 모르는 내용은 남긴다


def core_name(text: str) -> str:
    """비교용 이름: 괄호를 위 세 층 규칙으로 정리한 뒤, 연도·학기·차수, 공지 종류를 나타내는 말, 공백·기호를 지운다."""
    t = text.lower()
    prev = None
    while prev != t:  # 괄호 안에 괄호가 있을 수 있어 안쪽부터 반복해서 처리한다
        prev = t
        t = _INNER_BRACKET.sub(lambda m: bracket_kept(next(g for g in m.groups() if g is not None)), t)
    t = _REVISION.sub(" ", t)
    t = _YEAR.sub(" ", t)
    t = _SEMESTER.sub(" ", t)
    t = _ROUND.sub(" ", t)
    for w in _KIND_WORDS:
        t = t.replace(w, " ")
    return re.sub(r"[^0-9a-z가-힣]", "", t)


def scholarship_key(item: dict) -> dict:
    """묶을 때 비교하는 값. 이름은 제목에서 만든다 (분류의 name은 괄호 속 재단 이름이 빠질 수 있다).
    연도·학기·차수는 분류가 준 값이 있으면 그것을, 없으면 제목에서 뽑는다."""
    title = item.get("title") or item.get("name") or ""
    return {
        "name": core_name(title),
        "year": item["year"] if item.get("year") is not None else _year(title),
        "semester": item["semester"] if item.get("semester") is not None else _semester(title),
        "round": item["round"] if item.get("round") is not None else _round(title),
    }


def same_scholarship(a: dict, b: dict) -> bool:
    """두 키가 같은 장학금인가. 이름은 정리한 뒤 완전히 같아야 한다 (비슷한 이름은 다른 장학금일 수 있다).
    연도·학기는 한쪽이 모르면 넘어가고, 차수는 둘 다 같아야 한다 (모름 ≠ 2차)."""
    if len(a["name"]) < MIN_NAME or a["name"] != b["name"]:
        return False
    for field in ("year", "semester"):
        if a[field] is not None and b[field] is not None and a[field] != b[field]:
            return False
    return a["round"] == b["round"]


def _days_apart(a: str | None, b: str | None) -> int:
    if not a or not b:
        return 0
    return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days)


def _order(item: dict):
    return (item["source"].get("posted_at") or "", int(item["id"]))


def has_details(item: dict) -> bool:
    """장학금 상세(금액·조건·마감)가 있는 공지인가: 모집·수정 공지, 또는 마감된 모집 공지.
    분류는 "… 모집 안내(마감)"에도 '완료' 라벨을 붙이므로 notice_kind로 결과 공지와 가린다."""
    return item["_label"] in ("모집", "수정") or item.get("notice_kind") == "모집"


def opens_event(item: dict) -> bool:
    """새 이벤트를 여는 공지: '모집' 공지와 마감된 모집 공지("… 모집 안내(마감)", 라벨 '완료').
    마감된 모집 공지는 그 자체가 모집 공지라서, 앞의 같은 이름 모집(다른 학기·다른 기관일 수 있음)에 붙이지 않는다."""
    return item["_label"] == "모집" or (item["_label"] == "완료" and item.get("notice_kind") == "모집")


def group_notices(items: list[dict]) -> list[list[dict]]:
    """공지(라벨이 있는 것만)를 게시 순서대로 보며 이벤트로 묶는다.

    - 모집 공지(마감된 모집 공지 포함)는 항상 새 이벤트를 연다. (같은 이름의 모집 공지가 또 오면 다음 차수나 재모집일 수 있다)
    - 수정 공지와 결과 공지(완료)는 같은 장학금인 이벤트 중 가장 최근 것에 붙는다. 없으면 혼자 이벤트가 된다.
    - 같은 장학금인지는 이벤트의 **첫 공지**와 비교한다 (사슬처럼 이어 묶지 않는다).
    """
    events: list[dict] = []  # {"key", "posted_at", "notices"}
    for item in sorted(items, key=_order):
        key = scholarship_key(item)
        posted = item["source"].get("posted_at")
        target = None
        if not opens_event(item):
            for ev in reversed(events):
                if _days_apart(ev["posted_at"], posted) <= MAX_DAYS and same_scholarship(ev["key"], key):
                    target = ev
                    break
        if target is None:
            events.append({"key": key, "posted_at": posted, "notices": [item]})
        else:
            target["notices"].append(item)
    return [ev["notices"] for ev in events]
