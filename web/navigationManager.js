// 주소와 현재 위치를 관리하고 화면 종료 → 위치 갱신 → 화면 진입 순서를 연결한다.
// 입력: 화면별 진입·종료 함수와 이동 요청. 출력: 주소 변경과 해당 화면 함수 호출.
export class NavigationManager {
  #screens;
  #current = null;
  #started = false;

  // 화면별 처리 함수를 보관한다. 데이터 로딩이 끝나 start()를 호출하기 전에는 전환하지 않는다.
  constructor(screens) {
    this.#screens = screens;
  }

  // 현재 위치를 제공한다. 위치 객체는 읽기 전용이며 이 Manager 안에서만 교체한다.
  get current() {
    return this.#current;
  }

  // 최초 주소를 처리하고 이후 버튼 이동·브라우저 뒤로/앞으로를 같은 이벤트로 받는다.
  start() {
    if (this.#started) return;
    this.#started = true;
    window.addEventListener('hashchange', this.#handleRouteChange);
    this.#handleRouteChange();
  }

  // 메인 이동을 요청한다. 실제 전환은 주소 변경 이벤트가 실행한다.
  openMain() {
    window.location.hash = '/';
  }

  // 즐겨찾기 목록 이동을 요청한다. 실제 전환은 주소 변경 이벤트가 실행한다.
  openFavorites() {
    window.location.hash = '/favorites';
  }

  // 현재 목록 출처를 유지한 상세 주소로 이동한다. 상세 사이 이동도 방문 기록에 남긴다.
  openDetail(id) {
    const source = this.#current?.view === 'favorites' ||
      (this.#current?.view === 'detail' && this.#current.detailSource === 'favorites')
      ? '/favorites' : '';
    window.location.hash = `${source}/scholarships/${encodeURIComponent(id)}`;
  }

  // 상세에서는 출처 목록으로, 즐겨찾기 목록에서는 메인으로 이동한다.
  backToList() {
    if (this.#current?.view === 'detail' && this.#current.detailSource === 'favorites') {
      this.openFavorites();
    } else {
      this.openMain();
    }
  }

  // 주소에서 화면·선택 ID·상세 출처만 해석한다. 잘못된 주소는 항목 없는 상세로 전달한다.
  #parseRoute(hash) {
    if (hash === '' || hash === '#' || hash === '#/') {
      return { view: 'main', selectedId: null, detailSource: 'main' };
    }
    if (hash === '#/favorites') {
      return { view: 'favorites', selectedId: null, detailSource: 'favorites' };
    }
    const match = hash.match(/^#\/(favorites\/)?scholarships\/([^/]+)$/);
    let selectedId = null;
    try {
      if (match) selectedId = decodeURIComponent(match[2]);
    } catch {
      // 잘못 인코딩된 ID도 화면의 기존 장학금 없음 안내로 처리한다.
    }
    return { view: 'detail', selectedId, detailSource: match?.[1] ? 'favorites' : 'main' };
  }

  // 같은 위치는 유지하고, 이동할 때 현재 화면 종료 후 위치를 교체해 목표 화면에 진입한다.
  #handleRouteChange = () => {
    const target = this.#parseRoute(window.location.hash);
    const current = this.#current;
    if (current && current.view === target.view && current.selectedId === target.selectedId &&
        current.detailSource === target.detailSource) return;
    if (current) this.#screens[current.view].leave?.(current);
    this.#current = Object.freeze(target);
    this.#screens[target.view].enter(this.#current);
  };
}
