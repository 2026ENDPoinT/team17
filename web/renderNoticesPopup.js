// 이벤트의 관련 공지를 카드 목록으로 표시하는 팝업이다.
// 입력: 부모 DOM과 notices 배열. 출력: 열린 dialog 요소.

// 관련 공지를 최신 게시일 순으로 나열하고, 카드에서 공식 페이지를 새 탭으로 연다.
export function renderNoticesPopup(container, notices = []) {
  const dialog = document.createElement('dialog');
  dialog.className = 'filter-popup notices-popup';
  dialog.setAttribute('aria-labelledby', 'notices-popup-title');

  const header = document.createElement('header');
  const title = document.createElement('h2');
  title.id = 'notices-popup-title';
  title.textContent = '관련 공지 보기';
  header.append(title);

  const content = document.createElement('div');
  content.className = 'filter-popup-content notices-popup-content';
  // 원본 배열을 보존하며 최신 게시일 순으로 정렬한다. 같은 날은 최신 공지 번호를 먼저 둔다.
  const sortedNotices = [...notices].sort((a, b) =>
    (b.posted_at ?? '').localeCompare(a.posted_at ?? '') ||
    String(b.bidx ?? '').localeCompare(String(a.bidx ?? ''), 'en', { numeric: true }));
  for (const notice of sortedNotices) {
    const card = document.createElement('a');
    card.className = 'notice-card';
    if (/^https?:\/\//i.test(notice.url ?? '')) {
      card.href = notice.url;
      card.target = '_blank';
      card.rel = 'noopener noreferrer';
    } else {
      card.setAttribute('aria-disabled', 'true');
      card.title = '공식 공지 링크 미확인';
    }
    const name = document.createElement('span');
    name.className = 'notice-card-title';
    name.textContent = notice.title || '공지 제목 미확인';
    const date = document.createElement('span');
    date.className = 'notice-card-date';
    date.textContent = notice.posted_at || '게시일 미확인';
    card.append(name, date);
    content.append(card);
  }
  if (notices.length === 0) {
    const empty = document.createElement('p');
    empty.textContent = '관련 공지가 없습니다.';
    content.append(empty);
  }

  const footer = document.createElement('footer');
  const closeButton = document.createElement('button');
  closeButton.type = 'button';
  closeButton.textContent = '닫기';
  // 닫기 버튼으로 팝업을 닫는다.
  closeButton.addEventListener('click', () => dialog.close());
  footer.append(closeButton);
  dialog.append(header, content, footer);
  // 닫기 버튼이나 Esc로 닫으면 팝업 DOM을 정리한다.
  dialog.addEventListener('close', () => dialog.remove());
  container.append(dialog);
  dialog.showModal();
  return dialog;
}
