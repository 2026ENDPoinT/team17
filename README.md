# team17
ENDPoinT 해커톤 2026 Team 17 — **장학금 헌터**

서울과기대 교내 게시판(본부·학과)에 흩어진 장학금 공지를 모아 금액·조건·마감을 비교하고 정렬·필터할 수 있게 해 주는 웹 서비스.

- 서비스 범위와 일정: [docs/scholarship-mvp.md](docs/scholarship-mvp.md)
- 팀·AI 공통 규칙: [AGENTS.md](AGENTS.md)

## 처음 한 번 (개발 환경)

Python 쪽(수집·추출)은 **uv**로 관리한다. 각자 PC에 깔린 Python 버전과 상관없이, uv가 프로젝트에 고정된 **Python 3.11**과 같은 버전의 라이브러리를 맞춰 준다.

1. uv 설치 (한 번만)
   - Windows (PowerShell): `winget install astral-sh.uv`
   - macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - 설치 후 터미널을 다시 열고 `uv --version`으로 확인한다.
2. 저장소 폴더에서 환경 맞추기

   ```bash
   uv sync
   ```

   처음 실행하면 Python 3.11을 받아 `.venv/`를 만들고 라이브러리를 설치한다.

화면(웹)은 **Node.js 24**와 Vite를 쓴다. (설정은 화면 담당이 추가 예정)

## 자주 쓰는 명령

| 하는 일 | 명령 |
|---|---|
| Python 스크립트 실행 | `uv run python <파일>.py` |
| 라이브러리 추가 (팀에 먼저 알리기) | `uv add <이름>` |
| 라이브러리 바뀐 뒤 맞추기 (`git pull` 후) | `uv sync` |
| 코드 검사 (3.11 문법 포함) | `uv run ruff check .` |
| 자동 정리 (import 정렬 등) | `uv run ruff check . --fix` |

- `pip install`은 쓰지 않는다. `uv.lock`과 어긋나서 팀원마다 버전이 달라진다.
- 푸시하면 GitHub Actions가 Python 3.11로 검사한다 (`.github/workflows/python-check.yml`). 빨간 X가 뜨면 바로 고친다.

## 폴더

| 폴더 | 내용 |
|---|---|
| `docs/` | 조사·기획 문서 |
| `tools/research/` | 사전 조사용 실측 스크립트 |
| `crawler/` | 크롤링 담당: 공지 수집 → `data/raw/` |
| `classifier/` | 분류 담당: 분류·추출 → `data/extracted/`, 빌드 → `web/public/scholarships.json` |
| `web/` | 화면 담당: 정렬·필터·비교 화면 |
| `data/reviewed/` | 사람이 검수해 덮어쓴 값 |
