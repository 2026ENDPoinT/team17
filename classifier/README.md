# classifier: 장학금 공지 분류·추출

크롤러가 만든 `data/raw/{bidx}.json`을 읽어 모집 공지인지 가리고, 금액·마감·조건·서류를 뽑아 `data/extracted/{bidx}.json`에 쓴다.
빌드하면 사람 검수값(`data/reviewed/`)을 덮어써서 화면용 `web/public/scholarships.json`을 만든다.

- 담당: 분류 담당 (이 폴더와 `data/extracted/`는 분류 담당만 고친다)
- 입력 형식: [`data/raw/_sample.json`](../data/raw/_sample.json), 설명은 [`crawler/README.md`](../crawler/README.md)
- 출력 형식: [`data/scholarships.sample.json`](../data/scholarships.sample.json). 필드를 바꾸면 샘플과 이 문서를 같이 고치고 화면 담당에게 알린다.

## 실행

저장소 루트에서 실행한다. 표준 라이브러리만 쓰고, 네트워크·LLM은 쓰지 않는다.

```bash
uv run python classifier/extract.py   # data/raw → data/extracted
uv run python classifier/build.py     # data/extracted + data/reviewed → web/public/scholarships.json
```

| 파일 | 역할 |
|---|---|
| `config.py` | 경로, 분류 규칙에 쓰는 키워드 목록 (규칙을 고칠 때 먼저 여기를 본다) |
| `rules.py` | 제목·본문 → 값 + 근거 문장. 순수 함수만 있다 |
| `extract.py` | raw 1건 → extracted 1건 저장 |
| `build.py` | extracted + reviewed 합치기, '모집'만 남겨 scholarships.json 저장 |

## 처리 순서

1. **공지 종류** (제목만 본다): 결과 단어("지급완료", "심사 결과"…) → `결과`, 안내 단어("서약서", "박람회"…) → `안내`, 모집 단어 + 장학 단어 → `모집`, 나머지 → `확인필요`. **빌드에는 `모집`만 들어간다.**
2. **유형**: 근로장학 게시판(`bnum=57138`)이거나 제목에 "근로" → `근로`, "(홍보)"·"재단"·"장학회" → `교외`, 나머지 → `교내`.
3. **금액**: 금액 단어가 있는 줄에서 등록금 비율 → 시급 → 만원 → 원 순서로 찾는다. 소득 기준 줄은 건너뛴다.
4. **마감일**: 제목의 `~11/12`을 먼저 보고(연장되면 제목이 바뀌므로), 없으면 본문의 "신청기간", "까지" 줄에서 마지막 날짜를 쓴다. 발표·면접·근무기간 줄은 건너뛴다.
5. **조건**: 학년, 최소 평점, 소득 구간 상한. 거주지·소득 언급만 있고 값을 못 뽑으면 `eligibility.unclear`에 넣는다.
6. **준비 부담**: "제출서류" 다음 목록 중 서류 이름처럼 보이는 것만 남긴다. 본문에 "면접"이 있으면 면접 있음.
7. **근거 문장**: 금액·마감·중복 제한은 값을 뽑은 원문 줄을 `evidence`에 남긴다. 규칙은 원문에 있는 글자만 뽑으므로 숫자를 지어내지 않는다.

못 찾은 값은 `null`로 두고 `needs_check`에 이름을 넣는다. 그 값은 검수에서 채운다.

## 추출 결과 필드 (`data/extracted/{bidx}.json`)

`data/scholarships.sample.json`의 항목 하나와 같고, 아래 필드가 더 있다. 아래 필드는 빌드할 때 빠진다.

| 필드 | 설명 |
|---|---|
| `notice_kind` | `모집` / `결과` / `안내` / `확인필요` |
| `notice_kind_reason` | 그렇게 판단한 이유 (예: "제목에 '지급완료'") |
| `content_hash` | 원본의 해시. 원본이 바뀌었는지 비교할 때 쓴다 |

화면까지 가는 필드 중 샘플에 새로 넣은 것:

| 필드 | 설명 |
|---|---|
| `closed` | 제목에 "(마감)", "선발완료" 등이 있으면 `true`. 마감일을 모르는 공지도 모집이 끝났는지 알 수 있다 |
| `needs_check` | 사람이 확인해야 하는 항목: `amount`, `deadline`, `documents`, `poster_only`(본문 없이 포스터만), `body_short`(본문 100자 미만) |

## 검수 (`data/reviewed/{bidx}.json`)

틀린 값만 적는다. 안쪽 필드는 그 필드만 덮어쓴다.

```json
{
  "_comment": "포스터 보고 입력",
  "amount": { "type": "lump_sum", "value": 3000000, "text": "300만원" },
  "deadline": "2026-11-20"
}
```

- 모집이 아닌데 `모집`으로 분류됐으면 `{"exclude": true}`
- 모집인데 다른 종류로 분류됐으면 `{"notice_kind": "모집"}`
- 검수 파일이 있는 항목은 빌드 결과에 `reviewed: true`가 붙는다.

## 첫 실행 결과 (본부 장학공지 37건, 2026-11-13)

- 모집 27, 결과 3, 안내 5, 확인필요 2 (시험지원인력 모집, KRA 아동돌봄. 장학금인지 사람이 판단)
- 모집 27건 중 금액을 뽑은 것 8건, 마감일을 뽑은 것 18건. 나머지 대부분은 본문이 거의 없는 교외 "(홍보)" 공지라, 포스터나 첨부를 보고 검수에서 채워야 한다.
- 알려진 한계: 본문 문장이 특이하면 학년을 잘못 읽을 수 있다(예: 896900 가족장학금이 `[1]`). 학과(`departments`)는 아직 뽑지 않는다.

## 다음 할 일

- 학과 재게시 중복 묶기 (크롤러와 분류 중 어디서 할지 정해야 함)
- LLM 보조 추출 (API 키, 라이브러리를 팀이 정한 뒤). LLM 값은 `evidence`가 원문에 실제로 있는지 코드로 확인하고 통과한 것만 쓴다.
