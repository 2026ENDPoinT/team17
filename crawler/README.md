# crawler: 교내 게시판 장학금 공지 수집

교내 게시판 목록에서 제목에 장학금 키워드가 있는 글을 골라 상세 페이지를 읽고, 글 1건마다 `data/raw/{bidx}.json` 파일 1개를 만든다.

- 담당: 크롤링 담당 (이 폴더와 `data/raw/`는 크롤링 담당만 고친다)
- 받는 사람: 분류 담당 (`classifier/`가 `data/raw/`를 읽는다)
- 형식의 기준: [`data/raw/_sample.json`](../data/raw/_sample.json). 필드를 바꾸면 샘플과 이 문서를 같이 고치고 팀에 알린다.

## `data/raw/{bidx}.json` 필드

샘플 값은 **지어낸 예시**다. 실제 공지가 아니다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `_sample` | bool | 샘플 파일에만 `true`. 실제 수집 파일에는 없다. 분류 쪽은 이 값이 있는 파일을 건너뛴다 |
| `bidx` | int | 글 번호. 전역 고유이고 파일 이름으로 쓴다 |
| `bnum` | int | 게시판 번호. 첨부 경로(`/storage/{site}/bbs/{bnum}/…`)에 쓰인다. 샘플은 `0` |
| `site` | string | 호스트 앞부분 (`www`, `ice`, `mech` …). `tools/research/boards.txt` 첫 칸과 같다 |
| `board` | string | 게시판 이름 (`장학공지`, `공지사항` …) |
| `url` | string | 원문 상세 주소. 화면의 "원문 보기" 링크로 쓴다 |
| `title` | string | 목록에 보이는 제목 그대로. "(마감)", "연장" 같은 수정도 그대로 둔다 |
| `posted_date` | string | 게시일 `YYYY-MM-DD`. 사이트에 시각이 없어서 날짜만 있다 |
| `pinned` | bool | 목록 상단 고정 공지인지 |
| `matched_keywords` | string[] | 제목에서 걸린 키워드 (`장학`, `근로`, `학자금`, `등록금`) |
| `body_text` | string | 본문(`td.cont`) 텍스트. 줄바꿈 유지, HTML 태그 제거. **이메일·전화번호는 `[연락처]`, 이름·학번 명단은 `[명단 삭제]`로 바꾼 뒤** 저장한다. 본문이 없으면 `""` |
| `has_images` | bool | 본문에 이미지가 있는지. 포스터만 있는 글(본문 `""` + `true`)을 분류 쪽이 "원문 확인 필요"로 넘기는 데 쓴다 |
| `attachments` | object[] | 첨부 목록. 없으면 `[]`. 파일 자체는 저장하지 않는다 |
| `attachments[].name` | string | 화면에 보이는 첨부 이름 |
| `attachments[].ext` | string | 소문자 확장자 (`pdf`, `hwp`, `hwpx` …) |
| `attachments[].url` | string | 원문 첨부 주소 (다시 배포하지 않고 링크만 둔다) |
| `attachments[].text` | string \| null | 첨부에서 뽑은 텍스트 (개인정보 제거 후). 뽑지 않았거나 실패하면 `null` |
| `attachments[].text_status` | string | `ok` / `failed` / `not_extracted` / `unsupported` |
| `content_hash` | string | `sha256:` + `sha256(title + "\n" + body_text)`. 다시 읽었을 때 값이 바뀌면 글이 수정된 것이다 |
| `first_seen` | string | 처음 수집한 시각 (ISO 8601, `+09:00`) |
| `last_checked` | string | 마지막으로 다시 읽은 시각 |

## 정하지 않은 것

- 학과 재게시 중복 묶기(제목 유사도)는 크롤러에서 할지 분류에서 할지 아직 정하지 않았다. 지금은 `bidx`마다 파일 1개만 만든다.
- 첨부 텍스트 추출(HWP·PDF)은 데모 범위 밖이다. 시간이 남으면 `text_status`를 `ok`로 채운다.
