// 선택한 장학금의 핵심 정보·검수 여부·상세 메모를 표시한다.
// 입력: 화면을 넣을 DOM 요소와 장학금 한 건. 출력: 영역별 DOM 요소.
import { formatAmount, formatDeadline, getMainConditions } from './logic.js';
import { renderNoticesPopup } from './renderNoticesPopup.js';

// 상세와 별 클릭을 연결하고 Manager의 변경 결과를 반영할 함수를 반환한다. 항목이 없으면 목록 이동을 안내한다.
export function renderDetail(container, item, handlers = {}) {
  const layout = document.createElement('main');
  layout.className = 'detail-layout';
  if (!item) {
    const message = document.createElement('section');
    const heading = document.createElement('h1');
    heading.textContent = '장학금을 찾을 수 없습니다.';
    const backButton = document.createElement('button');
    backButton.type = 'button';
    backButton.textContent = '목록으로';
    backButton.disabled = !handlers.onBack;
    if (handlers.onBack) backButton.addEventListener('click', handlers.onBack);
    message.append(heading, backButton);
    layout.append(message);
    container.replaceChildren(layout);
    return { layout, backButton };
  }
  const left = document.createElement('div');
  left.className = 'detail-left';
  const review = document.createElement('p');
  review.className = 'detail-review';
  review.textContent = `검수 여부 : ${item.reviewed === true ? '검수 완료' : item.reviewed === false ? '미검수' : '미확인'}`;
  const header = document.createElement('div');
  header.className = 'detail-header';
  const favoriteButton = document.createElement('button');
  favoriteButton.type = 'button';
  favoriteButton.className = 'scholarship-favorite detail-favorite';
  favoriteButton.setAttribute('aria-pressed', String(handlers.isFavorite === true));
  favoriteButton.setAttribute('aria-label', `${item.name || '장학금'} 즐겨찾기 ${handlers.isFavorite ? '해제' : '저장'}`);
  favoriteButton.title = handlers.isFavorite ? '즐겨찾기 해제' : '즐겨찾기 저장';
  favoriteButton.disabled = !handlers.onToggleFavorite;
  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  icon.setAttribute('viewBox', '0 0 24 24');
  icon.setAttribute('aria-hidden', 'true');
  const star = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  star.setAttribute('d', 'M12 3 14.78 8.63 21 9.54 16.5 13.92 17.56 20.12 12 17.19 6.44 20.12 7.5 13.92 3 9.54 9.22 8.63Z');
  icon.append(star);
  favoriteButton.append(icon);
  // 선택한 장학금을 FavoriteManager의 저장·해제 처리 함수에 전달한다.
  favoriteButton.addEventListener('click', () => handlers.onToggleFavorite?.(item));
  header.append(review, favoriteButton);
  const mainInfo = createDetailMainArea(item);
  const navigation = createDetailNavigationArea(handlers);
  const details = createDetailInfoArea(item);

  left.append(mainInfo, navigation.section);
  layout.append(header, left, details.section);
  container.replaceChildren(layout);
  // Manager의 변경 결과로 별과 이전·다음만 갱신한다. 상세 DOM과 스크롤은 유지한다.
  const updateFavorite = (changedItem, result) => {
    const selected = result.selected;
    favoriteButton.setAttribute('aria-pressed', String(selected));
    favoriteButton.setAttribute('aria-label', `${changedItem.name || '장학금'} 즐겨찾기 ${selected ? '해제' : '저장'}`);
    favoriteButton.title = selected ? '즐겨찾기 해제' : '즐겨찾기 저장';
    if (result.navigation) {
      handlers.previousItem = result.navigation.previousItem;
      handlers.nextItem = result.navigation.nextItem;
      navigation.previousButton.disabled = !handlers.previousItem;
      navigation.nextButton.disabled = !handlers.nextItem;
    }
  };
  return { layout, review, favoriteButton, mainInfo, navigation, details, updateFavorite };
}

// 핵심 정보·원문·줄별 조건을 내부 스크롤에 넣고 공식 공지 팝업을 연결한다.
function createDetailMainArea(item) {
  const section = document.createElement('section');
  section.className = 'detail-main-info';
  section.setAttribute('aria-label', '장학금 핵심 정보');
  const heading = document.createElement('h1');
  heading.textContent = item.name || '장학금명 미확인';
  section.append(heading);

  const amountAndDeadline = document.createElement('div');
  amountAndDeadline.className = 'detail-amount-deadline';
  for (const [label, value, original] of [
    ['금액', formatAmount(item.amount), item.amount?.text],
    ['마감', `${formatDeadline(item.deadline)}${item.closed === true ? ' · 마감됨' : ''}`, item.deadline_text],
  ]) {
    const group = document.createElement('div');
    group.className = 'detail-main-field';
    const title = document.createElement('h2');
    title.textContent = label;
    const text = document.createElement('p');
    text.textContent = value;
    // 브라우저 기본 접기·펼치기를 사용해 별도 이벤트 함수 없이 독립적으로 동작한다.
    const toggle = document.createElement('details');
    toggle.className = 'detail-original';
    const trigger = document.createElement('summary');
    trigger.textContent = '원문 보기';
    const originalText = document.createElement('p');
    originalText.textContent = original || '미확인';
    toggle.append(trigger, originalText);
    group.append(title, text, toggle);
    amountAndDeadline.append(group);
  }
  section.append(amountAndDeadline);

  const conditionTitle = document.createElement('h2');
  conditionTitle.textContent = '핵심 지원 조건';
  const conditions = document.createElement('div');
  conditions.className = 'detail-main-conditions';
  for (const condition of getMainConditions(item.eligibility)) {
    const line = document.createElement('span');
    line.className = 'scholarship-condition';
    line.textContent = condition;
    conditions.append(line);
  }
  section.append(conditionTitle, conditions);

  const noticesButton = document.createElement('button');
  noticesButton.type = 'button';
  noticesButton.className = 'detail-official-link';
  noticesButton.textContent = '공식 공지 보기';
  // 선택한 이벤트의 공지 목록을 전달해 관련 공지 팝업을 연다.
  noticesButton.addEventListener('click', () => renderNoticesPopup(section.closest('.detail-layout'), item.notices ?? []));
  section.append(noticesButton);
  const guidance = document.createElement('p');
  guidance.className = 'detail-guidance';
  guidance.textContent = '신청 전 공식 공지를 확인하세요.';
  section.append(guidance);
  const scrollContent = document.createElement('div');
  scrollContent.className = 'detail-main-scroll';
  scrollContent.append(...section.childNodes);
  section.append(scrollContent);
  return section;
}

// 전달받은 이전·다음 항목과 이벤트를 버튼에 연결하며, 이동할 항목이 없으면 비활성화한다.
function createDetailNavigationArea(handlers) {
  const section = document.createElement('nav');
  section.className = 'detail-navigation';
  section.setAttribute('aria-label', '장학금 화면 이동');
  const previousButton = document.createElement('button');
  previousButton.type = 'button';
  previousButton.textContent = '이전 장학금';
  previousButton.disabled = !handlers.previousItem || !handlers.onOpenDetail;
  // 이전 장학금 선택을 main.js의 주소 변경 함수에 전달한다.
  previousButton.addEventListener('click', () => {
    if (!previousButton.disabled) handlers.onOpenDetail(handlers.previousItem);
  });
  const nextButton = document.createElement('button');
  nextButton.type = 'button';
  nextButton.textContent = '다음 장학금';
  nextButton.disabled = !handlers.nextItem || !handlers.onOpenDetail;
  // 다음 장학금 선택을 main.js의 주소 변경 함수에 전달한다.
  nextButton.addEventListener('click', () => {
    if (!nextButton.disabled) handlers.onOpenDetail(handlers.nextItem);
  });
  const backButton = document.createElement('button');
  backButton.type = 'button';
  backButton.className = 'detail-back-button';
  backButton.textContent = '목록으로';
  backButton.disabled = !handlers.onBack;
  if (handlers.onBack) backButton.addEventListener('click', handlers.onBack);
  section.append(previousButton, nextButton, backButton);
  return { section, previousButton, nextButton, backButton };
}

// 카테고리 배지·강조 요약문과 지원 자격·준비 사항·주의 사항을 오른쪽 메모에 채운다.
function createDetailInfoArea(item) {
  const section = document.createElement('div');
  section.className = 'detail-info';
  const areas = {};
  for (const [key, title] of [
    ['overview', '요약·카테고리'],
    ['eligibility', '지원 자격'],
    ['preparation', '준비 사항'],
    ['cautions', '주의 사항'],
  ]) {
    const note = document.createElement('section');
    note.className = 'detail-note';
    const content = document.createElement('div');
    content.className = 'detail-note-content';
    if (key !== 'overview') {
      const heading = document.createElement('h2');
      heading.textContent = title;
      note.append(heading);
    } else {
      content.classList.add('detail-overview');
    }
    note.append(content);
    section.append(note);
    areas[key] = content;
  }

  for (const [className, value] of [['detail-category', item.category], ['detail-summary', item.summary]]) {
    const text = document.createElement('p');
    text.className = className;
    text.textContent = value || '미확인';
    areas.overview.append(text);
  }

  const eligibility = item.eligibility ?? {};
  const unclear = eligibility.unclear ?? [];
  const labels = {
    grades: '지원 학년', departments: '지원 학과', gpa_min: '최소 평점',
    score_min: '최소 백분위 성적', income_max: '최대 소득분위',
    residence: '거주지', other_conditions: '기타 조건',
    amount: '금액', deadline: '마감', duplicate_restriction: '중복 수혜 제한',
    poster_only: '포스터 정보',
  };
  for (const key of ['grades', 'departments', 'gpa_min', 'score_min', 'income_max', 'residence', 'other_conditions']) {
    const block = document.createElement('p');
    block.className = 'detail-condition';
    const value = eligibility[key];
    let display = '미확인';
    if (value != null && !unclear.includes(key)) {
      if (Array.isArray(value)) {
        if (value.length > 0) display = value.join(', ');
      } else {
        display = String(value).trim() || '미확인';
      }
    }
    block.textContent = `${labels[key]} : ${display}`;
    areas.eligibility.append(block);
  }

  const documentTitle = document.createElement('p');
  documentTitle.textContent = '제출 서류';
  const documentList = document.createElement('ul');
  const documents = item.burden?.documents;
  for (const name of Array.isArray(documents) && documents.length > 0 ? documents : ['미확인']) {
    const entry = document.createElement('li');
    entry.textContent = name;
    documentList.append(entry);
  }
  const interview = document.createElement('p');
  interview.textContent = `면접 여부 : ${item.burden?.interview === true ? '있음' : item.burden?.interview === false ? '없음' : '미확인'}`;
  areas.preparation.append(documentTitle, documentList, interview);

  const restriction = document.createElement('p');
  restriction.textContent = `중복 수혜 제한 : ${item.duplicate_restriction === true ? '있음' : item.duplicate_restriction === false ? '없음' : '미확인'}`;
  areas.cautions.append(restriction);
  const checkFields = new Set([...unclear, ...(item.needs_check ?? [])]);
  for (const key of checkFields) {
    const text = document.createElement('p');
    text.textContent = `${labels[key] ?? key} : 미확인 · 공식 공지 확인 필요`;
    areas.cautions.append(text);
  }
  const guidance = document.createElement('p');
  guidance.textContent = '신청 방법과 최종 지원 조건은 공식 공지를 확인하세요.';
  areas.cautions.append(guidance);
  return { section, ...areas };
}
