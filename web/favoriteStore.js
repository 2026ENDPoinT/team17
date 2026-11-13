// 즐겨찾기를 브라우저에 저장하고 복원한다.
// 입력: 장학금 ID 배열. 출력: 복원한 ID 배열 또는 저장 성공 여부.
const STORAGE_KEY = 'scholarship-hunter:favorite-ids';

// 시작할 때 저장한 ID를 읽는다. 손상되거나 저장소가 차단되었으면 빈 목록을 반환한다.
export function loadFavorites() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (!Array.isArray(saved)) return [];
    // 유효한 ID만 문자열로 통일하고 중복을 제거한다.
    return [...new Set(saved.filter((id) =>
      (typeof id === 'string' && id.length > 0) || Number.isFinite(id)).map(String))];
  } catch {
    return [];
  }
}

// 버튼 조작 직후 저장한다. 실패하면 호출자가 안내할 수 있도록 false를 반환한다.
export function saveFavorites(ids) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
    return true;
  } catch {
    return false;
  }
}
