// 장학금 정보를 메인 블록에 표시할 문구로 가공한다.
// 입력: 장학금의 금액·마감·지원 조건. 출력: 표시용 문자열과 조건 배열.

// 현재 이벤트 ID 또는 소속 공지 bidx와 일치하는 저장 ID들을 반환한다. 합쳐진 이벤트도 찾는다.
export function getMatchingFavoriteIds(item, favoriteIds) {
  const noticeIds = new Set((item.notices ?? []).map((notice) => String(notice.bidx)));
  // 실제 ID의 event- 접두사를 제외해 공지 번호와 비교한다.
  return favoriteIds.filter((id) => String(id) === String(item.id) ||
    noticeIds.has(String(id).replace(/^event-/, '')));
}

// 저장한 순서대로 이벤트를 찾는다. 합쳐진 이벤트는 한 번만 남기고 사라진 ID는 item: null로 유지한다.
export function getFavoriteEntries(items, favoriteIds) {
  const entries = [];
  const seen = new Set();
  for (const id of favoriteIds) {
    // 현재 이벤트 ID를 먼저 찾고, 없으면 소속 공지 번호를 대조한다.
    const item = items.find((candidate) => String(candidate.id) === String(id)) ??
      items.find((candidate) => getMatchingFavoriteIds(candidate, [id]).length > 0);
    if (item && seen.has(String(item.id))) continue;
    if (item) seen.add(String(item.id));
    entries.push({ id, item: item ?? null });
  }
  return entries;
}

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

// 원본과 적용된 필터를 받아 조건에 맞는 새 목록을 반환한다. 같은 그룹은 OR, 그룹 사이는 AND다.
// amountType이 전달되면 해당 유형에서 금액이 확인된 항목만 남긴다.
export function filterScholarships(items, filters, today = getToday()) {
  const currentDate = parseDeadline(today);
  // 선택한 그룹만 검사하며, 그 그룹의 조건이 미확인이면 해당 장학금을 제외한다.
  return items.filter((item) => {
    const eligibility = item.eligibility ?? {};
    const uncertain = [...(eligibility.unclear ?? []), ...(item.needs_check ?? [])];
    if (filters.amountType && (item.amount?.type !== filters.amountType ||
        !Number.isFinite(item.amount?.value) || uncertain.includes('amount'))) return false;
    if (filters.categories.length > 0 &&
        (uncertain.includes('category') || !filters.categories.includes(item.category))) return false;
    if (filters.grades.length > 0) {
      if (uncertain.includes('grades') || !Array.isArray(eligibility.grades)) return false;
      // 선택한 학년 중 하나라도 대상 학년에 포함되면 이 그룹의 조건을 통과한다.
      if (!filters.grades.some((grade) => eligibility.grades.includes(grade))) return false;
    }
    if (filters.departments.length > 0 && (uncertain.includes('departments') ||
        !Array.isArray(eligibility.departments) ||
        // 선택한 학과 중 하나라도 지원 학과에 포함되면 통과한다.
        !filters.departments.some((department) => eligibility.departments.includes(department)))) return false;
    if (filters.openOnly) {
      const deadline = parseDeadline(item.deadline);
      if (item.closed === true || uncertain.includes('deadline') ||
          deadline === null || deadline < currentDate) return false;
    }
    return true;
  });
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

// 카드의 모집 상태·7일 이내 마감 여부·최신 수정 공지 게시일을 계산한다.
export function getRecruitmentStatus(item, today = getToday()) {
  const deadline = parseDeadline(item.deadline);
  const currentDate = parseDeadline(today);
  const closed = item.closed === true || item.status === '완료' ||
    (deadline !== null && deadline < currentDate);
  const uncertain = [...(item.eligibility?.unclear ?? []), ...(item.needs_check ?? [])];
  const open = !closed && deadline !== null && !uncertain.includes('deadline');
  let modified = false;
  let modifiedDate = null;
  for (const notice of item.notices ?? []) {
    if (notice.label !== '수정') continue;
    modified = true;
    if (parseDeadline(notice.posted_at) !== null &&
        (modifiedDate === null || notice.posted_at > modifiedDate)) {
      modifiedDate = notice.posted_at;
    }
  }
  return {
    label: closed ? '마감' : open ? '모집 중' : '마감일 미확인',
    urgent: open && currentDate !== null && deadline >= currentDate &&
      deadline - currentDate <= 7 * 86400000,
    modified: open && (modified || item.status === '수정'),
    modifiedDate,
  };
}

// 같은 금액 유형의 두 항목을 금액 내림차순으로 비교하고, 금액이 같으면 마감순으로 비교한다.
// 금액 유형과 미확인 값은 filterScholarships()에서 먼저 걸러낸다.
export function compareAmount(a, b, today = getToday()) {
  const difference = b.amount.value - a.amount.value;
  return difference || compareDeadline(a, b, today);
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
