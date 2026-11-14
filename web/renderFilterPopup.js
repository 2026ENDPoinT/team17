// 적용 전 필터를 별도 상태로 편집하는 팝업이다.
// 입력: 부모 DOM·적용된 필터·적용 이벤트. 출력: 열린 dialog 요소.
import { FILTER_OPTIONS, DEPARTMENT_GROUPS } from './filterOptions.js';

// 학과를 단과대학 제목 아래 묶어 복수 선택하게 하고, 적용할 때만 임시 필터를 전달한다.
export function renderFilterPopup(container, filters, handlers) {
  const draft = structuredClone(filters);
  const dialog = document.createElement('dialog');
  dialog.className = 'filter-popup';
  dialog.setAttribute('aria-labelledby', 'filter-popup-title');

  const header = document.createElement('header');
  const title = document.createElement('h2');
  title.id = 'filter-popup-title';
  title.textContent = '필터 선택';
  header.append(title);

  const content = document.createElement('div');
  content.className = 'filter-popup-content';
  const optionButtons = [];
  for (const [key, label, values] of [
    ['categories', '유형 · 여러 개 선택', FILTER_OPTIONS.categories],
    ['grades', '학년 · 여러 개 선택', FILTER_OPTIONS.grades],
    ['departments', '학과·학부·전공 · 여러 개 선택', FILTER_OPTIONS.departments],
    ['openOnly', '모집 상태', [true]],
  ]) {
    const group = document.createElement('fieldset');
    const legend = document.createElement('legend');
    legend.textContent = label;
    const options = document.createElement('div');
    options.className = `filter-popup-options filter-popup-options-${key}`;
    for (const value of values) {
      if (key === 'departments') {
        // 각 단과대학의 첫 학과 앞에 선택할 수 없는 제목을 붙인다.
        const college = DEPARTMENT_GROUPS.find((entry) => entry.departments[0] === value);
        if (college) {
          const heading = document.createElement('h3');
          heading.className = 'filter-college-heading';
          heading.textContent = college.college;
          options.append(heading);
        }
      }
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'filter-option';
      button.textContent = key === 'grades' ? `${value}학년` : key === 'openOnly' ? '모집 중만 보기' : value;
      const selected = Array.isArray(draft[key]) ? draft[key].includes(value) : draft[key] === value;
      button.setAttribute('aria-pressed', String(selected));
      optionButtons.push({ button, key, value });
      // 임시 선택만 변경하고 같은 그룹의 선택 표시를 갱신한다. 메인에는 아직 전달하지 않는다.
      button.addEventListener('click', () => {
        if (Array.isArray(draft[key])) {
          const index = draft[key].indexOf(value);
          if (index < 0) draft[key].push(value);
          else draft[key].splice(index, 1);
        } else {
          draft.openOnly = !draft.openOnly;
        }
        for (const option of optionButtons) {
          if (option.key !== key) continue;
          const active = Array.isArray(draft[key]) ? draft[key].includes(option.value) : draft[key] === option.value;
          option.button.setAttribute('aria-pressed', String(active));
        }
      });
      options.append(button);
    }
    group.append(legend, options);
    content.append(group);
  }
  const guidance = document.createElement('p');
  guidance.textContent = '학과 제한 없음은 학과 값이 비어 있는 항목을 표시하며, 학과 정보 미확인 항목도 포함될 수 있습니다. 그 외 선택한 조건이 미확인인 장학금은 제외됩니다. 정확한 마감 시각은 공식 공지를 확인하세요.';
  content.append(guidance);

  const footer = document.createElement('footer');
  const resetButton = document.createElement('button');
  resetButton.type = 'button';
  resetButton.textContent = '초기화';
  // 팝업의 임시 상태와 선택 표시만 초기화한다. 적용 전 메인 상태는 유지한다.
  resetButton.addEventListener('click', () => {
    draft.categories = [];
    draft.grades = [];
    draft.departments = [];
    draft.openOnly = false;
    for (const { button } of optionButtons) button.setAttribute('aria-pressed', 'false');
  });
  const cancelButton = document.createElement('button');
  cancelButton.type = 'button';
  cancelButton.textContent = '취소';
  // 임시 상태를 전달하지 않고 팝업을 닫아 편집 내용을 버린다.
  cancelButton.addEventListener('click', () => dialog.close());
  const applyButton = document.createElement('button');
  applyButton.type = 'button';
  applyButton.className = 'filter-popup-apply';
  applyButton.textContent = '적용';
  // 적용 이벤트에 독립된 상태를 전달하고 팝업을 닫는다.
  applyButton.addEventListener('click', () => {
    handlers.onApply(structuredClone(draft));
    dialog.close();
  });
  footer.append(resetButton, cancelButton, applyButton);
  dialog.append(header, content, footer);
  // 취소 버튼이나 브라우저 기본 Esc 동작으로 닫히면 DOM과 임시 상태를 정리한다.
  dialog.addEventListener('close', () => dialog.remove());
  container.append(dialog);
  dialog.showModal();
  return dialog;
}
