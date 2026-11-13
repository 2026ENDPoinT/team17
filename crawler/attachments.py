"""첨부파일 텍스트 추출. 입력: 첨부 URL과 확장자 / 출력: (text_status, 개인정보를 지운 텍스트 또는 None)

- pdf: pypdf / hwp, hwpx: hwp-hwpx-parser / docx: 표준 라이브러리(zip 안의 XML)
- 파일 원본은 data/raw에 저장하지 않는다. record 모드일 때만 crawler/fixtures/files/에 남는다 (Git 제외).
- 결과 공지(선발 결과, 지급완료, 명단 등)의 첨부는 명단이 들어 있을 수 있어 내려받지 않는다.

text_status 값
  ok               텍스트를 뽑았다
  empty            열었지만 글자가 없다 (스캔한 이미지 PDF 등)
  failed           받거나 읽다가 실패했다
  unsupported      지원하지 않는 형식 (jpg, xlsx, zip …)
  skipped_result   결과 공지라 일부러 뽑지 않았다
  skipped_large    MAX_ATTACHMENT_BYTES보다 커서 받지 않았다
  not_extracted    아직 시도하지 않았다
"""

import io
import re
import tempfile
import zipfile
from pathlib import Path

import fetch
import privacy
from config import MAX_ATTACHMENT_BYTES, MAX_ATTACHMENT_CHARS

SUPPORTED = {"pdf", "hwp", "hwpx", "docx"}

# 제목이 이 모양이면 결과 공지로 보고 첨부를 뽑지 않는다
_RESULT_TITLE = re.compile(r"결과|지급\s*완료|명단|합격자|선발자|선정자|최종\s*선발")


def is_result_notice(title: str) -> bool:
    return bool(_RESULT_TITLE.search(title))


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader

    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)


def _hwp_text(data: bytes, ext: str) -> str:
    from hwp_hwpx_parser import Reader

    # 이 라이브러리는 파일 경로와 확장자로 형식을 판단해서, 잠깐 임시 파일로 쓴다
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"attachment.{ext}"
        path.write_bytes(data)
        with Reader(path) as r:
            return r.text


def _docx_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        xml = z.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)


def _clean(text: str) -> str:
    lines = [re.sub(r"[ \t　\xa0]+", " ", line).strip() for line in text.splitlines()]
    out: list[str] = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()


def extract(url: str, ext: str, mode: str) -> tuple[str, str | None]:
    if ext not in SUPPORTED:
        return "unsupported", None
    try:
        data = fetch.get_bytes(url, mode, MAX_ATTACHMENT_BYTES)
    except fetch.TooLarge:
        return "skipped_large", None
    except fetch.FixtureMissing:
        return "not_extracted", None
    except Exception:
        return "failed", None
    try:
        if ext == "pdf":
            raw = _pdf_text(data)
        elif ext in ("hwp", "hwpx"):
            raw = _hwp_text(data, ext)
        else:
            raw = _docx_text(data)
    except Exception:
        return "failed", None
    text = privacy.scrub(_clean(raw))[:MAX_ATTACHMENT_CHARS]
    return ("ok", text) if text else ("empty", None)
