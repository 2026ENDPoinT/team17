"""HTML 가져오기. 입력: URL / 출력: HTML 문자열.

모드 3가지 (crawl.py의 --mode로 고른다)
- live:    학교 서버에 요청한다. 같은 호스트는 REQUEST_INTERVAL초 간격, 실패하면 간격을 늘려 재시도.
- record:  live와 같지만 받은 HTML을 crawler/fixtures/에 저장한다.
- offline: 학교 서버에 요청하지 않고 crawler/fixtures/에 저장된 HTML만 읽는다. (개발·테스트용)
"""

import hashlib
import json
import ssl
import time
import urllib.parse
import urllib.request

from config import FIXTURE_DIR, REQUEST_INTERVAL, RETRIES, TIMEOUT, USER_AGENT

_ssl = ssl.create_default_context()
_last_request: dict[str, float] = {}  # 호스트별 마지막 요청 시각


class FixtureMissing(Exception):
    pass


def _fixture_path(url: str):
    return FIXTURE_DIR / (hashlib.sha1(url.encode("utf-8")).hexdigest()[:16] + ".html")


def _wait_for(host: str):
    last = _last_request.get(host)
    if last is not None:
        gap = time.monotonic() - last
        if gap < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - gap)
    _last_request[host] = time.monotonic()


class TooLarge(Exception):
    pass


def _download_bytes(url: str, max_bytes: int | None = None) -> bytes:
    host = urllib.parse.urlparse(url).netloc
    delay = 2.0
    for attempt in range(RETRIES + 1):
        _wait_for(host)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ssl) as r:
                if max_bytes is None:
                    return r.read()
                data = r.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise TooLarge(url)
                return data
        except TooLarge:
            raise
        except Exception:
            if attempt == RETRIES:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")


def _download(url: str) -> str:
    return _download_bytes(url).decode("utf-8", "replace")


def get_bytes(url: str, mode: str, max_bytes: int) -> bytes:
    """첨부파일용. record 모드면 crawler/fixtures/files/에 저장한다. (첨부 원본은 Git에 올리지 않는다)"""
    path = FIXTURE_DIR / "files" / (hashlib.sha1(url.encode("utf-8")).hexdigest()[:16] + ".bin")
    if mode == "offline":
        if not path.exists():
            raise FixtureMissing(url)
        return path.read_bytes()
    data = _download_bytes(url, max_bytes)
    if mode == "record":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return data


def _save_fixture(url: str, text: str):
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    # newline="": 줄바꿈을 받은 그대로 저장한다. (Windows에서 \n이 \r\n으로 바뀌면 offline 결과가 live와 달라진다)
    with open(_fixture_path(url), "w", encoding="utf-8", newline="") as f:
        f.write(text)
    index_path = FIXTURE_DIR / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    index[_fixture_path(url).name] = url
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


def get(url: str, mode: str) -> str:
    if mode == "offline":
        path = _fixture_path(url)
        if not path.exists():
            raise FixtureMissing(url)
        with open(path, encoding="utf-8", newline="") as f:
            return f.read()
    text = _download(url)
    if mode == "record":
        _save_fixture(url, text)
    return text
