"""수집 → 추출 → 이벤트 빌드를 순서대로 돌린다. 입력: 명령(refresh / rebuild) / 출력: web/public/events.json

사용법 (저장소 루트에서)
  uv run python tools/pipeline.py refresh    # 새 공지 받기: 수집(live) → 추출 → 이벤트 빌드
  uv run python tools/pipeline.py rebuild    # 다시 만들기: 추출 → 이벤트 빌드 (학교 서버 요청 없음)

언제 무엇을 쓰나
  refresh: 학교 게시판에 새 글이 올라왔거나 기존 글이 수정됐을 때
  rebuild: 분류 규칙(classifier/), 묶기 규칙(events/), 검수 파일(data/reviewed/)을 고쳤을 때
  날짜만 지났을 때는 돌릴 필요 없다. 마감 여부와 D-day는 화면이 접속 시점의 날짜로 계산한다.

옵션: refresh --mode offline 은 저장된 HTML(crawler/fixtures/)로 수집 단계를 돌린다 (재게시 규칙을 고쳤을 때, 시험할 때).

각 단계는 따로 실행되는 스크립트다. 폴더마다 config.py가 있어서 한 프로세스에서 import하지 않고 하나씩 실행한다.
수집이 실패로 끝나면 멈춘다. 이미 저장된 데이터로 화면 파일만 만들려면 rebuild를 돌린다.
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

EXTRACT = ["classifier/extract.py"]
BUILD = ["events/build.py"]


def run_step(name: str, script: list[str]) -> int:
    """단계 하나를 지금 쓰는 Python(uv run의 3.11)으로 실행하고 종료 코드를 돌려준다."""
    print(f"\n=== {name}: {' '.join(script)} ===", flush=True)
    return subprocess.run([sys.executable, *script], cwd=ROOT).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="수집 → 추출 → 이벤트 빌드를 순서대로 실행")
    sub = parser.add_subparsers(dest="command", required=True)
    refresh = sub.add_parser("refresh", help="수집 → 추출 → 이벤트 빌드")
    refresh.add_argument("--mode", choices=["live", "offline"], default="live", help="수집 방식 (기본 live)")
    sub.add_parser("rebuild", help="추출 → 이벤트 빌드 (학교 서버 요청 없음)")
    args = parser.parse_args()

    steps = [("추출", EXTRACT), ("이벤트 빌드", BUILD)]
    if args.command == "refresh":
        steps.insert(0, ("수집", ["crawler/crawl.py", "--mode", args.mode]))

    for name, script in steps:
        code = run_step(name, script)
        if code != 0:
            print(f"\n중단: '{name}' 단계가 실패했다 (종료 코드 {code}). 뒤 단계는 돌리지 않았다.", file=sys.stderr)
            if name == "수집":
                print("일부 글만 실패했다면 저장된 데이터는 정상이다. 위 출력을 확인하고 "
                      "'uv run python tools/pipeline.py rebuild'로 이어서 만들 수 있다.", file=sys.stderr)
            return code

    print("\n완료: web/public/events.json 을 만들었다. 'git diff --stat'으로 바뀐 내용을 확인하고 커밋한다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
