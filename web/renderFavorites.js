// 즐겨찾기 페이지와 저장된 장학금 목록을 표시한다.
// 입력: 표시할 DOM 영역·즐겨찾기 항목·핸들러. 출력: 제목 바와 전체 너비의 목록 영역.
import { createScholarshipBlock } from './renderMain.js';
import { getToday } from './logic.js';

// 즐겨찾기 주소로 이동했을 때 제목·뒤로가기·스크롤 목록의 틀을 만든다.
export function renderFavorites(container, handlers) {
  const layout = document.createElement('div');
  layout.className = 'main-layout favorites-layout';
  const title = document.createElement('header');
  title.className = 'main-title';
  const heading = document.createElement('h1');
  heading.textContent = '즐겨찾기';
  const backButton = document.createElement('button');
  backButton.type = 'button';
  backButton.className = 'main-favorites-button';
  backButton.textContent = '뒤로가기';
  backButton.addEventListener('click', handlers.onBack);
  title.append(heading, backButton);
  const panel = document.createElement('div');
  panel.className = 'main-list-panel';
  const list = document.createElement('main');
  list.className = 'main-list';
  list.setAttribute('aria-label', '즐겨찾기한 장학금 목록');
  list.tabIndex = 0;
  panel.append(list);
  layout.append(title, panel);
  container.replaceChildren(layout);
  return { layout, title, list };
}

// 정상 이벤트는 메인 카드를 재사용하고, 사라진 이벤트는 안내와 즐겨찾기 해제 버튼을 표시한다.
export function renderFavoriteList(container, entries, favoriteIds, handlers) {
  const fragment = document.createDocumentFragment();
  const today = getToday();
  for (const entry of entries) {
    if (entry.item) {
      fragment.append(createScholarshipBlock(entry.item, handlers.onOpenDetail, today,
        favoriteIds, handlers.onToggleFavorite));
      continue;
    }
    const card = document.createElement('article');
    card.className = 'scholarship-block favorite-missing';
    const message = document.createElement('p');
    message.textContent = '더 이상 제공되지 않는 장학금입니다.';
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'main-favorites-button scholarship-favorite';
    remove.dataset.favoriteId = String(entry.id);
    remove.textContent = '즐겨찾기 해제';
    // 찾을 수 없는 항목도 저장 ID로 공통 해제 핸들러에 전달한다.
    remove.addEventListener('click', () => handlers.onToggleFavorite({ id: entry.id }));
    card.append(message, remove);
    fragment.append(card);
  }
  if (entries.length === 0) {
    const message = document.createElement('p');
    message.setAttribute('role', 'status');
    message.textContent = '즐겨찾기한 장학금이 없습니다.';
    fragment.append(message);
  }
  container.replaceChildren(fragment);
}
