// 원본 데이터와 화면 상태를 보관하고 데이터 읽기·정렬·즐겨찾기·화면별 진입과 종료를 연결한다.
// 입력: 이벤트 JSON·저장된 즐겨찾기·사용자 조작. 출력: 메인·즐겨찾기·상세 화면.
import { loadScholarships } from './data.js';
import { sortScholarships, compareDeadline, compareAmount, filterScholarships } from './logic.js';
import { renderMain, updateMainView } from './renderMain.js';
import { renderDetail } from './renderDetail.js';
import { renderFilterPopup } from './renderFilterPopup.js';
import { loadSettings, saveSettings } from './settingStore.js';
import { AMOUNT_TYPES } from './filterOptions.js';
import { FavoriteManager } from './favoriteManager.js';
import { NavigationManager } from './navigationManager.js';
import { renderFavorites, updateFavoritesView } from './renderFavorites.js';

const state = {
  items: [],
  visibleItems: [],
  ...loadSettings(),
  favorites: new FavoriteManager({
    // 별 클릭 시점의 데이터·위치·탐색 순서만 Manager에 전달한다.
    getContext: () => ({ ...state.navigation.current, items: state.items, order: state.favoriteDetailOrder }),
    // 탐색 순서를 보관하고 현재 화면이 제공한 갱신 함수를 호출한다.
    onChange: (item, result) => {
      if (result.navigation) state.favoriteDetailOrder = result.navigation.order;
      const screen = state.navigation.current.view === 'detail' ? detailAreas : areas;
      screen.updateFavorite(item, result);
    },
    // 저장 실패 시 기존 화면을 유지하고 브라우저 저장 설정 확인을 안내한다.
    onError: () => window.alert('즐겨찾기를 저장하지 못했습니다. 브라우저의 사이트 저장 설정을 확인해 주세요.'),
  }),
  favoritesScrollTop: 0,
  navigation: new NavigationManager({
    main: { enter: enterMain, leave: leaveMain },
    favorites: { enter: enterFavorites, leave: leaveFavorites },
    detail: { enter: enterDetail },
  }),
  favoriteDetailOrder: [],
  loading: true,
  error: null,
};
const compareFunctions = { deadline: compareDeadline, amount: compareAmount };
const mainHandlers = {
  // 제목 버튼을 누르면 즐겨찾기 이동을 요청한다.
  onOpenFavorites: () => state.navigation.openFavorites(),
  onOpenFilters: handleOpenFilterPopup,
  onResetFilters: handleResetFilters,
  onSortChange: handleSortChange,
  onAmountTypeChange: handleAmountTypeChange,
  // 메인의 별 변경 후 현재 스크롤을 보관하고 목록과 별 표시를 갱신한다.
  onFavoriteChange: (scrollTop) => {
    state.listScrollTop = scrollTop;
    updateMain();
  },
};
const app = document.getElementById('app');
let areas = renderMain(app, mainHandlers);
let detailAreas = null;
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

// 메인에 필요한 데이터와 콜백을 renderMain.js에 전달하고, 정상 표시 상태의 설정을 저장한다.
function updateMain() {
  updateMainView(areas, {
    items: state.visibleItems,
    sortBy: state.sortBy,
    amountType: state.amountType,
    filters: state.filters,
    loading: state.loading,
    error: state.error,
    scrollTop: state.listScrollTop,
  }, {
    // 카드에서 선택한 장학금의 상세 이동을 요청한다.
    onOpenDetail: (item) => state.navigation.openDetail(item.id),
    isFavorite: state.favorites.isFavorite,
    onToggleFavorite: state.favorites.handleToggleFavorite,
    onRemoveFilter: handleRemoveFilter,
  });
  if (!state.loading && !state.error) saveSettings(state);
}

// Manager에서 즐겨찾기 목록을 준비해 표시 데이터와 콜백을 renderFavorites.js에 전달한다.
function updateFavorites() {
  const entries = state.favorites.getEntries(state.items);
  updateFavoritesView(areas, { entries, scrollTop: state.favoritesScrollTop }, {
    isFavorite: state.favorites.isFavorite,
    // 즐겨찾기 카드 클릭 시 해당 장학금의 상세 이동을 요청한다.
    onOpenDetail: (item) => state.navigation.openDetail(item.id),
    onToggleFavorite: state.favorites.handleToggleFavorite,
  });
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

// 금액 유형 드롭다운에서 호출하며, 유형 하나를 저장하고 필터링·정렬 후 목록을 맨 위부터 표시한다.
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

// 메인의 초기화 버튼에서 호출하며, 복수 학과를 포함한 모든 조건을 즉시 해제한다.
function handleResetFilters() {
  handleApplyFilters({ categories: [], grades: [], departments: [], openOnly: false });
}

// NavigationManager가 메인을 떠날 때 호출한다. 팝업을 닫고 목록 스크롤과 설정을 저장한다.
function leaveMain() {
  if (filterPopup?.open) filterPopup.close();
  state.listScrollTop = areas.list.scrollTop;
  saveSettings(state);
}

// NavigationManager가 메인에 진입할 때 호출한다. 목록·설정을 복원하고 스크롤 저장 이벤트를 연결한다.
function enterMain() {
  areas = renderMain(app, mainHandlers);
  updateMain();
  // 메인 목록 스크롤이 바뀔 때 저장해 새로고침 후에도 위치를 복원한다.
  areas.list.addEventListener('scroll', () => {
    state.listScrollTop = areas.list.scrollTop;
    saveSettings(state);
  });
}

// NavigationManager가 즐겨찾기를 떠날 때 호출한다. 목록 복귀에 사용할 스크롤을 보관한다.
function leaveFavorites() {
  state.favoritesScrollTop = areas.list.scrollTop;
}

// NavigationManager가 즐겨찾기에 진입할 때 호출한다. 목록·건수·스크롤을 복원한다.
function enterFavorites() {
  areas = renderFavorites(app, {
    // 즐겨찾기 목록의 뒤로가기 버튼을 누르면 메인 이동을 요청한다.
    onBack: () => state.navigation.backToList(),
    // 즐겨찾기 해제 후 현재 스크롤을 보관하고 목록과 건수를 갱신한다.
    onFavoriteChange: (scrollTop) => {
      state.favoritesScrollTop = scrollTop;
      updateFavorites();
    },
  });
  updateFavorites();
}

// NavigationManager가 해석한 위치로 상세 데이터와 이전·다음을 준비한 뒤 상세 화면을 표시한다.
function enterDetail({ selectedId, detailSource }) {
  let items = state.visibleItems;
  if (detailSource === 'favorites') {
    items = [];
    for (const { item } of state.favorites.getEntries(state.items)) {
      if (item) items.push(item);
    }
    // 즐겨찾기에 표시된 순서를 보관해 현재 항목을 해제한 뒤에도 이웃을 찾을 수 있게 한다.
    state.favoriteDetailOrder = items.map((item) => String(item.id));
  }
  // 주소의 ID에 해당하는 항목과 현재 목록에서의 위치를 찾는다.
  const item = state.items.find((candidate) => String(candidate.id) === selectedId);
  // 이전·다음은 현재 정렬된 목록의 위치를 기준으로 선택한다.
  const index = items.findIndex((candidate) => String(candidate.id) === selectedId);
  const detailHandlers = {
    isFavorite: item ? state.favorites.isFavorite(item) : false,
    onToggleFavorite: state.favorites.handleToggleFavorite,
    previousItem: index > 0 ? items[index - 1] : null,
    nextItem: index >= 0 && index < items.length - 1 ? items[index + 1] : null,
    // 이전·다음 버튼이 전달한 장학금의 상세 이동을 요청한다.
    onOpenDetail: (item) => state.navigation.openDetail(item.id),
    // 목록으로 버튼을 누르면 현재 상세의 출처 목록으로 복귀를 요청한다.
    onBack: () => state.navigation.backToList(),
  };
  detailAreas = renderDetail(app, item, detailHandlers);
}

// 원본과 표시 목록을 준비한 뒤 NavigationManager를 시작한다. 로딩 중 변경한 주소도 시작 시 읽는다.
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
    else state.navigation.start();
  }
}

// 새로고침·탭 이동 전에 현재 목록 위치를 마지막으로 저장한다.
window.addEventListener('pagehide', () => {
  if (state.navigation.current?.view === 'main') state.listScrollTop = areas.list.scrollTop;
  saveSettings(state);
});
initialize();
