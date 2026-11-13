// 즐겨찾기 ID·추가·해제·탐색을 관리하고 처리 결과를 화면 갱신 콜백에 전달한다.
// 입력: 장학금·화면 맥락 조회와 결과 콜백. 출력: 즐겨찾기 상태·목록·탐색 결과와 갱신 요청.
import { loadFavorites, saveFavorites } from './favoriteStore.js';

export class FavoriteManager {
  #ids;
  #handlers;

  // 저장 ID를 복원하고 화면 맥락 조회·성공·실패 콜백을 보관한다. 아직 콜백은 실행하지 않는다.
  constructor(handlers = {}) {
    this.#ids = loadFavorites();
    this.#handlers = handlers;
  }

  // 이벤트 ID 또는 소속 공지 번호에 해당하는 저장 ID들을 찾는다.
  #getMatchingIds(item) {
    // 합쳐진 이벤트에서도 기존 공지 번호로 저장된 즐겨찾기를 연결한다.
    const noticeIds = new Set((item.notices ?? []).map((notice) => String(notice.bidx)));
    // 같은 이벤트를 가리키는 저장 ID를 모두 찾아 해제할 때도 함께 제거한다.
    return this.#ids.filter((id) => id === String(item.id) ||
      noticeIds.has(id.replace(/^event-/, '')));
  }

  // 현재 장학금의 즐겨찾기 여부를 반환한다. 화면 콜백으로 전달해도 이 객체를 유지한다.
  isFavorite = (item) => {
    return this.#getMatchingIds(item).length > 0;
  };

  // 별 클릭을 받아 저장한다. 실패를 알리거나 상세 탐색 계산 후 화면 갱신 콜백을 호출한다.
  handleToggleFavorite = (item) => {
    const result = this.toggle(item);
    if (!result.success) {
      this.#handlers.onError?.();
      return result;
    }
    const context = this.#handlers.getContext?.();
    if (context?.view === 'detail' && context.detailSource === 'favorites') {
      result.navigation = this.updateFavoriteNavigation(context.items, context.selectedId, context.order);
    }
    this.#handlers.onChange?.(item, result);
    return result;
  };

  // 저장 순서로 현재 장학금에 연결한다. 합쳐진 항목은 한 번만, 사라진 항목은 null로 남긴다.
  getEntries(items) {
    const entries = [];
    const seen = new Set();
    for (const id of this.#ids) {
      // 현재 이벤트 ID를 먼저 찾는다.
      const item = items.find((candidate) => String(candidate.id) === id) ??
        // 이벤트 ID가 바뀌었으면 소속 공지 번호를 대조한다.
        items.find((candidate) => (candidate.notices ?? []).some(
          // 저장 ID의 접두사를 제외한 값과 공지 번호를 비교한다.
          (notice) => String(notice.bidx) === id.replace(/^event-/, '')));
      if (item && seen.has(String(item.id))) continue;
      if (item) seen.add(String(item.id));
      entries.push({ id, item: item ?? null });
    }
    return entries;
  }

  // 추가·해제할 ID를 계산하고 저장한다. 저장에 성공한 경우에만 내부 상태를 변경한다.
  toggle(item) {
    const matchingIds = this.#getMatchingIds(item);
    const selected = matchingIds.length > 0;
    // 해제하면 같은 이벤트에 대응하는 저장 ID를 모두 제거한다.
    const nextIds = selected
      ? this.#ids.filter((id) => !matchingIds.includes(id))
      : [...this.#ids, String(item.id)];
    if (!saveFavorites(nextIds)) return { success: false, selected };
    this.#ids = nextIds;
    return { success: true, selected: !selected };
  }

  // 별 변경 후 상세의 이전·다음과 새 탐색 순서를 계산한다. 버튼 반영은 성공 콜백에 맡긴다.
  updateFavoriteNavigation(items, selectedId, order) {
    const remaining = new Map();
    for (const { item } of this.getEntries(items)) {
      if (item) remaining.set(String(item.id), item);
    }
    // 현재 항목이 저장되어 있으면 최신 저장 순서, 해제되었으면 기존 탐색 순서를 사용한다.
    const nextOrder = remaining.has(selectedId) ? [...remaining.keys()] : [...order];
    const index = nextOrder.indexOf(selectedId);
    // 현재 위치 앞에서 가장 가까운 남은 항목을 찾는다.
    const previousId = index > 0
      ? nextOrder.slice(0, index).reverse().find((id) => remaining.has(id)) : null;
    // 현재 위치 뒤에서 가장 가까운 남은 항목을 찾는다.
    const nextId = index >= 0
      ? nextOrder.slice(index + 1).find((id) => remaining.has(id)) : null;
    return {
      previousItem: remaining.get(previousId) ?? null,
      nextItem: remaining.get(nextId) ?? null,
      order: nextOrder,
    };
  }
}
