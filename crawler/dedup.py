"""학과 재게시 묶기. 입력: data/raw 레코드 목록 / 출력: {bidx: 대표 글 bidx 또는 None}

같은 공지를 여러 게시판에 다시 올리면 bidx가 새로 생긴다. 제목으로 같은 글인지 판단해 묶는다.
파일은 지우지 않고 각 글에 duplicate_of(대표 글 bidx)만 적는다. 틀린 묶음은 data/reviewed/에서 고친다.

같은 글로 보는 조건 (2026-11-13 실제 데이터 71건으로 정함)
1. 서로 다른 게시판이다. (같은 게시판에 같은 제목이면 새 차수 모집일 수 있다)
2. 정규화한 제목의 유사도가 0.9 이상이다. ("신청 안내"와 "선발 결과 안내"가 0.85였다)
3. 제목 속 숫자가 모두 같다. ("1차 지급완료"와 "2차 지급완료"가 0.96이었다)
4. 게시일 차이가 14일 이내다.

대표 글: 본부(www) 글 > 먼저 올라온 글 > bidx가 작은 글
각 글은 대표 글과 직접 비교한다 (사슬처럼 이어 묶지 않는다).
"""

import datetime
import difflib
import re

SIMILARITY = 0.9
MAX_DAYS_APART = 14

_BRACKETS = re.compile(r"\([^()]*\)|\[[^\[\]]*\]|【[^】]*】|<[^<>]*>")
_NUM = re.compile(r"\d+")


def normalize_title(title: str) -> str:
    """괄호 안 내용([학부], (홍보), (~11/6(금)) 등)과 공백·기호를 지운다."""
    t = title.lower()
    prev = None
    while prev != t:  # 괄호 안에 괄호가 있을 수 있어 안쪽부터 반복해서 지운다
        prev = t
        t = _BRACKETS.sub("", t)
    return re.sub(r"[^0-9a-z가-힣]", "", t)


def _days_apart(a: str | None, b: str | None) -> int:
    if not a or not b:
        return 0
    return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days)


def is_same_notice(a: dict, b: dict) -> bool:
    if (a["site"], a["board"]) == (b["site"], b["board"]):
        return False
    na, nb = normalize_title(a["title"]), normalize_title(b["title"])
    if not na or not nb or _NUM.findall(na) != _NUM.findall(nb):
        return False
    if _days_apart(a["posted_date"], b["posted_date"]) > MAX_DAYS_APART:
        return False
    return difflib.SequenceMatcher(None, na, nb).ratio() >= SIMILARITY


def _priority(r: dict):
    return (r["site"] != "www", r["posted_date"] or "9999", r["bidx"])


def assign_duplicates(records: list[dict]) -> dict[int, int | None]:
    """대표 글 후보 순서(_priority)대로 보면서, 이미 정한 대표 글과 **직접** 같은 글이면 그 대표에 붙인다.
    A~B, B~C라서 A와 C까지 한 묶음이 되는 사슬 묶기는 하지 않는다.
    (6개월 데이터에서 '등록금 납부 일정 안내'가 '분할납부제 실시 안내'와 사슬로 묶인 일이 있었다)"""
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
