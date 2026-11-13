// 메인 화면의 전체 배치와 영역별 틀을 만든다.
// 입력: 화면을 넣을 DOM 요소. 출력: 이후 갱신에 사용할 영역별 DOM 요소.
import { formatAmount, formatDeadline, getMainConditions, getToday } from './logic.js';

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
export function renderScholarshipList(container, items, onOpenDetail) {
  const fragment = document.createDocumentFragment();
  const today = getToday();

  for (const item of items) {
    fragment.append(createScholarshipBlock(item, onOpenDetail, today));
  }
  if (items.length === 0) {
    const message = document.createElement('p');
    message.textContent = '선택된 필터에 적합한 장학금이 없습니다.';
    fragment.append(message);
  }
  container.replaceChildren(fragment);
}

// 장학금 한 건을 세 줄짜리 블록으로 만들고, 클릭하면 전달받은 상세 이동 함수를 호출한다.
export function createScholarshipBlock(item, onOpenDetail, today) {
  const block = document.createElement('button');
  block.type = 'button';
  block.className = 'scholarship-block';

  const name = document.createElement('span');
  name.className = 'scholarship-name';
  name.textContent = item.name || '장학금명 미확인';

  const info = document.createElement('span');
  info.className = 'scholarship-info';
  const amount = document.createElement('span');
  amount.textContent = formatAmount(item.amount);
  const deadline = document.createElement('span');
  deadline.textContent = `${formatDeadline(item.deadline, today)}${item.closed === true ? ' · 마감됨' : ''}`;
  deadline.title = item.deadline_text || '마감 상세 정보 미확인';
  info.append(amount, deadline);

  const conditions = document.createElement('span');
  conditions.className = 'scholarship-conditions';
  conditions.textContent = getMainConditions(item.eligibility).join(' / ');

  block.append(name, info, conditions);
  block.addEventListener('click', () => onOpenDetail(item));
  return block;
}

// 메인 화면의 좌우 틀을 만들고, 이후 부분 갱신에 사용할 각 영역을 반환한다.
export function renderMain(container, handlers = {}) {
  const layout = document.createElement('div');
  layout.className = 'main-layout';

  const list = createListArea();
  const sidebar = document.createElement('aside');
  sidebar.className = 'main-sidebar';
  sidebar.setAttribute('aria-label', '장학금 검색 설정');

  const title = createTitleArea();
  const sort = createSortArea();
  const filters = createFilterArea(handlers.onOpenFilters);
  const resetButton = document.createElement('button');
  resetButton.type = 'button';
  resetButton.className = 'main-filter-reset';
  resetButton.textContent = '필터 초기화';
  resetButton.disabled = !handlers.onResetFilters;
  if (handlers.onResetFilters) resetButton.addEventListener('click', handlers.onResetFilters);

  sidebar.append(title, sort, filters.section, resetButton);
  layout.append(list, sidebar);
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

// 오른쪽 위에 표시할 서비스 제목과 설명 영역을 만든다.
function createTitleArea() {
  const header = document.createElement('header');
  header.className = 'main-title';

  const heading = document.createElement('h1');
  heading.textContent = '장학금 헌터';
  const description = document.createElement('p');
  description.textContent = '교내 게시판의 장학금을 모아 금액·마감·지원 조건을 비교하세요.';

  header.append(heading, description);
  return header;
}

// 현재 정렬 기준인 마감순을 표시하는 영역을 만든다.
function createSortArea() {
  const section = document.createElement('section');
  section.className = 'main-sort';
  section.setAttribute('aria-label', '정렬');

  const heading = document.createElement('h2');
  heading.textContent = '정렬';
  const value = document.createElement('p');
  value.textContent = '마감순';

  section.append(heading, value);
  return section;
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
