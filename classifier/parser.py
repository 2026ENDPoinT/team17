"""구문 분석: 공지 텍스트 → 문단(Section) 목록. 입력: 본문이나 첨부 텍스트 문자열 / 출력: Document.

컴파일러가 소스를 먼저 구문 트리로 바꾸고 다음 단계들이 그 트리를 같이 쓰듯이,
공지를 "지원자격 / 지원금액 / 신청기간 / 제출서류 / 우대·우선순위 / 일정 / 신청방법" 문단으로 한 번 나눈다.
값을 뽑는 함수(rules.py)는 그대로 두고, 어느 문단의 텍스트를 넣을지만 여기서 정한다.
"1순위: 4분위 이하"는 우선순위 문단에, "면접심사: 11.28"은 일정 문단에 있으니 소득·마감 추출이 볼 일이 없다.
"""

import re
from dataclasses import dataclass, field

from config import (
    CONDITION_LIST_MAX,
    SECTION_HEAD_MAX,
    SECTION_LINE_MAX,
    SECTION_WORD_POS,
    SECTION_WORDS,
    SECTION_WORDS_WITH_COLON,
)
from rules import LEVEL_NONE, conditions_from_block, level, lines_of, preference_tag, strip_marks

# 값을 뽑을 때 보지 않는 문단 (자격·금액·마감과 섞이면 틀린 값이 나오는 곳)
NOT_VALUE_KINDS = ["preference", "schedule", "method", "documents"]


@dataclass
class Section:
    """문단 하나. kind는 eligibility / preference / amount / period / schedule / documents / method / intro / other."""

    kind: str
    head: str | None  # 문단 제목 줄 (intro·other는 None)
    level: int  # 제목 줄의 번호 단계 (1. → 1, 가. → 2, 1) → 3, 가) → 4, ○·-·※ → 5, 없음 → 6)
    lines: list[str] = field(default_factory=list)  # 제목 줄을 포함한 문단의 줄
    # 제목만 있고 내용은 아래 줄에 있는 문단 ("※ 제외대상 |", "지원대상: 아래 조건을 모두 충족하는 자").
    # 이런 문단은 같은 단계의 기호 줄("- …")이 와도 끝나지 않는다
    header_only: bool = False
    item_level: int | None = None  # 제목만 있는 문단에서 첫 항목의 번호 단계


@dataclass
class Document:
    """공지 텍스트 하나를 문단으로 나눈 결과."""

    sections: list[Section]

    def text(self, kinds: list[str]) -> str:
        """kinds에 드는 문단의 줄만 이어 붙인다."""
        return "\n".join(line for s in self.sections if s.kind in kinds for line in s.lines)

    def text_except(self, kinds: list[str]) -> str:
        """kinds에 드는 문단을 뺀 나머지 줄을 이어 붙인다."""
        return "\n".join(line for s in self.sections if s.kind not in kinds for line in s.lines)

    def full(self) -> str:
        return "\n".join(line for s in self.sections for line in s.lines)

    def kinds(self) -> list[str]:
        return [s.kind for s in self.sections]


def section_kind(line: str) -> str | None:
    """줄이 문단 제목이면 문단 종류를, 아니면 None을 돌려준다."""
    cleaned = strip_marks(line)
    head, sep, _ = cleaned.partition(":")
    if sep:
        if len(head) > SECTION_HEAD_MAX:
            return None
        target, limit = head, len(head)
    else:
        if len(cleaned) > SECTION_LINE_MAX:
            return None
        target, limit = cleaned, SECTION_WORD_POS
    found: list[tuple[int, int, str]] = []  # (위치, 종류 순서, 종류)
    for order, (kind, words) in enumerate(SECTION_WORDS.items()):
        for word in words:
            at = target.find(word)
            if 0 <= at <= limit:
                found.append((at, order, kind))
    if sep:
        for kind, words in SECTION_WORDS_WITH_COLON.items():
            for word in words:
                if head.strip().endswith(word):
                    found.append((head.find(word), 99, kind))
    return min(found)[2] if found else None


def is_header_only(line: str) -> bool:
    """제목 줄에 내용이 없거나 '아래 조건', '다음과 같이'처럼 아래 줄을 가리키기만 하는지."""
    cleaned = strip_marks(line).strip(" |:")
    _, sep, rest = cleaned.partition(":")
    content = rest.strip(" |") if sep else ""
    return not content or "아래" in content or "다음" in content


def _ends_section(current: Section, lv: int) -> bool:
    """제목이 아닌 줄(번호 단계 lv)이 지금 문단을 끝내는지."""
    if current.level == LEVEL_NONE and lv == LEVEL_NONE:
        return False  # 번호 없는 제목 아래 번호 없는 줄은 이어진다
    if not current.header_only:
        return lv <= current.level
    # 제목만 있는 문단 ("※ 제외대상 |", "❍ 구비서류", "- 우대 사항:")은 첫 항목의 번호 단계를 따른다.
    # 공고문은 "❍ 구비서류" 아래에 "① …"처럼 더 큰 번호를 쓰기도 한다
    if current.item_level is None:
        big_heading = current.level <= 2  # "4. 지원자격" 바로 다음 "5. 선발인원"은 항목이 아니다
        return lv <= current.level if big_heading else lv <= 2
    if lv in (current.item_level, LEVEL_NONE):
        return False
    # 첫 항목이 번호 없는 표 머리("제출서류 | 비고")였고 그다음이 "① …"이면, ①이 항목 단계다
    if current.item_level == LEVEL_NONE and lv > current.level:
        current.item_level = lv
        return False
    # 항목 아래의 더 작은 줄은 이어지지만, 제목과 같은 기호의 줄("❍ …")은 다음 항목이다.
    # 번호 없는 항목 다음의 기호 줄("- 우대 사항:" 아래 두 줄, 그다음 "★ 필수 교육")도 끝난 것이다
    return not (lv > current.item_level and lv != current.level)


def parse(text: str) -> Document:
    """텍스트를 문단 트리로 나눈다. 열린 문단을 스택에 쌓는다 (바깥 문단이 아래, 안쪽 문단이 위).

    - 제목 줄: 같거나 깊은 단계의 열린 문단을 닫고, 새 문단을 연다 ("4. 지원자격" 안의 "- 우대사항:"은 안쪽 문단).
    - 제목이 아닌 줄: 그 줄의 번호 단계로 끝나는 문단을 닫고, 남은 맨 위 문단에 붙인다.
      "1) 1순위 / 2) 2순위 / 3) 3순위" 다음의 "4) 교수 추천 학생"처럼 닫힌 목록과 같은 단계(1)·가)·○)의 줄이면
      그 목록의 다음 항목으로 본다. "4. 지원자격" 다음의 "5. 선발인원"처럼 큰 항목이면 "other" 문단을 연다.
    - 첫 제목 전의 줄은 "intro" 문단이다.
    """
    intro = Section("intro", None, 0)
    sections = [intro]
    stack = [intro]
    for line in lines_of(text):
        kind = section_kind(line)
        lv = level(line)
        # 서류 목록 안의 "7) 우대조건(가산점 부여) 항목 증빙서류"는 새 문단이 아니라 서류 이름이다
        if kind and stack[-1].kind == "documents" and lv > stack[-1].level:
            kind = None
        if kind:
            while len(stack) > 1 and stack[-1].level >= lv:
                stack.pop()
            new = Section(kind, line, lv, [line], header_only=is_header_only(line))
            sections.append(new)
            stack.append(new)
            continue
        closed = None
        while len(stack) > 1 and _ends_section(stack[-1], lv):
            closed = stack.pop()
        # 닫힌 문단이 "1) 1순위: …"처럼 제목 줄 자체가 목록 항목이고, 이 줄도 이름표 없는 같은 단계 항목이면
        # 같은 목록이 이어지는 것이다. "◦ 근무장소: …"처럼 이름표가 있는 줄은 다른 항목이다
        if (closed is not None and closed.level == lv and lv >= 3 and not closed.header_only
                and closed.kind in ("eligibility", "preference") and ":" not in strip_marks(line)[:15]):
            new = Section(closed.kind, closed.head, lv, [line])  # 닫힌 목록의 다음 항목 (같은 문단 제목을 쓴다)
            sections.append(new)
            stack.append(new)
        elif len(stack) == 1 and len(sections) > 1:
            new = Section("other", None, lv, [line])  # 제목 없는 큰 항목 ("5. 선발인원: 2명")
            sections.append(new)
            stack.append(new)
        else:
            stack[-1].lines.append(line)
            if stack[-1].header_only and stack[-1].item_level is None:
                stack[-1].item_level = lv
    return Document([s for s in sections if s.lines])


def other_conditions(doc: Document) -> list[str]:
    """자격·우대 문단에서 값으로 못 바꾸는 조건 문장을 모은다. 우대 문단 줄에는 "우대:" 같은 이름표가 붙는다."""
    results: list[str] = []
    for s in doc.sections:
        if s.kind == "eligibility":
            found = conditions_from_block(s.lines, None)
        elif s.kind == "preference":
            found = conditions_from_block(s.lines, preference_tag(s.head or "") or "우대")
        else:
            continue
        results += [c for c in found if c not in results]
    return results[:CONDITION_LIST_MAX]


def describe(doc: Document) -> str:
    """문단 나눈 결과를 사람이 읽게 보여 준다 (디버깅용)."""
    out = []
    for s in doc.sections:
        out.append(f"[{s.kind}] " + re.sub(r"\s+", " ", (s.head or s.lines[0]))[:60] + f"  ({len(s.lines)}줄)")
    return "\n".join(out)
