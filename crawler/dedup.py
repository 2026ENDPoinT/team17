"""학과 재게시 표시. 입력: data/raw 레코드 목록 / 출력: {bidx: 대표 글 bidx 또는 None}

같은 공지를 여러 게시판에 다시 올리면 bidx가 새로 생긴다. 크롤러는 **내용이 같은 복사본**만 표시한다.
같은 장학금의 다른 공지(모집·수정·완료)를 하나의 이벤트로 묶는 일은 다음 단계(라벨링 → 이벤트 묶기)가 한다.
파일은 지우지 않고 각 글에 duplicate_of(대표 글 bidx)만 적는다. 틀린 표시는 data/reviewed/에서 고친다.

같은 글로 보는 조건 (2026-11-13, 6개월 데이터 238건으로 정함)
1. 후보: 서로 다른 게시판 / 게시일 60일 이내 / 정규화한 제목 유사도 0.7 이상
   (같은 게시판의 같은 제목은 새 차수 모집일 수 있어 보지 않는다.
    내용이 같은 재게시 21쌍은 모두 제목 유사도 0.9 이상이었다. 0.7은 여유를 둔 값이다)
2. 확인: 첨부 파일 이름 목록이 완전히 같다 (본문 유무와 상관없이. 포스터만 올린 재게시가 있다)
   또는 둘 다 본문이 있고(30자 이상) 본문 유사도 0.95 이상 (공백 무시) + 본문 속 숫자가 모두 같음
   (등록금 1차·2차 공지는 같은 틀에 날짜만 달라 본문 유사도가 0.99였다)
   본문도 첨부도 비교할 수 없으면 표시하지 않는다.
   제목만으로 판단하던 이전 방식은 "[해성문화재단] 장학생 선발"과 "어의장학생 선발"처럼
   제목이 비슷하지만 다른 공지를 묶었다. 잘못 묶으면 장학금 하나가 화면에서 숨으므로,
   애매하면 묶지 않는 쪽을 고른다.

대표 글: 본부(www) 글 > 먼저 올라온 글 > bidx가 작은 글
각 글은 대표 글과 직접 비교한다 (A~B, B~C라서 A~C까지 묶는 사슬 묶기를 하지 않는다).
"""

import datetime
import difflib
import re

TITLE_CANDIDATE = 0.7
BODY_SAME = 0.95
MIN_BODY_CHARS = 30
MAX_DAYS_APART = 60

_BRACKETS = re.compile(r"\(([^()]*)\)|\[([^\[\]]*)\]|【([^】]*)】|<([^<>]*)>")
_NUM = re.compile(r"\d+")

# 괄호 안 내용 중 지우는 것 (2026-11-13, 제목 309개의 괄호 내용을 모아 정함). 나머지는 남긴다.
# 1) 날짜·기한: 숫자와 함께 ~ / . : 까지 시 예정 월 이 있는 것, 요일 한 글자
_DATE_LIKE = re.compile(r"\d.*(~|/|\.|:|까지|시|예정|월)|^(~|까지)|^[월화수목금토일]$")
# 2) 상태·안내 꼬리표
_STATUS_WORDS = re.compile(r"마감|홍보|완료|수정|필독|필수|중요|연장|안내|공지|교체|추가|신규|타과생")
# 3) 글을 올린 학교 부서·대상 (장학금을 구분하는 정보가 아니다). 재단·장학회 이름은 남긴다
_SCHOOL_UNIT = re.compile(r"(처|원|센터|과|팀|단|대학|본부|관|실|소|부|전공|조합|미술관)$|^(학부|대학원|일반대학원|장학|재학생|학부생|학부 재학생)")
_KEEP = re.compile(r"재단|장학회|협회|사랑의열매|희망사다리|유형|\d+차|^\d[\d,]*만?원$")


def _bracket_kept(inner: str) -> str:
    """괄호 안 내용을 남길지 정한다. 남기면 괄호 기호만 빼고 내용을 돌려준다."""
    s = inner.strip()
    if not s:
        return ""
    if _KEEP.search(s) and not _DATE_LIKE.search(s.replace(" ", "")):
        return " " + s + " "  # 재단 이름, 차수, 유형은 장학금을 구분하는 정보다
    if _DATE_LIKE.search(s) or _STATUS_WORDS.search(s) or _SCHOOL_UNIT.search(s):
        return ""
    return " " + s + " "  # 모르는 내용은 남긴다 (지워서 생기는 오판이 더 위험하다)


def normalize_title(title: str) -> str:
    """제목에서 상태 꼬리표·날짜·학교 부서 괄호만 지우고, 재단 이름·차수 같은 정보는 남긴 뒤 공백·기호를 지운다.
    예) "[해성문화재단] 2026년도 2학기 장학생 선발 안내 (마감)" → "해성문화재단2026년도2학기장학생선발안내"
        "★2026학년도 2학기 등록금 납부(2차) 일정 안내★" → "2026학년도2학기등록금납부2차일정안내"
    재게시 후보를 고를 때만 쓴다. 최종 판단은 본문·첨부로 한다."""
    t = title.lower()
    prev = None
    while prev != t:  # 괄호 안에 괄호가 있을 수 있어 안쪽부터 처리한다
        prev = t
        t = _BRACKETS.sub(lambda m: _bracket_kept(next(g for g in m.groups() if g is not None)), t)
    return re.sub(r"[^0-9a-z가-힣]", "", t)


def _days_apart(a: str | None, b: str | None) -> int:
    if not a or not b:
        return 0
    return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days)


def _body(r: dict) -> str:
    return re.sub(r"\s+", "", r["body_text"])


def _attachment_names(r: dict) -> list[str]:
    return sorted(re.sub(r"\s+", "", a["name"]).lower() for a in r["attachments"])


def is_candidate(a: dict, b: dict) -> bool:
    if (a["site"], a["board"]) == (b["site"], b["board"]):
        return False
    if _days_apart(a["posted_date"], b["posted_date"]) > MAX_DAYS_APART:
        return False
    na, nb = normalize_title(a["title"]), normalize_title(b["title"])
    return bool(na and nb) and difflib.SequenceMatcher(None, na, nb).ratio() >= TITLE_CANDIDATE


def has_same_content(a: dict, b: dict) -> bool:
    # 1) 첨부 파일 이름 목록이 완전히 같다. 학과가 본문 대신 포스터만 올리고 첨부는 그대로 다는 경우가 있다
    names = _attachment_names(a)
    if names and names == _attachment_names(b):
        return True
    # 2) 둘 다 본문이 있고 거의 같으며, 본문 속 숫자(날짜·금액·차수)가 모두 같다
    #    등록금 1차·2차 공지처럼 같은 틀에 날짜만 바꾼 공지는 본문 유사도가 0.99여서 숫자로 구분한다
    x, y = _body(a), _body(b)
    if len(x) >= MIN_BODY_CHARS and len(y) >= MIN_BODY_CHARS:
        if _NUM.findall(x) != _NUM.findall(y):
            return False
        sm = difflib.SequenceMatcher(None, x, y, autojunk=False)
        # quick 비교로 먼저 거른 뒤 정확한 비교를 한다 (긴 본문에서 속도)
        return sm.real_quick_ratio() >= BODY_SAME and sm.quick_ratio() >= BODY_SAME and sm.ratio() >= BODY_SAME
    return False


def is_same_notice(a: dict, b: dict) -> bool:
    return is_candidate(a, b) and has_same_content(a, b)


def _priority(r: dict):
    return (r["site"] != "www", r["posted_date"] or "9999", r["bidx"])


def assign_duplicates(records: list[dict]) -> dict[int, int | None]:
    """대표 글 후보 순서(_priority)대로 보면서, 이미 정한 대표 글과 직접 같은 글이면 그 대표에 붙인다."""
    reps: list[dict] = []
    result: dict[int, int | None] = {}
    for r in sorted(records, key=_priority):
        rep = next((x for x in reps if is_same_notice(x, r)), None)
        if rep is None:
            reps.append(r)
            result[r["bidx"]] = None
        else:
            result[r["bidx"]] = rep["bidx"]
    return result
