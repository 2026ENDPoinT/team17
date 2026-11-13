// 원본 데이터와 화면 상태를 보관하고 데이터 읽기·정렬·화면 표시를 연결한다.
// 입력: 이벤트 JSON과 사용자 조작. 출력: 메인 화면.
import { loadScholarships } from './data.js';
import { sortScholarships, compareDeadline, compareAmount, filterScholarships } from './logic.js';
import { renderMain, renderScholarshipList, renderListStatus, renderSelectedFilters } from './renderMain.js';
import { renderDetail } from './renderDetail.js';
import { renderFilterPopup } from './renderFilterPopup.js';
import { loadSettings, saveSettings } from './settingStore.js';
import { AMOUNT_TYPES } from './filterOptions.js';

const state = {
  items: [],
  visibleItems: [],
  ...loadSettings(),
  loading: true,
  error: null,
  selectedId: null,
  view: 'loading',
};
const compareFunctions = { deadline: compareDeadline, amount: compareAmount };
const mainHandlers = {
  onOpenFilters: handleOpenFilterPopup,
  onResetFilters: handleResetFilters,
  onSortChange: handleSortChange,
  onAmountTypeChange: handleAmountTypeChange,
};
const app = document.getElementById('app');
let areas = renderMain(app, mainHandlers);
let filterPopup = null;

// 원본을 필터링한 뒤 정렬해 메인과 상세 이동이 공유할 표시 목록을 저장한다.
function updateVisibleItems() {
  const filters = {
    ...state.filters,
    amountType: state.sortBy === 'amount' ? state.amountType : null,
  };
  const filteredItems = filterScholarships(state.items, filters);
  state.visibleItems = sortScholarships(filteredItems, compareFunctions[state.sortBy]);
}

// 로딩·오류 안내 또는 보관 중인 표시 목록을 그린 뒤 스크롤 위치를 복원하고 설정을 저장한다.
function updateMain() {
  areas.sort.select.value = state.sortBy;
  areas.sort.select.disabled = state.loading || !!state.error;
  areas.sort.amountTypes.hidden = state.sortBy !== 'amount';
  for (const [type, button] of Object.entries(areas.sort.amountButtons)) {
    button.setAttribute('aria-pressed', String(type === state.amountType));
    button.disabled = state.loading || !!state.error;
  }
  areas.filterSelectButton.disabled = state.loading || !!state.error;
  areas.resetButton.disabled = state.loading || !!state.error;
  if (state.loading) return renderListStatus(areas.list, 'loading');
  if (state.error) return renderListStatus(areas.list, 'error');
  renderScholarshipList(areas.list, state.visibleItems, handleOpenDetail);
  renderSelectedFilters(areas.filters, state.filters, handleRemoveFilter);
  areas.list.scrollTop = state.listScrollTop;
  saveSettings(state);
}

// 드롭다운의 정렬 기준을 저장하고 목록을 재계산한다. 금액순으로 전환하면 일시금을 기본 선택한다.
function handleSortChange(sortBy) {
  if (!Object.hasOwn(compareFunctions, sortBy) || state.sortBy === sortBy) return;
  state.sortBy = sortBy;
  if (sortBy === 'amount') state.amountType = 'lump_sum';
  state.listScrollTop = 0;
  updateVisibleItems();
  updateMain();
}

// 금액 유형 버튼에서 호출하며, 유형 하나를 저장하고 필터링·정렬 후 목록을 맨 위부터 표시한다.
function handleAmountTypeChange(amountType) {
  if (state.sortBy !== 'amount' || !Object.hasOwn(AMOUNT_TYPES, amountType) ||
      state.amountType === amountType) return;
  state.amountType = amountType;
  state.listScrollTop = 0;
  updateVisibleItems();
  updateMain();
}

// 필터 선택 버튼에서 호출하며, 현재 적용 상태를 복사해 편집할 팝업을 연다.
function handleOpenFilterPopup() {
  if (state.loading || state.error || filterPopup?.open) return;
  filterPopup = renderFilterPopup(app, state.filters, { onApply: handleApplyFilters });
}

// 팝업이 전달한 필터를 저장하고 표시 목록을 재계산한 뒤 목록을 맨 위부터 그린다.
function handleApplyFilters(filters) {
  state.filters = structuredClone(filters);
  state.listScrollTop = 0;
  updateVisibleItems();
  updateMain();
}

// 메인의 선택된 필터 하나를 제거한다. 팝업을 거치지 않고 즉시 적용한다.
function handleRemoveFilter(key, value) {
  const filters = structuredClone(state.filters);
  if (Array.isArray(filters[key])) {
    const index = filters[key].indexOf(value);
    if (index >= 0) filters[key].splice(index, 1);
  } else {
    filters[key] = key === 'openOnly' ? false : null;
  }
  handleApplyFilters(filters);
}

// 메인의 초기화 버튼에서 호출하며, 적용된 모든 조건을 즉시 해제한다.
function handleResetFilters() {
  handleApplyFilters({ categories: [], grades: [], department: null, openOnly: false });
}

// 상세 주소를 변경한다. 실제 화면 표시는 주소 변경 이벤트가 담당하며 방문 기록도 남는다.
function handleOpenDetail(item) {
  window.location.hash = `/scholarships/${encodeURIComponent(item.id)}`;
}

// 상세에서 직접 접속했어도 이전 방문 기록에 관계없이 목록 주소로 이동한다.
function handleBackToList() {
  window.location.hash = '/';
}

// 현재 주소에 맞는 화면을 표시한다. 버튼 이동·뒤로/앞으로 가기·최초 접속에 공통으로 사용한다.
function handleRouteChange() {
  if (state.loading || state.error) return;
  if (filterPopup?.open) filterPopup.close();
  if (state.view === 'main') {
    state.listScrollTop = areas.list.scrollTop;
    saveSettings(state);
  }

  const hash = window.location.hash;
  if (hash === '' || hash === '#' || hash === '#/') {
    state.view = 'main';
    state.selectedId = null;
    areas = renderMain(app, mainHandlers);
    updateMain();
    // 목록 스크롤이 바뀔 때 저장해 목록에서 새로고침해도 위치를 복원한다.
    areas.list.addEventListener('scroll', () => {
      state.listScrollTop = areas.list.scrollTop;
      saveSettings(state);
    });
    return;
  }

  const match = hash.match(/^#\/scholarships\/([^/]+)$/);
  let id = null;
  try {
    if (match) id = decodeURIComponent(match[1]);
  } catch {
    // 잘못 인코딩된 주소도 찾을 수 없는 장학금 안내로 처리한다.
  }
  state.view = 'detail';
  state.selectedId = id;
  const items = state.visibleItems;
  // 주소의 ID에 해당하는 항목과 현재 목록에서의 위치를 찾는다.
  const item = state.items.find((candidate) => String(candidate.id) === id);
  // 이전·다음은 현재 정렬된 목록의 위치를 기준으로 선택한다.
  const index = items.findIndex((candidate) => String(candidate.id) === id);
  renderDetail(app, item, {
    previousItem: index > 0 ? items[index - 1] : null,
    nextItem: index >= 0 && index < items.length - 1 ? items[index + 1] : null,
    onOpenDetail: handleOpenDetail,
    onBack: handleBackToList,
  });
}

// 원본 데이터를 읽고 표시 목록을 계산한 뒤 현재 주소에 맞는 화면을 표시한다.
async function initialize() {
  updateMain();
  try {
    state.items = await loadScholarships();
    updateVisibleItems();
  } catch (error) {
    state.error = error;
  } finally {
    state.loading = false;
    if (state.error) updateMain();
    else handleRouteChange();
  }
}

// 주소가 바뀌면 같은 처리 함수를 실행해 브라우저 이동과 화면 표시를 일치시킨다.
window.addEventListener('hashchange', handleRouteChange);
// 새로고침·탭 이동 전에 현재 목록 위치를 마지막으로 저장한다.
window.addEventListener('pagehide', () => {
  if (state.view === 'main') state.listScrollTop = areas.list.scrollTop;
  saveSettings(state);
});
initialize();
