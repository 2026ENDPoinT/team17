// 메인 화면의 틀을 만들고 전달받은 데이터로 목록·설정·상태 표시를 갱신한다.
// 입력: DOM 영역·표시 데이터·이벤트 콜백. 출력: 메인 화면과 부분 갱신에 사용할 영역.
import { formatAmount, formatDeadline, getMainConditions, getToday, getRecruitmentStatus } from './logic.js';
import { AMOUNT_TYPES } from './filterOptions.js';

// main.js가 준비한 표시 데이터로 메인 영역을 갱신한다. 앱 상태 변경과 설정 저장은 하지 않는다.
export function updateMainView(areas, data, handlers) {
  const count = areas.title.querySelector('.main-list-count');
  const disabled = data.loading || !!data.error;
  count.hidden = disabled;
  count.textContent = disabled ? '' : `총 ${data.items.length}건`;
  areas.sort.select.value = data.sortBy;
  areas.sort.select.disabled = disabled;
  areas.sort.amountTypes.hidden = data.sortBy !== 'amount';
  areas.sort.amountSelect.value = data.amountType;
  areas.sort.amountSelect.disabled = disabled;
  areas.filterSelectButton.disabled = disabled;
  areas.resetButton.disabled = disabled;
  if (data.loading) return renderListStatus(areas.list, 'loading');
  if (data.error) return renderListStatus(areas.list, 'error');
  renderScholarshipList(areas.list, data.items, handlers.onOpenDetail,
    handlers.isFavorite, handlers.onToggleFavorite);
  renderSelectedFilters(areas.filters, data.filters, handlers.onRemoveFilter);
  areas.list.scrollTop = data.scrollTop;
}

// 데이터를 기다리거나 불러오기에 실패했을 때 왼쪽 영역에 상태 안내를 표시한다.
export function renderListStatus(container, status) {
  const message = document.createElement('div');
  message.className = 'main-list-status';
  message.setAttribute('role', 'status');
  if (status === 'loading') {
    const spinner = document.createElement('span');
    spinner.className = 'main-loading-spinner';
    spinner.setAttribute('aria-hidden', 'true');
    message.append(spinner, '로딩중');
  } else {
    message.textContent = '정보를 불러오는데 실패했습니다.';
  }
  container.replaceChildren(message);
}

// 목록이 바뀌면 왼쪽 영역만 다시 그린다. 즐겨찾기 여부는 전달받은 조회 함수로 확인한다.
export function renderScholarshipList(container, items, onOpenDetail, isFavorite, onToggleFavorite) {
  const fragment = document.createDocumentFragment();
  const today = getToday();

  for (const item of items) {
    fragment.append(createScholarshipBlock(item, onOpenDetail, today, isFavorite?.(item) ?? false, onToggleFavorite));
  }
  if (items.length === 0) {
    const message = document.createElement('p');
    message.textContent = '선택된 필터에 적합한 장학금이 없습니다.';
    fragment.append(message);
  }
  container.replaceChildren(fragment);
}

// 메인·즐겨찾기 공통 카드를 만든다. 별은 호출자가 계산한 선택 여부로 표시한다.
export function createScholarshipBlock(item, onOpenDetail, today, selected = false, onToggleFavorite) {
  const block = document.createElement('article');
  block.className = 'scholarship-block';
  const openButton = document.createElement('button');
  openButton.type = 'button';
  openButton.className = 'scholarship-open';

  const name = document.createElement('span');
  name.className = 'scholarship-name';
  name.textContent = item.name || '장학금명 미확인';

  const heading = document.createElement('span');
  heading.className = 'scholarship-heading';
  const status = getRecruitmentStatus(item, today);
  const statusArea = document.createElement('span');
  statusArea.className = 'scholarship-status';
  statusArea.textContent = status.label;
  if (status.modified) {
    statusArea.classList.add('scholarship-status-modified');
    const modified = document.createElement('span');
    modified.className = 'scholarship-modified';
    modified.textContent = '수정됨';
    const tooltip = document.createElement('span');
    tooltip.className = 'scholarship-status-tooltip';
    tooltip.id = `modified-date-${item.id}`;
    tooltip.setAttribute('role', 'tooltip');
    tooltip.textContent = `수정 공지 게시일: ${status.modifiedDate ?? '미확인'}`;
    openButton.setAttribute('aria-describedby', tooltip.id);
    statusArea.append(modified, tooltip);
  }
  heading.append(name, statusArea);

  const info = document.createElement('span');
  info.className = 'scholarship-info';
  const amount = document.createElement('span');
  amount.textContent = formatAmount(item.amount);
  info.append(amount);
  if (status.label === '모집 중') {
    const deadline = document.createElement('span');
    deadline.textContent = formatDeadline(item.deadline, today);
    deadline.title = item.deadline_text || '마감 상세 정보 미확인';
    info.append(deadline);
  }

  const conditions = document.createElement('span');
  conditions.className = 'scholarship-conditions';
  for (const condition of getMainConditions(item.eligibility)) {
    const line = document.createElement('span');
    line.className = 'scholarship-condition';
    line.textContent = condition;
    conditions.append(line);
  }

  const conditionsRow = document.createElement('span');
  conditionsRow.className = 'scholarship-conditions-row';
  conditionsRow.append(conditions);
  if (status.urgent) {
    const urgent = document.createElement('span');
    urgent.className = 'scholarship-deadline-urgent';
    urgent.textContent = '마감 임박';
    conditionsRow.append(urgent);
  }

  openButton.append(heading, info, conditionsRow);
  // 클릭한 장학금을 main.js의 상세 이동 함수에 전달한다.
  openButton.addEventListener('click', () => onOpenDetail(item));

  const favorite = document.createElement('button');
  favorite.type = 'button';
  favorite.className = 'scholarship-favorite';
  favorite.dataset.favoriteId = String(item.id);
  favorite.setAttribute('aria-pressed', String(selected));
  favorite.setAttribute('aria-label', `${item.name || '장학금'} 즐겨찾기 ${selected ? '해제' : '저장'}`);
  favorite.title = selected ? '즐겨찾기 해제' : '즐겨찾기 저장';
  favorite.disabled = !onToggleFavorite;
  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  icon.setAttribute('viewBox', '0 0 24 24');
  icon.setAttribute('aria-hidden', 'true');
  const star = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  star.setAttribute('d', 'M12 3 14.78 8.63 21 9.54 16.5 13.92 17.56 20.12 12 17.19 6.44 20.12 7.5 13.92 3 9.54 9.22 8.63Z');
  icon.append(star);
  favorite.append(icon);
  // 상세 이동 버튼과 독립적으로 저장·해제를 요청한다.
  favorite.addEventListener('click', () => onToggleFavorite?.(item));
  block.append(openButton, favorite);
  return block;
}

// 메인 틀과 즐겨찾기 변경 후 목록 갱신·포커스 복원 기능을 만들어 반환한다.
export function renderMain(container, handlers = {}) {
  const layout = document.createElement('div');
  layout.className = 'main-layout';

  const list = createListArea();
  const listPanel = document.createElement('div');
  listPanel.className = 'main-list-panel';
  listPanel.append(list);
  const sidebar = document.createElement('aside');
  sidebar.className = 'main-sidebar';
  sidebar.setAttribute('aria-label', '장학금 검색 설정');

  const title = createTitleArea(handlers.onOpenFavorites);
  const sort = createSortArea(handlers);
  const filters = createFilterArea(handlers.onOpenFilters);
  const resetButton = document.createElement('button');
  resetButton.type = 'button';
  resetButton.className = 'main-filter-reset';
  resetButton.textContent = '필터 초기화';
  resetButton.disabled = !handlers.onResetFilters;
  if (handlers.onResetFilters) resetButton.addEventListener('click', handlers.onResetFilters);

  filters.section.append(resetButton);
  sidebar.append(sort.section, filters.section);
  layout.append(title, listPanel, sidebar);
  container.replaceChildren(layout);

  // Manager의 성공 알림을 받으면 현재 스크롤로 목록 갱신을 요청하고 누른 별의 포커스를 복원한다.
  const updateFavorite = (item) => {
    handlers.onFavoriteChange?.(list.scrollTop);
    // 새 목록에서 같은 장학금의 별을 찾는다.
    const button = Array.from(list.querySelectorAll('.scholarship-favorite'))
      .find((candidate) => candidate.dataset.favoriteId === String(item.id));
    (button ?? list).focus({ preventScroll: true });
  };
  return { layout, list, title, sort, filters: filters.content, filterSelectButton: filters.selectButton, resetButton, updateFavorite };
}

// 적용된 필터를 학과별로도 각각 표시하고, 제거 버튼을 누르면 해당 조건만 호출자에게 전달한다.
export function renderSelectedFilters(container, filters, onRemove) {
  const entries = [];
  for (const value of filters.categories) entries.push(['categories', value, value]);
  for (const value of filters.grades) entries.push(['grades', value, `${value}학년`]);
  for (const value of filters.departments) entries.push(['departments', value, value]);
  if (filters.openOnly) entries.push(['openOnly', true, '모집 중만 보기']);
  const fragment = document.createDocumentFragment();
  for (const [key, value, label] of entries) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'main-selected-filter';
    button.textContent = `${label} ×`;
    button.setAttribute('aria-label', `${label} 필터 제거`);
    // 이 조건의 해제를 요청한다. 실제 상태 변경·계산은 main.js에서 수행한다.
    button.addEventListener('click', () => onRemove(key, value));
    fragment.append(button);
  }
  if (entries.length === 0) {
    const empty = document.createElement('p');
    empty.className = 'main-filter-empty';
    empty.textContent = '선택된 필터가 없습니다.';
    fragment.append(empty);
  }
  container.replaceChildren(fragment);
}

// 장학금 블록을 담을 왼쪽 스크롤 영역을 만든다.
function createListArea() {
  const list = document.createElement('main');
  list.className = 'main-list';
  list.setAttribute('aria-label', '장학금 목록');
  list.tabIndex = 0;
  return list;
}

// 서비스 제목·목록 건수 영역과 즐겨찾기 버튼을 만든다. 건수는 updateMainView에서 갱신한다.
function createTitleArea(onOpenFavorites) {
  const header = document.createElement('header');
  header.className = 'main-title';

  const heading = document.createElement('h1');
  heading.textContent = '장학금 헌터';
  const count = document.createElement('p');
  count.className = 'main-list-count';
  count.setAttribute('aria-live', 'polite');
  const favoritesButton = document.createElement('button');
  favoritesButton.type = 'button';
  favoritesButton.className = 'main-favorites-button';
  favoritesButton.textContent = '즐겨찾기';
  favoritesButton.disabled = !onOpenFavorites;
  if (onOpenFavorites) favoritesButton.addEventListener('click', onOpenFavorites);

  header.append(heading, count, favoritesButton);
  return header;
}

// 정렬·금액 유형 드롭다운을 만들고, 선택 변경을 main.js의 처리 함수에 전달한다.
function createSortArea(handlers) {
  const section = document.createElement('section');
  section.className = 'main-sort';
  section.setAttribute('aria-label', '정렬');

  const heading = document.createElement('h2');
  heading.textContent = '정렬';
  const select = document.createElement('select');
  select.setAttribute('aria-label', '정렬 기준');
  for (const [value, label] of [['deadline', '마감순'], ['amount', '금액순']]) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    select.append(option);
  }
  select.disabled = !handlers.onSortChange;
  // 선택된 기준을 전달한다. 상태 변경과 목록 재계산은 main.js에서 수행한다.
  select.addEventListener('change', (event) => handlers.onSortChange?.(event.target.value));

  const amountTypes = document.createElement('label');
  amountTypes.className = 'main-amount-types';
  amountTypes.hidden = true;
  const amountLabel = document.createElement('span');
  amountLabel.textContent = '금액 유형';
  const amountSelect = document.createElement('select');
  amountSelect.setAttribute('aria-label', '금액 유형');
  amountSelect.disabled = !handlers.onAmountTypeChange;
  for (const [value, label] of Object.entries(AMOUNT_TYPES)) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    amountSelect.append(option);
  }
  // 선택한 금액 유형을 전달한다. 상태 저장과 목록 갱신은 main.js에서 처리한다.
  amountSelect.addEventListener('change', (event) => handlers.onAmountTypeChange?.(event.target.value));
  amountTypes.append(amountLabel, amountSelect);
  section.append(heading, select, amountTypes);
  return { section, select, amountTypes, amountSelect };
}

// 필터 제목 옆에 팝업 열기 버튼을 두고 적용된 필터를 표시할 영역을 반환한다.
function createFilterArea(onOpenFilters) {
  const section = document.createElement('section');
  section.className = 'main-filters';
  section.setAttribute('aria-label', '필터');

  const heading = document.createElement('h2');
  heading.textContent = '필터';
  const header = document.createElement('div');
  header.className = 'main-filter-header';
  const selectButton = document.createElement('button');
  selectButton.type = 'button';
  selectButton.textContent = '필터 선택';
  selectButton.disabled = !onOpenFilters;
  if (onOpenFilters) selectButton.addEventListener('click', onOpenFilters);
  header.append(heading, selectButton);
  const content = document.createElement('div');
  content.className = 'main-filter-content';

  section.append(header, content);
  return { section, content, selectButton };
}
