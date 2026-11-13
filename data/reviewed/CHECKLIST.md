# 검수 체크리스트

`uv run python classifier/review_list.py`로 다시 만든다. 직접 고치지 않는다 (체크 표시는 검수 파일이 생기면 목록에서 빠진다).

**검수 방법**

1. 원문 링크를 열어 포스터·첨부를 확인한다.
2. 아래 JSON 뼈대를 `data/reviewed/{bidx}.json`으로 저장하고, **확인한 값만 남긴다.** 모르는 값은 줄째 지운다.
3. `"needs_check": []`를 꼭 남긴다. 남아 있으면 화면이 그 장학금을 필터에서 뺀다.
4. 장학금 모집이 아니면 내용 대신 `{"exclude": true}`만 적는다.
5. `uv run python events/build.py`로 화면용 파일을 다시 만든다.

금액 유형: `lump_sum`(원) / `tuition_ratio`(등록금 %) / `hourly`(시급 원). 같은 유형끼리만 금액순으로 비교된다.

대상 0건 (완료되지 않은 이벤트 중 확인 필요가 있고 아직 검수하지 않은 것)
