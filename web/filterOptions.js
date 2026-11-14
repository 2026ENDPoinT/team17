// 필터와 금액 유형 선택지를 정의한다. 학과 출처는 docs/notice-sources.md 2절이다.
// 출력: 화면 표시와 저장 상태 검증에서 공유하는 선택지. 학교 서버에는 요청하지 않는다.
export const AMOUNT_TYPES = {
  lump_sum: '일시금',
  tuition_ratio: '등록금 비율',
  hourly: '시급',
};

// 단과대학은 제목으로만 표시한다. 소속 학과는 가로 가나다순이다.
export const DEPARTMENT_GROUPS = [
  { college: '공과대학', departments: [
    '건설시스템공학과', '건축공학전공', '건축기계설비공학과', '건축학부', '건축학전공', '기계·자동차공학과', '기계공학과', '기계시스템공학부', '기계시스템디자인공학과', '미래자동차전공', '신소재공학과', '안전공학과', '지능형로봇전공'
  ] },
  { college: '정보통신대학', departments: [
    '스마트ICT융합공학과', '전기정보공학과', '전자공학과', '컴퓨터공학과'
  ] },
  { college: '에너지바이오대학', departments: [
    '바이오메디컬학과', '스포츠과학과', '식품생명공학과', '안경광학과', '양자융합물리학과', '정밀화학과', '화공생명공학과', '환경공학과'
  ] },
  { college: '조형대학', departments: [
    '금속공예디자인학과', '도예학과', '디자인학과', '산업디자인전공', '시각디자인전공', '조형예술학과'
  ] },
  { college: '인문사회대학', departments: [
    '문예창작학과', '영어영문학과', '행정학과'
  ] },
  { college: '기술경영융합대학', departments: [
    '경영학과', '경영학전공', '글로벌테크노경영전공', '산업공학과', '산업정보시스템전공', 'ITM전공', 'MSDE학과'
  ] },
  { college: '미래융합대학', departments: [
    '건설환경융합공학과', '문화예술학과', '벤처경영학과', '영어과', '융합기계공학과', '정보통신융합공학과', '헬스피트니스학과'
  ] },
  { college: '창의융합대학', departments: [
    '미래에너지융합학과', '인공지능응용학과', '지능형반도체공학과'
  ] },
  { college: '교양대학', departments: [
    'ST자유전공'
  ] },
  { college: '국제대학', departments: [
    '글로벌한국어문화학과', '글로벌IT컨버전스학과', 'AI·미디어학과'
  ] },
];

export const FILTER_OPTIONS = {
  categories: ['교내', '교외', '근로'],
  grades: [1, 2, 3, 4],
  departments: [
    '학과 제한 없음',
    // 단과대학 순서대로 소속 학과를 한 배열에 모은다.
    ...DEPARTMENT_GROUPS.flatMap((group) => group.departments),
  ],
};
