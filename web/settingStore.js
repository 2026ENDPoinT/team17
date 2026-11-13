// 같은 탭의 브라우저 저장소에 목록 설정을 저장하고 복원한다.
// 입력: 필터·정렬 이름·금액 유형·스크롤 위치. 출력: 복원할 설정 객체 또는 저장 성공 여부.
import { FILTER_OPTIONS, AMOUNT_TYPES } from './filterOptions.js';
const STORAGE_KEY = 'scholarship-hunter:main-settings';

// 목록 설정을 복원하고 기존 단일 학과는 배열로 옮긴다. 없거나 손상된 설정은 기본값을 쓴다.
export function loadSettings() {
  const defaults = {
    filters: { categories: [], grades: [], departments: [], openOnly: false },
    sortBy: 'deadline', amountType: 'lump_sum', listScrollTop: 0,
  };
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY));
    if (!saved || typeof saved !== 'object') return defaults;
    const filters = saved.filters ?? {};
    const departments = Array.isArray(filters.departments)
      ? filters.departments : [filters.department];
    return {
      filters: {
        // 저장된 값 중 유효한 유형만 복원한다.
        categories: Array.isArray(filters.categories)
          ? filters.categories.filter((value) => FILTER_OPTIONS.categories.includes(value)) : [],
        // 저장된 값 중 1~4학년만 복원한다.
        grades: Array.isArray(filters.grades)
          ? filters.grades.filter((value) => FILTER_OPTIONS.grades.includes(value)) : [],
        // 기존 단일 선택도 보존하며, 중복과 유효하지 않은 학과를 제거한다.
        departments: [...new Set(departments.filter((value) => FILTER_OPTIONS.departments.includes(value)))],
        openOnly: filters.openOnly === true,
      },
      sortBy: saved.sortBy === 'amount' ? 'amount' : 'deadline',
      amountType: Object.hasOwn(AMOUNT_TYPES, saved.amountType) ? saved.amountType : 'lump_sum',
      listScrollTop: Number.isFinite(saved.listScrollTop) && saved.listScrollTop >= 0
        ? saved.listScrollTop : 0,
    };
  } catch {
    return defaults;
  }
}

// 원본 데이터와 함수는 제외하고 목록 설정만 저장한다. 저장소를 사용할 수 없어도 화면은 계속 동작한다.
export function saveSettings(state) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      filters: state.filters,
      sortBy: state.sortBy,
      amountType: state.amountType,
      listScrollTop: state.listScrollTop,
    }));
    return true;
  } catch {
    return false;
  }
}
