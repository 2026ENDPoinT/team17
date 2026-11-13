// 메인 화면의 전체 배치와 영역별 틀을 만든다.
// 입력: 화면을 넣을 DOM 요소. 출력: 이후 갱신에 사용할 영역별 DOM 요소.
import { formatAmount, formatDeadline, getMainConditions, getToday, getRecruitmentStatus, getMatchingFavoriteIds } from './logic.js';
import { AMOUNT_TYPES } from './filterOptions.js';

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

// 목록이 바뀌면 왼쪽 영역만 다시 그린다. 상세 이동 동작은 호출자가 전달한다.
export function renderScholarshipList(container, items, onOpenDetail, favoriteIds = [], onToggleFavorite) {
  const fragment = document.createDocumentFragment();
  const today = getToday();

  for (const item of items) {
    fragment.append(createScholarshipBlock(item, onOpenDetail, today, favoriteIds, onToggleFavorite));
  }
  if (items.length === 0) {
    const message = document.createElement('p');
    message.textContent = '선택된 필터에 적합한 장학금이 없습니다.';
    fragment.append(message);
  }
  container.replaceChildren(fragment);
}

// 카드 내용은 상세 이동 버튼에, 오른쪽 아래 별은 별도의 즐겨찾기 버튼에 연결한다.
export function createScholarshipBlock(item, onOpenDetail, today, favoriteIds = [], onToggleFavorite) {
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

  openButton.append(heading, info, conditions);
  // 클릭한 장학금을 main.js의 상세 이동 함수에 전달한다.
  openButton.addEventListener('click', () => onOpenDetail(item));

  const favorite = document.createElement('button');
  favorite.type = 'button';
  favorite.className = 'scholarship-favorite';
  favorite.dataset.favoriteId = String(item.id);
  const selected = getMatchingFavoriteIds(item, favoriteIds).length > 0;
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

// 상단 제목 바와 아래쪽 목록·설정 박스를 만들고 부분 갱신용 영역을 반환한다.
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

  return { layout, list, title, sort, filters: filters.content, filterSelectButton: filters.selectButton, resetButton };
}

// 메인에 적용된 필터만 표시하고, 각 제거 버튼을 누르면 해당 조건을 호출자에게 전달한다.
export function renderSelectedFilters(container, filters, onRemove) {
  const entries = [];
  for (const value of filters.categories) entries.push(['categories', value, value]);
  for (const value of filters.grades) entries.push(['grades', value, `${value}학년`]);
  if (filters.department) entries.push(['department', filters.department, filters.department]);
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

// 서비스 제목·설명과 오른쪽 즐겨찾기 버튼을 만들고 전달받은 클릭 핸들러를 연결한다.
function createTitleArea(onOpenFavorites) {
  const header = document.createElement('header');
  header.className = 'main-title';

  const heading = document.createElement('h1');
  heading.textContent = '장학금 헌터';
  const description = document.createElement('p');
  description.textContent = '교내 게시판의 장학금을 모아 금액·마감·지원 조건을 비교하세요.';
  const favoritesButton = document.createElement('button');
  favoritesButton.type = 'button';
  favoritesButton.className = 'main-favorites-button';
  favoritesButton.textContent = '즐겨찾기';
  favoritesButton.disabled = !onOpenFavorites;
  if (onOpenFavorites) favoritesButton.addEventListener('click', onOpenFavorites);

  header.append(heading, description, favoritesButton);
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
