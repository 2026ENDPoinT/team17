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
MAX_PAGES = 10  # 게시판마다 목록 몇 쪽까지 읽을지 (본부 대학공지는 60일에 약 9쪽)
RECHECK_DAYS = 14  # 이미 받은 글도 이 기간 안이면 다시 읽어 수정 여부를 확인한다

# 첨부 텍스트 추출
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024  # 이보다 큰 첨부는 받지 않는다
MAX_ATTACHMENT_CHARS = 20000  # 첨부 1개에서 저장할 최대 글자 수

# 취업정보 게시판은 "근로"가 "기간제근로자 채용"에 걸려서 "장학"만 본다
JOB_KEYWORDS = ["장학"]

# 수집 대상 게시판. site와 board 이름은 tools/research/boards.txt와 같게 쓴다.
# filter_keywords=False: 게시판 자체가 장학 게시판이라 제목 키워드로 거르지 않는다.
# keywords: 이 게시판만 다른 키워드를 쓸 때 (없으면 KEYWORDS)
#
# 학과 게시판 고른 기준 (2026-11-13 실측, 최근 60일): 본부 공지를 다시 올린 것이 아니라
# 학과가 직접 올린 장학금 공지가 있었던 학부 게시판만 넣었다. 대학원 공지는 넣지 않는다.
BOARDS = [
    {"site": "www", "board": "장학공지", "url": "https://www.seoultech.ac.kr/service/info/janghak/",
     "filter_keywords": False},
    {"site": "architecture", "board": "장학금",
     "url": "https://architecture.seoultech.ac.kr/bachelor_of_information/scholarship", "filter_keywords": False},
    {"site": "www", "board": "대학공지", "url": "https://www.seoultech.ac.kr/service/info/notice/",
     "filter_keywords": True},
    {"site": "iise", "board": "공지사항", "url": "https://iise.seoultech.ac.kr/notice/faculty_announcements_",
     "filter_keywords": True},
    {"site": "civil", "board": "학부공지", "url": "https://civil.seoultech.ac.kr/haksainfor/notice",
     "filter_keywords": True},
    {"site": "eie", "board": "학부공지", "url": "https://eie.seoultech.ac.kr/majornotice/notice",
     "filter_keywords": True},
    {"site": "dse", "board": "공지사항", "url": "https://dse.seoultech.ac.kr/information/bulletin",
     "filter_keywords": True},
    {"site": "safety", "board": "공지사항", "url": "https://safety.seoultech.ac.kr/b_information/notic",
     "filter_keywords": True},
    {"site": "optometry", "board": "공지사항",
     "url": "https://optometry.seoultech.ac.kr/bachelor_of_information/notice", "filter_keywords": True},
    {"site": "gtm", "board": "GTM소식", "url": "https://gtm.seoultech.ac.kr/info_plaza/gtm_info",
     "filter_keywords": True},
    {"site": "computer", "board": "학부공지", "url": "https://computer.seoultech.ac.kr/info/notice",
     "filter_keywords": True},
    {"site": "biz", "board": "공지사항", "url": "https://biz.seoultech.ac.kr/railway/bizrailwaynotice",
     "filter_keywords": True},
    {"site": "gsklc", "board": "공지사항", "url": "https://gsklc.seoultech.ac.kr/information/bulletin",
     "filter_keywords": True},
    # 기업 연구장학생 모집
    {"site": "eng", "board": "취업정보", "url": "https://eng.seoultech.ac.kr/information_plaza/jobs",
     "filter_keywords": True, "keywords": JOB_KEYWORDS},
    {"site": "car", "board": "취업정보", "url": "https://car.seoultech.ac.kr/bach/info",
     "filter_keywords": True, "keywords": JOB_KEYWORDS},
    {"site": "msde", "board": "취업정보", "url": "https://msde.seoultech.ac.kr/community_/jobs_",
     "filter_keywords": True, "keywords": JOB_KEYWORDS},
]
