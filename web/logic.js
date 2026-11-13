// 장학금 정보를 메인 블록에 표시할 문구로 가공한다.
// 입력: 장학금의 금액·마감·지원 조건. 출력: 표시용 문자열과 조건 배열.

// 한국의 오늘 날짜를 YYYY-MM-DD 형식으로 반환한다.
export function getToday() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date());
}

// 유효한 날짜를 숫자로 바꾸며, 날짜가 없거나 잘못되었으면 null을 반환한다.
function parseDeadline(deadline) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(deadline)) return null;
  const date = Date.parse(`${deadline}T00:00:00Z`);
  return Number.isFinite(date) && new Date(date).toISOString().slice(0, 10) === deadline
    ? date : null;
}

// 장학금 배열과 비교 함수를 받아, 원본을 바꾸지 않고 정렬한 새 배열을 반환한다.
export function sortScholarships(items, compareFunction) {
  return [...items].sort(compareFunction);
}

// 두 장학금을 모집 중 → 마감됨 → 날짜 미확인 순으로 비교한다.
// 음수면 a가 앞, 양수면 b가 앞, 0이면 기존 순서를 유지한다.
export function compareDeadline(a, b, today = getToday()) {
  const currentDate = parseDeadline(today);
  const dateA = parseDeadline(a.deadline);
  const dateB = parseDeadline(b.deadline);
  const groupA = dateA === null ? 2 : a.closed === true || dateA < currentDate ? 1 : 0;
  const groupB = dateB === null ? 2 : b.closed === true || dateB < currentDate ? 1 : 0;

  if (groupA !== groupB) return groupA - groupB;
  // 같은 그룹에서는 마감이 빠른 순서로 두고, 같은 날짜는 기존 순서를 유지한다.
  if (dateA === null || dateB === null) return 0;
  return dateA - dateB;
}

// 금액을 일시금·등록금 비율·시급에 맞는 문구로 바꾸며, 알 수 없으면 미확인으로 표시한다.
export function formatAmount(amount) {
  if (!Number.isFinite(amount?.value)) return '금액 미확인';

  const value = amount.value.toLocaleString('ko-KR');
  switch (amount.type) {
    case 'lump_sum': return `${value}원`;
    case 'tuition_ratio': return `등록금 ${value}%`;
    case 'hourly': return `시급 ${value}원`;
    default: return '금액 미확인';
  }
}

// 마감 날짜와 기준 날짜로 D-day 문구를 만든다. 기준 날짜를 생략하면 한국의 오늘 날짜를 쓴다.
export function formatDeadline(deadline, today) {
  const end = parseDeadline(deadline);
  if (end === null) return '마감 미확인';
  const currentDate = today ?? getToday();
  const days = Math.round((end - Date.parse(`${currentDate}T00:00:00Z`)) / 86400000);
  const label = days > 0 ? `D-${days}` : days === 0 ? 'D-day' : `D+${-days}`;
  return `${deadline} (${label})`;
}

// 확인된 조건을 학년 → 학과 → 성적 → 소득 → 거주지 순서로 최대 3개 골라 반환한다.
export function getMainConditions(eligibility = {}) {
  const conditions = [];
  const unclear = eligibility?.unclear ?? [];
  // 해당 조건에 값이 있고, 불확실한 조건으로 분류되지 않았는지 확인한다.
  const known = (key) => eligibility?.[key] != null && !unclear.includes(key);

  if (known('grades') && eligibility.grades.length > 0) {
    conditions.push(`${eligibility.grades.join('·')}학년`);
  }
  if (known('departments') && eligibility.departments.length > 0) {
    conditions.push(eligibility.departments.join('·'));
  }
  if (known('gpa_min')) conditions.push(`성적 ${eligibility.gpa_min} 이상`);
  if (known('score_min')) conditions.push(`백분위 성적 ${eligibility.score_min}점 이상`);
  if (known('income_max')) conditions.push(`소득 ${eligibility.income_max}분위 이하`);
  if (known('residence') && eligibility.residence.trim()) {
    conditions.push(`거주지 ${eligibility.residence}`);
  }
  if (known('other_conditions')) conditions.push(...eligibility.other_conditions);

  return conditions.length > 0 ? conditions.slice(0, 3) : ['지원 조건 미확인'];
}
