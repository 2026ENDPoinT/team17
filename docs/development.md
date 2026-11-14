# 개발 환경과 명령

> 저장소를 받아 직접 실행하거나 고치려는 사람을 위한 문서다. (2026-11-14, README에 있던 개발용 내용을 옮김)
> 서비스 소개는 [README](../README.md), 팀·AI 공통 규칙과 폴더 구조는 [AGENTS.md](../AGENTS.md), 서비스 범위는 [scholarship-mvp.md](scholarship-mvp.md)에 있다.

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

## 화면 열기

화면(`web/`)은 순수 JavaScript 모듈이라 빌드 없이 열 수 있다. 다만 `index.html`을 더블 클릭해 열면 브라우저가 JSON 요청을 막으므로, 저장소 루트에서 정적 서버를 띄운다.

```bash
uv run python -m http.server 8000 --directory web
```

브라우저에서 <http://localhost:8000>을 연다. 화면은 `web/public/events.json`을 읽는다.

- Vite 설정(`package.json`)은 아직 저장소에 없다. 화면 담당이 추가하면 이 절을 `npm` 명령으로 바꾼다. Node.js는 **24**를 쓴다.

## 자주 쓰는 명령

| 하는 일 | 명령 |
|---|---|
| Python 스크립트 실행 | `uv run python <파일>.py` |
| 라이브러리 추가 (팀에 먼저 알리기) | `uv add <이름>` |
| 라이브러리 바뀐 뒤 맞추기 (`git pull` 후) | `uv sync` |
| 코드 검사 (3.11 문법 포함) | `uv run ruff check .` |
| 자동 정리 (import 정렬 등) | `uv run ruff check . --fix` |
| 새 공지 받기 (수집 → 추출 → 이벤트 빌드) | `uv run python tools/pipeline.py refresh` |
| 규칙·검수를 고친 뒤 다시 만들기 (추출 → 이벤트 빌드) | `uv run python tools/pipeline.py rebuild` |

- `pip install`은 쓰지 않는다. `uv.lock`과 어긋나서 팀원마다 버전이 달라진다.
- 푸시하면 GitHub Actions가 Python 3.11로 검사한다 (`.github/workflows/python-check.yml`). 빨간 X가 뜨면 바로 고친다.
- `refresh`는 학교 서버에 실제로 요청한다. 규칙만 고쳤을 때는 `rebuild`를 쓴다. 두 명령의 차이는 `tools/pipeline.py` 맨 위에 적혀 있다.
- GitHub에서 수집을 돌리려면 Actions 화면에서 `collect.yml`을 수동 실행한다. 봇이 `main`에 데이터 커밋을 올리므로 푸시 전에 `git pull --rebase`를 한다.

## 폴더

| 폴더 | 내용 |
|---|---|
| `docs/` | 조사·기획 문서 |
| `tools/research/` | 사전 조사용 실측 스크립트 |
| `tools/pipeline.py` | 수집 → 추출 → 이벤트 빌드를 순서대로 실행 |
| `crawler/` | 크롤링 담당: 공지 수집 → `data/raw/` |
| `classifier/` | 분류 담당: 분류·추출 → `data/extracted/` |
| `events/` | 이벤트 묶기: 같은 장학금의 공지를 묶어 화면용 `web/public/events.json`을 만듦 |
| `web/` | 화면 담당: 정렬·필터·상세 화면 |
| `data/reviewed/` | 사람이 검수해 덮어쓴 값 |

폴더별 담당과 주고받는 파일 형식의 기준은 [AGENTS.md](../AGENTS.md) "폴더 구조" 절이다. 이 표와 다르면 AGENTS.md가 맞다.
