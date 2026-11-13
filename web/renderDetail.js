// 상세 화면의 전체 틀과 세 영역을 만든다.
// 입력: 화면을 넣을 DOM 요소. 출력: 이후 정보와 이벤트를 연결할 영역별 DOM 요소.

// 왼쪽 정보·왼쪽 이동 버튼·오른쪽 상세 정보 영역을 배치하고 각 영역을 반환한다.
export function renderDetail(container) {
  const layout = document.createElement('main');
  layout.className = 'detail-layout';
  const left = document.createElement('div');
  left.className = 'detail-left';
  const mainInfo = createDetailMainArea();
  const navigation = createDetailNavigationArea();
  const details = createDetailInfoArea();

  left.append(mainInfo, navigation.section);
  layout.append(left, details.section);
  container.replaceChildren(layout);
  return { layout, mainInfo, navigation, details };
}

// 장학금명·금액·마감·핵심 조건·공식 링크를 넣을 왼쪽 위의 빈 영역을 만든다.
function createDetailMainArea() {
  const section = document.createElement('section');
  section.className = 'detail-main-info';
  section.setAttribute('aria-label', '장학금 핵심 정보');
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

// 오른쪽에 지원 자격·준비 사항·주의 사항 메모의 제목과 빈 내용 영역을 만든다.
function createDetailInfoArea() {
  const section = document.createElement('div');
  section.className = 'detail-info';
  const areas = {};
  for (const [key, title] of [
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
  return { section, ...areas };
}
