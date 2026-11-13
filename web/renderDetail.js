// 선택한 장학금의 핵심 정보·검수 여부·상세 메모를 표시한다.
// 입력: 화면을 넣을 DOM 요소와 장학금 한 건. 출력: 영역별 DOM 요소.
import { formatAmount, formatDeadline, getMainConditions } from './logic.js';

// 왼쪽 정보·왼쪽 이동 버튼·오른쪽 상세 정보 영역을 배치하고 각 영역을 반환한다.
export function renderDetail(container, item) {
  const layout = document.createElement('main');
  layout.className = 'detail-layout';
  const left = document.createElement('div');
  left.className = 'detail-left';
  const review = document.createElement('p');
  review.className = 'detail-review';
  review.textContent = `검수 여부 : ${item.reviewed === true ? '검수 완료' : item.reviewed === false ? '미검수' : '미확인'}`;
  const mainInfo = createDetailMainArea(item);
  const navigation = createDetailNavigationArea();
  const details = createDetailInfoArea(item);

  left.append(review, mainInfo, navigation.section);
  layout.append(left, details.section);
  container.replaceChildren(layout);
  return { layout, review, mainInfo, navigation, details };
}

// 장학금 핵심 정보를 채우고, 금액·마감의 독립적인 원문 토글과 공식 링크를 만든다.
function createDetailMainArea(item) {
  const section = document.createElement('section');
  section.className = 'detail-main-info';
  section.setAttribute('aria-label', '장학금 핵심 정보');
  const heading = document.createElement('h1');
  heading.textContent = item.name || '장학금명 미확인';
  section.append(heading);

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
    section.append(group);
  }

  const conditionTitle = document.createElement('h2');
  conditionTitle.textContent = '핵심 지원 조건';
  const conditions = document.createElement('p');
  conditions.textContent = getMainConditions(item.eligibility).join(' / ');
  section.append(conditionTitle, conditions);

  if (/^https?:\/\//i.test(item.source?.url ?? '')) {
    const link = document.createElement('a');
    link.className = 'detail-official-link';
    link.textContent = '공식 공지 보기';
    link.href = item.source.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    section.append(link);
  } else {
    const missing = document.createElement('p');
    missing.textContent = '공식 공지 링크 미확인';
    section.append(missing);
  }
  const guidance = document.createElement('p');
  guidance.className = 'detail-guidance';
  guidance.textContent = '신청 전 공식 공지를 확인하세요.';
  section.append(guidance);
  return section;
}

// 이전·다음 장학금과 목록으로 이동할 버튼 영역을 만든다. 이벤트 연결 전에는 비활성화한다.
function createDetailNavigationArea() {
  const section = document.createElement('nav');
  section.className = 'detail-navigation';
  section.setAttribute('aria-label', '장학금 화면 이동');
  const previousButton = document.createElement('button');
  previousButton.type = 'button';
  previousButton.textContent = '이전 장학금';
  previousButton.disabled = true;
  const nextButton = document.createElement('button');
  nextButton.type = 'button';
  nextButton.textContent = '다음 장학금';
  nextButton.disabled = true;
  const backButton = document.createElement('button');
  backButton.type = 'button';
  backButton.className = 'detail-back-button';
  backButton.textContent = '목록으로';
  backButton.disabled = true;
  section.append(previousButton, nextButton, backButton);
  return { section, previousButton, nextButton, backButton };
}

// 요약·카테고리, 전체 지원 자격, 준비 사항과 주의 사항을 오른쪽 메모에 채운다.
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
    const heading = document.createElement('h2');
    heading.textContent = title;
    const content = document.createElement('div');
    content.className = 'detail-note-content';
    note.append(heading, content);
    section.append(note);
    areas[key] = content;
  }

  for (const [label, value] of [['요약', item.summary], ['카테고리', item.category]]) {
    const text = document.createElement('p');
    text.textContent = `${label} : ${value || '미확인'}`;
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
