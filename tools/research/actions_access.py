"""GitHub Actions 러너(해외 IP)에서 학교 사이트에 접근되는지 한 번 확인한다. 조사용이며 서비스 코드가 아니다.

실행: uv run python tools/research/actions_access.py   (워크플로 .github/workflows/access-test.yml이 돌린다)
입력: crawler/config.py의 BOARDS / 출력: 게시판마다 한 줄 (성공 여부, 목록 글 수, 걸린 시간). 파일은 쓰지 않는다.

요청 수: 게시판 16곳의 목록 1쪽씩 + 상세 1건 + 첨부 1개 = 최대 18번. 크롤러의 fetch를 그대로 써서
User-Agent, 호스트별 1초 간격, 잘린 응답 재시도가 실제 수집과 같다. 제목·본문은 출력하지 않는다.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "crawler"))

import fetch  # noqa: E402
from config import BOARDS  # noqa: E402
from parse import parse_detail, parse_list  # noqa: E402


def timed(func):
    """func()를 실행해 (결과 또는 None, 오류 이름 또는 None, 걸린 초)를 돌려준다."""
    start = time.monotonic()
    try:
        return func(), None, time.monotonic() - start
    except Exception as e:
        return None, f"{e.__class__.__name__}: {e}"[:120], time.monotonic() - start


def main() -> int:
    failed = 0
    first_rows: list[dict] = []
    for board in BOARDS:
        url = f"{board['url']}?page=1"
        rows, error, sec = timed(lambda: parse_list(fetch.get(url, "live"), board["url"]))
        if error or not rows:
            failed += 1
            print(f"실패  {board['site']:<10} 목록  {sec:5.1f}초  {error or '글 0건 (차단 페이지일 수 있음)'}")
        else:
            print(f"성공  {board['site']:<10} 목록  {sec:5.1f}초  글 {len(rows)}건")
            if not first_rows:
                first_rows = rows

    # 상세 1건과 그 글의 첨부 1개 (첨부는 /storage/ 정적 파일이라 경로가 다르다)
    for row in first_rows:
        detail, error, sec = timed(lambda: parse_detail(fetch.get(row["url"], "live"), row["url"]))
        if error or not detail["found_body"]:
            failed += 1
            print(f"실패  상세  {sec:5.1f}초  {error or '본문 위치를 못 찾음'}")
            break
        print(f"성공  상세  {sec:5.1f}초  본문 {len(detail['body_text'])}자, 첨부 {len(detail['attachments'])}개")
        if not detail["attachments"]:
            continue  # 첨부가 있는 글이 나올 때까지 다음 글을 본다 (최대 목록 1쪽)
        att = detail["attachments"][0]
        data, error, sec = timed(lambda: fetch.get_bytes(att["url"], "live", 20_000_000))
        if error:
            failed += 1
            print(f"실패  첨부  {sec:5.1f}초  {error}")
        else:
            print(f"성공  첨부  {sec:5.1f}초  {len(data)}바이트 ({att['ext']})")
        break

    print(f"\n결과: 실패 {failed}건")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
