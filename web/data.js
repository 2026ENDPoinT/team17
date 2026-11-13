// 개발용 샘플 JSON을 읽는다. 입력: JSON 주소. 출력: 원본 장학금 배열.

// 파일을 불러온 뒤 화면에서 사용할 items 배열이 있는지 확인해 반환한다.
export async function loadScholarships(url = new URL('./samples/scholarships.sample.json', import.meta.url)) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`데이터 요청 실패: ${response.status}`);
  const data = await response.json();
  if (!Array.isArray(data.items)) throw new Error('장학금 목록 형식이 올바르지 않습니다.');
  return data.items;
}
