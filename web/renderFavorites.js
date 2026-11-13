// 즐겨찾기 화면의 틀을 만들고 전달받은 목록·건수·스크롤을 화면에 반영한다.
// 입력: DOM 영역·표시 데이터·이벤트 콜백. 출력: 즐겨찾기 화면과 부분 갱신에 사용할 영역.
import { createScholarshipBlock } from './renderMain.js';
import { getToday } from './logic.js';

// main.js가 연결한 즐겨찾기 항목으로 건수와 목록을 갱신하고 스크롤을 복원한다.
export function updateFavoritesView(areas, data, handlers) {
  areas.title.querySelector('.main-list-count').textContent = `총 ${data.entries.length}건`;
  renderFavoriteList(areas.list, data.entries, handlers);
  areas.list.scrollTop = data.scrollTop;
}

// 즐겨찾기 화면 틀과 해제 후 갱신·포커스 복원 기능을 반환한다. 건수는 updateFavoritesView에서 갱신한다.
export function renderFavorites(container, handlers) {
  const layout = document.createElement('div');
  layout.className = 'main-layout favorites-layout';
  const title = document.createElement('header');
  title.className = 'main-title';
  const heading = document.createElement('h1');
  heading.textContent = '즐겨찾기';
  const count = document.createElement('p');
  count.className = 'main-list-count';
  count.setAttribute('aria-live', 'polite');
  const backButton = document.createElement('button');
  backButton.type = 'button';
  backButton.className = 'main-favorites-button';
  backButton.textContent = '뒤로가기';
  backButton.addEventListener('click', handlers.onBack);
  title.append(heading, count, backButton);
  const panel = document.createElement('div');
  panel.className = 'main-list-panel';
  const list = document.createElement('main');
  list.className = 'main-list';
  list.setAttribute('aria-label', '즐겨찾기한 장학금 목록');
  list.tabIndex = 0;
  panel.append(list);
  layout.append(title, panel);
  container.replaceChildren(layout);
  // Manager의 성공 알림을 받으면 스크롤 보존과 목록 갱신을 요청하고 가능한 요소로 포커스를 복원한다.
  const updateFavorite = (item) => {
    handlers.onFavoriteChange?.(list.scrollTop);
    // 갱신 후 남아 있는 같은 항목의 버튼을 찾고, 없어졌으면 목록에 포커스를 둔다.
    const button = Array.from(list.querySelectorAll('.scholarship-favorite'))
      .find((candidate) => candidate.dataset.favoriteId === String(item.id));
    (button ?? list).focus({ preventScroll: true });
  };
  return { layout, title, list, updateFavorite };
}

// 전달받은 즐겨찾기 조회로 카드를 표시하고, 사라진 이벤트에는 안내와 해제 버튼을 표시한다.
export function renderFavoriteList(container, entries, handlers) {
  const fragment = document.createDocumentFragment();
  const today = getToday();
  for (const entry of entries) {
    if (entry.item) {
      fragment.append(createScholarshipBlock(entry.item, handlers.onOpenDetail, today,
        handlers.isFavorite(entry.item), handlers.onToggleFavorite));
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
    // 찾을 수 없는 항목도 저장 ID로 Manager의 해제 처리에 전달한다.
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
