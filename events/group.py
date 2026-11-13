"""이벤트 묶기 규칙 (순수 함수). 입력: 공지 목록(extracted + 검수값) / 출력: 이벤트별 공지 목록

같은 장학금에 대한 공지들(모집 → 수정(기한 연장·일정 변경) → 완료(마감·결과))을 이벤트 하나로 묶는다.
잘못 묶으면 장학금 하나가 화면에서 숨으므로, 애매하면 묶지 않는다 (크롤러 재게시 표시와 같은 원칙).

분류 담당이 공지마다 label, year, semester, round를 넣어 주면 그것을 쓴다.
아직 없으면 notice_kind와 제목으로 대신 읽는다 (아래 notice_label, scholarship_key).
"""

import datetime
import difflib
import re

LABELS = ("모집", "수정", "완료")
SAME_NAME = 0.9  # 정규화한 장학금 이름의 유사도가 이 값 이상이면 같은 이름
MAX_DAYS = 120  # 이벤트 첫 공지와 이 일수보다 멀면 다른 이벤트 (같은 이름의 다음 해 모집)

# 분류 라벨이 없을 때: 모집 공지 제목에 이 말이 있으면 '수정' 공지로 본다
CHANGE_WORDS = ["연장", "수정", "변경", "추가 선발", "추가선발", "추가 모집", "추가모집", "재공지", "재공고"]

_BRACKETS = re.compile(r"\([^()]*\)|\[[^\[\]]*\]|【[^】]*】|<[^<>]*>|『|』|「|」")
# "2026학년도", "2026년", "2026.", "2026-2학기", "26년". 두 자리는 '년'이 붙을 때만 ("11.13"을 연도로 읽지 않게)
_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)\s*(?:학년도|년도|년|\.|-)?|(?<!\d)(\d{2})\s*(?:학년도|년도|년)")
_SEMESTER = re.compile(r"([12])\s*학기|(상|하)반기")
_ROUND = re.compile(r"(\d+)\s*차|제\s*(\d+)\s*(?:기|회)")
# 이름에서 지우는 말: 공지 종류·상태를 나타내는 말이라 같은 장학금의 공지마다 다르다
_STATUS_WORDS = ["선발", "모집", "신청", "결과", "알림", "안내", "공고", "발표", "대상자", "기간", "추가", "연장",
                 "수정", "변경", "마감", "완료", "후지급", "지급", "재공지", "홍보", "학년도", "년도"]


def notice_label(item: dict) -> str | None:
    """공지 라벨: '모집' / '수정' / '완료' / None(안내 등, 이벤트에 넣지 않음)."""
    label = item.get("label")
    if label in LABELS:
        return label
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
    m = _ROUND.search(text)
    if not m:
        return None
    return int(m.group(1) or m.group(2))


def core_name(text: str) -> str:
    """장학금 이름에서 괄호, 연도·학기·차수, 공지 종류를 나타내는 말, 공백·기호를 지운다."""
    t = text.lower()
    prev = None
    while prev != t:  # 괄호 안에 괄호가 있을 수 있어 안쪽부터 반복해서 지운다
        prev = t
        t = _BRACKETS.sub(" ", t)
    t = _YEAR.sub(" ", t)
    t = _SEMESTER.sub(" ", t)
    t = _ROUND.sub(" ", t)
    for w in _STATUS_WORDS:
        t = t.replace(w, " ")
    return re.sub(r"[^0-9a-z가-힣]", "", t)


def scholarship_key(item: dict) -> dict:
    """묶을 때 비교하는 값. 분류가 준 값이 있으면 그것을, 없으면 이름·제목에서 뽑는다."""
    name = item.get("name") or item.get("title") or ""
    title = item.get("title") or ""
    both = f"{name} {title}"
    return {
        "name": core_name(name),
        "year": item["year"] if item.get("year") is not None else _year(both),
        "semester": item["semester"] if item.get("semester") is not None else _semester(both),
        "round": item["round"] if item.get("round") is not None else _round(name),
    }


def same_scholarship(a: dict, b: dict) -> bool:
    """두 키가 같은 장학금인가. 연도·학기는 한쪽이 모르면 넘어가고, 차수는 둘 다 같아야 한다 (모름 ≠ 2차)."""
    if len(a["name"]) < 4 or len(b["name"]) < 4:
        return False  # 이름이 너무 짧으면 판단하지 않는다
    for field in ("year", "semester"):
        if a[field] is not None and b[field] is not None and a[field] != b[field]:
            return False
    if a["round"] != b["round"]:
        return False
    if a["name"] == b["name"]:
        return True
    return difflib.SequenceMatcher(None, a["name"], b["name"]).ratio() >= SAME_NAME


def _days_apart(a: str | None, b: str | None) -> int:
    if not a or not b:
        return 0
    return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days)


def _order(item: dict):
    return (item["source"].get("posted_at") or "", int(item["id"]))


def group_notices(items: list[dict]) -> list[list[dict]]:
    """공지(라벨이 있는 것만)를 게시 순서대로 보며 이벤트로 묶는다.

    - 모집 공지는 항상 새 이벤트를 연다. (같은 이름의 모집 공지가 또 오면 다음 차수나 재모집일 수 있다)
    - 수정·완료 공지는 같은 장학금인 이벤트 중 가장 최근 것에 붙는다. 없으면 혼자 이벤트가 된다.
    - 같은 장학금인지는 이벤트의 **첫 공지**와 비교한다 (사슬처럼 이어 묶지 않는다).
    """
    events: list[dict] = []  # {"key", "posted_at", "notices"}
    for item in sorted(items, key=_order):
        label = item["_label"]
        key = scholarship_key(item)
        posted = item["source"].get("posted_at")
        target = None
        if label != "모집":
            for ev in reversed(events):
                if _days_apart(ev["posted_at"], posted) <= MAX_DAYS and same_scholarship(ev["key"], key):
                    target = ev
                    break
        if target is None:
            events.append({"key": key, "posted_at": posted, "notices": [item]})
        else:
            target["notices"].append(item)
    return [ev["notices"] for ev in events]
