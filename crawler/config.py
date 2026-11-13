"""크롤러 공통 설정: User-Agent, 요청 간격, 수집 대상 게시판, 제목 키워드.

다른 파일은 값을 여기서만 가져다 쓴다. (AGENTS.md: UA와 요청 간격은 한 곳에서 관리)
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"  # 출력: data/raw/{bidx}.json
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"  # 저장해 둔 HTML (Git에 올리지 않음)

USER_AGENT = "Mozilla/5.0 (team17 scholarship crawler; low-rate)"
REQUEST_INTERVAL = 1.0  # 같은 호스트에 요청 사이 최소 간격(초)
TIMEOUT = 25
RETRIES = 3  # 실패하면 2초, 4초, 8초 쉬고 다시 시도

# 제목에 이 단어가 있으면 장학금 공지로 본다
KEYWORDS = ["장학", "근로", "학자금", "등록금"]

SINCE_DAYS = 60  # 최근 며칠 글까지 모을지 (데모: 최근 1~2개월)
MAX_PAGES = 5  # 게시판마다 목록 몇 쪽까지 읽을지
RECHECK_DAYS = 14  # 이미 받은 글도 이 기간 안이면 다시 읽어 수정 여부를 확인한다

# 수집 대상 게시판. site와 board 이름은 tools/research/boards.txt와 같게 쓴다.
# filter_keywords=False: 게시판 자체가 장학 게시판이라 제목 키워드로 거르지 않는다.
BOARDS = [
    {
        "site": "www",
        "board": "장학공지",
        "url": "https://www.seoultech.ac.kr/service/info/janghak/",
        "filter_keywords": False,
    },
]
