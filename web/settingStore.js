// 같은 탭의 브라우저 저장소에 목록 설정을 저장하고 복원한다.
// 입력: 필터·정렬 이름·스크롤 위치. 출력: 복원할 설정 객체 또는 저장 성공 여부.
import { FILTER_OPTIONS } from './filterOptions.js';
const STORAGE_KEY = 'scholarship-hunter:main-settings';

// 저장된 목록 설정을 읽는다. 저장 내용이 없거나 손상됐으면 기본값을 반환한다.
export function loadSettings() {
  const defaults = {
    filters: { categories: [], grades: [], department: null, openOnly: false },
    sortBy: 'deadline', listScrollTop: 0,
  };
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY));
    if (!saved || typeof saved !== 'object') return defaults;
    const filters = saved.filters ?? {};
    return {
      filters: {
        // 저장된 값 중 유효한 유형만 복원한다.
        categories: Array.isArray(filters.categories)
          ? filters.categories.filter((value) => FILTER_OPTIONS.categories.includes(value)) : [],
        // 저장된 값 중 1~4학년만 복원한다.
        grades: Array.isArray(filters.grades)
          ? filters.grades.filter((value) => FILTER_OPTIONS.grades.includes(value)) : [],
        department: FILTER_OPTIONS.departments.includes(filters.department) ? filters.department : null,
        openOnly: filters.openOnly === true,
      },
      sortBy: saved.sortBy === 'deadline' ? saved.sortBy : 'deadline',
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
      listScrollTop: state.listScrollTop,
    }));
    return true;
  } catch {
    return false;
  }
}
