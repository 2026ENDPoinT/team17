// 원본 데이터와 화면 상태를 보관하고 데이터 읽기·정렬·화면 표시를 연결한다.
// 입력: 샘플 JSON과 사용자 조작. 출력: 메인 화면.
import { loadScholarships } from './data.js';
import { sortScholarships, compareDeadline } from './logic.js';
import { renderMain, renderScholarshipList, renderListStatus } from './renderMain.js';

const state = {
  items: [],
  compareFunction: compareDeadline,
  filters: {},
  loading: true,
  error: null,
  selectedId: null,
};
const areas = renderMain(document.getElementById('app'));

// 현재 상태에 따라 로딩·오류 안내 또는 정렬된 장학금 목록을 표시한다.
function updateMain() {
  if (state.loading) return renderListStatus(areas.list, 'loading');
  if (state.error) return renderListStatus(areas.list, 'error');
  const items = sortScholarships(state.items, state.compareFunction);
  renderScholarshipList(areas.list, items, handleOpenDetail);
}

// 선택한 장학금을 기록한다. 상세 화면 전환은 후속 구현에서 연결한다.
function handleOpenDetail(item) {
  state.selectedId = item.id;
}

// 처음 한 번 데이터를 읽어 보관하고, 성공 여부에 맞춰 화면을 갱신한다.
async function initialize() {
  updateMain();
  try {
    state.items = await loadScholarships();
  } catch (error) {
    state.error = error;
  } finally {
    state.loading = false;
    updateMain();
  }
}

initialize();
