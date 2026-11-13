"""규칙 정답 세트. 문장 하나를 넣었을 때 나와야 하는 값을 적어 두고, 규칙이 몇 개를 맞히는지 센다.

실행: uv run python classifier/check_rules.py
규칙을 고친 뒤 실행해서 맞힌 수가 줄지 않았는지 본다. 틀린 항목은 무엇이 나왔는지 같이 출력한다.
문장은 data/raw의 실제 공지에서 가져온 것(bidx 표시)과, 자주 나올 만한 함정 문장을 섞었다.
"""

from extract import split_by_deadline
from rules import (
    extract_amount,
    extract_departments,
    extract_eligibility,
    extract_residence,
    has_interview,
    prepare_attachment_text,
)


def interview(text):
    return has_interview(text)


def grades(text):
    return extract_eligibility(text)["grades"]


def gpa(text):
    return extract_eligibility(text)["gpa_min"]


def score(text):
    return extract_eligibility(text)["score_min"]


def income(text):
    return extract_eligibility(text)["income_max"]


def amount(text):
    return extract_amount(text)[0]["value"]


def departments(text):
    return extract_departments(text)[0]


def residence(text):
    return extract_residence("", text)[0]


# 재게시 묶음 나누기용 가짜 공지 3건. 크롤러가 셋 다 1번 글로 묶었다고 가정한다 (2, 3 → 1).
# 값: (2번 마감일, 3번 마감일, 3번 제목). 1번 마감일은 2026-11-06.
GROUPS = {
    "마감일 같음": ("2026-11-06", "2026-11-06", "장학생 선발 안내"),
    "마감일 다름": ("2026-12-04", "2026-11-06", "장학생 선발 안내"),
    "마감일 다름 2건": ("2026-12-04", "2026-12-04", "장학생 선발 안내"),
    "마감일 모름": (None, None, "장학생 선발 안내"),
    "기간 연장": ("2026-11-13", "2026-11-13", "장학생 선발 안내(신청기간 연장)"),
}


def regroup(name):
    d2, d3, title3 = GROUPS[name]
    items = {
        "1": {"id": "1", "title": "장학생 선발 안내", "deadline": "2026-11-06", "duplicate_of": None,
              "source": {"posted_at": "2026-10-20"}},
        "2": {"id": "2", "title": "장학생 선발 안내", "deadline": d2, "duplicate_of": "1",
              "source": {"posted_at": "2026-10-21"}},
        "3": {"id": "3", "title": title3, "deadline": d3, "duplicate_of": "1", "source": {"posted_at": "2026-10-22"}},
    }
    if name == "기간 연장":
        items["2"]["title"] = title3
    split_by_deadline(items, {"1": "www", "2": "dept", "3": "dept"})
    return {k: v["duplicate_of"] for k, v in items.items()}


# (필드 함수, 입력 문장, 정답, 설명)
CASES = [
    # ── 면접 ──
    (interview, "6. 선발 방법: 서류 심사 후 면접 (12월 초 개별 안내)", True, "면접 있음"),
    (interview, "※지원서 제출 후 1차 선발예정자에 한하여 개별 연락 및 면접 진행 예정", True, "896364"),
    (interview, "선발 방법: 서류 심사 (면접 없음)", False, "면접 없음"),
    (interview, "선발 방법: 서류평가로 선발하며 면접은 실시하지 않음", False, "면접 실시하지 않음"),
    (interview, "- 면접 생략, 서류 100%", False, "면접 생략"),
    # ── 학년 ──
    (grades, "1. 지원 대상: 본교 재학생 2~4학년, 직전 학기 성적 3.0 이상", [2, 3, 4], "학년 범위"),
    (grades, "○ 2027년도 1학기 기준, 3학년 1학기에 등록예정인 자", [3], "897477"),
    (grades, "지원자격: 3학년 이상 재학생, 2학년 이하 우대", [3, 4], "'3학년 이상'은 3~4학년, 우대 학년은 조건 아님"),
    (grades, "지원자격: 3학년 재학생 (2학년 우대)", [3], "같은 줄의 우대 학년만 거름"),
    (grades, "- 우대사항: 관련학과, 직전학기 미선발자, 2학년 이하, 실험실활동 유경험자", None, "897699 우대 줄"),
    (grades, "1순위: 4학년 재학생", None, "순위는 자격 아님"),
    # ── 평점·점수 ──
    (gpa, "- 성적기준 : 2026년 1학기 평균 평점 4.5만점에 3.0이상", 3.0, "896404"),
    (gpa, "지원자격: 직전학기 평점 3.0 이상 (평점 4.0 이상 우대)", 3.0, "같은 줄의 우대 평점만 거름"),
    (gpa, "가산점: 평점 4.0 이상인 자", None, "가산점 줄"),
    (score, "○ 전체학기 백분율 성적 85점 이상인 자", 85, "897477"),
    (score, "- 2026학년도 2학기 재학생으로 직전학기 성적 C0(70점/100점 만점) 이상인 학생", 70, "897503"),
    # ── 소득 ──
    (income, "- 학자금지원구간 9구간 이하에 해당하는 자", 9, "897503"),
    (income, "1. 지원 대상: 본교 재학생, 학자금 지원구간 0~6구간", 6, "구간 범위"),
    (income, "1순위: 학자금지원구간 4분위 이하", None, "순위는 자격 아님"),
    (income, "지원자격: 학자금 지원구간 8구간 이하 (3구간 이하 우선 선발)", 8, "같은 줄의 우선 선발 구간만 거름"),
    # ── 금액 ──
    (amount, "2. 지원금액: 1인당 500만원(250만원×2개 학기) ※ 생활비성 장학금", 5000000, "895588"),
    (amount, "- 장학금 : 학기당 300만 원(연 600만 원), 학업보조비·생활비, 최대 6학기 지원", 3000000, "896300"),
    (amount, "지원금액: 총 예산 5,000만원 범위 내 1인당 200만원", 2000000, "총 예산은 1인당 금액 아님"),
    (amount, "장학금액: 작년 지급액 150만원, 올해 1인당 200만원", 2000000, "작년 금액은 건너뜀"),
    (amount, "라. 지원내역: 수업료 100% 면제(단, 차상위~5구간 학생 중 국가장학 Ⅰ유형 미수혜 학생은 50%만 면제)", 100, "896900"),
    (amount, "❍ 장학금: 고등학생 50만원, 대학생 최대 100만원", 1000000, "896254 첨부, 대상별 금액은 대학생"),
    (amount, "금액) 지급하며 실 납부금액이 100만원 미만일 시 지원 대상 제외", None, "895660 첨부, 기준 금액"),
    (amount, "① 등록금 납부액 | 4,000,000원 | ② 다른 기관에서 받은 장학금 | 2,000,000원 | ③ 신청금액(①-②)", None,
     "897117 첨부, 계산 예시"),
    (amount, prepare_attachment_text("\x00 \x00지급액:\x002026년\x002학기\x00등록금\x00전액"), 100, "895660 첨부, PDF의 \\x00 공백"),
    (amount, prepare_attachment_text("Ⅱ 선 발 대 상 및 지 급 액\n지 급 액: 1인당 200만원"), 2000000, "PDF의 띄어 쓴 글자"),
    # ── 학과 ──
    (departments, "지원대상: 전기정보공학과, 전자공학과 재학생", ["전기정보공학과", "전자공학과"], "학과 두 곳"),
    (departments, "1) 안전공학과 재학생(※ 단, 4학년은 제외)", ["안전공학과"], "897508"),
    (departments, "※ 관련학과: X선분석실-화공생명공학과, 신소재공학과", None, "897699 우대사항의 관련학과"),
    (departments, "지원자격: 본교 재학생 (문의: 전기정보공학과 사무실)", None, "문의처 학과"),
    (departments, "정보통신대학 컴퓨터공학과에서는 학생들에게 취업 준비 지원을 위하여 재학생을 대상으로 모집합니다",
     None, "897737 주관 학과"),
    (departments, "서울과학기술대학교 산업공학과 동문회에서는 동문 재학생을 대상으로 장학금을 지원합니다",
     ["산업공학과"], "895611 학과 동문 대상"),
    (departments, "지원대상: 벤처경영학과 재학생", ["벤처경영학과"], "겹치는 이름"),
    # ── 거주지 ──
    (residence, "4. 신청자격 : 공고일 현재 은평구에 2년 이상 계속 거주하고 있는 초 · 중 · 고 · 대학생", "은평구", "896404"),
    (residence, "지원대상: 부 또는 모가 부산광역시에 주민등록이 되어 있는 자", "부산광역시", "부모 주민등록"),
    (residence, "- 희망사항: 학교인근 거주자 우대, 컴퓨터활용능력자격증 소지자 우대 (필수사항은 아님)", None, "897664"),
    (residence, "5. 신청방법 : 등기우편 및 방문접수 (서울특별시 은평구 은평로195 은평구청 3층 시민교육과)", None, "896404 접수처"),
    (residence, "지원자격: 서울 소재 대학 재학생, 거주지 무관", None, "학교 위치·무관"),
    # ── 재게시 묶음 나누기 (입력: 아래 GROUPS의 이름, 출력: {id: duplicate_of}) ──
    (regroup, "마감일 같음", {"1": None, "2": "1", "3": "1"}, "같은 마감일이면 크롤러 묶음 그대로"),
    (regroup, "마감일 다름", {"1": None, "2": None, "3": "1"}, "2차 모집(마감일 다름)은 따로 대표"),
    (regroup, "마감일 다름 2건", {"1": None, "2": None, "3": "2"}, "같은 새 마감일끼리는 다시 묶임"),
    (regroup, "마감일 모름", {"1": None, "2": "1", "3": "1"}, "마감일을 모르면 나눌 근거가 없음"),
    (regroup, "기간 연장", {"1": None, "2": "1", "3": "1"}, "제목에 '연장'이면 같은 공지"),
]


def main() -> None:
    passed = 0
    by_field: dict[str, list[int]] = {}
    for func, text, expected, note in CASES:
        got = func(text)
        ok = got == expected
        passed += ok
        stat = by_field.setdefault(func.__name__, [0, 0])
        stat[0] += ok
        stat[1] += 1
        if not ok:
            print(f"  틀림 [{func.__name__}] {note}: 정답 {expected!r}, 결과 {got!r}\n        {text[:70]}")
    print()
    for name, (ok, total) in by_field.items():
        print(f"  {name:12s} {ok}/{total}")
    print(f"맞힘 {passed}/{len(CASES)}")


if __name__ == "__main__":
    main()
