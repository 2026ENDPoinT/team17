"""학교 공통 CMS 페이지 파싱. 네트워크를 쓰지 않는 순수 함수만 둔다.

- parse_list(html, board_url) → 목록의 글 [{bidx, bnum, title, posted_date, pinned, url}]
- parse_detail(html, page_url) → {title, posted_date, body_text, has_images, attachments}

목록 레이아웃은 표형(table.tbl_list)과 카드형(div.blog_list) 두 가지다. (docs/research-findings.md 2.7절)
"""

import html
import re
import urllib.parse
from html.parser import HTMLParser

_DATE = re.compile(r"(20\d\d)[-.](\d\d)[-.](\d\d)|\b(\d\d)\.(\d\d)\.(\d\d)\b")
# 상세 글 링크만 고른다. 게시판 탭 링크(?do=list&bidx=...)는 글이 아니다.
_VIEW_HREF = re.compile(r"""href=['"]([^'"]*do=(?:common)?view[^'"]*)['"]""")


def _norm_date(text: str) -> str | None:
    m = _DATE.search(text)
    if not m:
        return None
    if m.group(1):
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return f"20{m.group(4)}-{m.group(5)}-{m.group(6)}"


def _clean_inline(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>|\s+", " ", fragment)).replace("\xa0", " ").strip()


def canonical_url(board_url: str, href: str) -> str:
    """상세 링크에서 do, bnum, bidx만 남긴다. (nowpage, searchtext 같은 군더더기 제거)"""
    full = urllib.parse.urljoin(board_url, html.unescape(href))
    parts = urllib.parse.urlparse(full)
    q = urllib.parse.parse_qs(parts.query)
    keep = [(k, q[k][0]) for k in ("do", "bnum", "bidx") if k in q]
    return urllib.parse.urlunparse(parts._replace(query=urllib.parse.urlencode(keep)))


def _row(block: str, board_url: str, pinned: bool) -> dict | None:
    m = _VIEW_HREF.search(block)
    if not m:
        return None
    url = canonical_url(board_url, m.group(1))
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if "bidx" not in q:
        return None
    a = re.search(r"<a[^>]*do=(?:common)?view[^>]*>(.*?)</a>", block, re.S)
    return {
        "bidx": int(q["bidx"][0]),
        "bnum": int(q["bnum"][0]) if "bnum" in q else None,
        "title": _clean_inline(a.group(1)) if a else "",
        "posted_date": _norm_date(block),
        "pinned": pinned,
        "url": url,
    }


def parse_list(page_html: str, board_url: str) -> list[dict]:
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page_html, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if not tds:
            continue
        number = re.sub(r"<[^>]+>|\s", "", tds[0])
        row = _row(tr, board_url, pinned=not number.isdigit())
        if row:
            rows.append(row)
    if not rows:  # 카드형
        for blk in re.split(r'<div class="list">', page_html)[1:]:
            row = _row(blk, board_url, pinned="ico_notice" in blk)
            if row:
                rows.append(row)
    return rows


_BLOCK_TAGS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "table", "ul", "ol"}


class _ContExtractor(HTMLParser):
    """<td class="cont"> 안의 텍스트와 이미지 수를 모은다. 속성 순서에 상관없이 class로 찾는다."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0  # cont 안에서 열린 td 깊이 (0이면 cont 밖)
        self.skip = 0  # script/style 안
        self.parts: list[str] = []
        self.images = 0
        self.found = False

    def handle_starttag(self, tag, attrs):
        if self.depth == 0:
            if tag == "td" and "cont" in (dict(attrs).get("class") or "").split():
                self.depth = 1
                self.found = True
            return
        if tag == "td":
            self.depth += 1
        if tag in ("script", "style"):
            self.skip += 1
        if tag == "img":
            self.images += 1
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.depth == 0:
            return
        if tag == "td":
            self.depth -= 1
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.parts.append(data)

    def text(self) -> str:
        raw = "".join(self.parts).replace("\xa0", " ")
        lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in raw.split("\n")]
        out: list[str] = []
        for line in lines:
            if line or (out and out[-1]):  # 빈 줄은 하나까지만
                out.append(line)
        return "\n".join(out).strip()


_DOWNLOAD = re.compile(r"downloadfile\(\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*\)")


def parse_detail(page_html: str, page_url: str) -> dict:
    ext = _ContExtractor()
    ext.feed(page_html)
    title = re.search(r"<th[^>]*>\s*제목\s*</th>\s*<td[^>]*>(.*?)</td>", page_html, re.S)
    date = re.search(r"<th[^>]*>\s*날짜\s*</th>\s*<td[^>]*>(.*?)</td>", page_html, re.S)

    attachments = []
    seen = set()
    for path, stored, name in _DOWNLOAD.findall(page_html):
        url = urllib.parse.urljoin(page_url, f"{path.rstrip('/')}/{stored}")
        if url in seen:
            continue
        seen.add(url)
        name = html.unescape(name).strip()
        attachments.append({
            "name": name,
            "ext": name.rsplit(".", 1)[-1].lower() if "." in name else "",
            "url": url,
            "text": None,
            "text_status": "not_extracted",
        })

    return {
        "found_body": ext.found,
        "title": _clean_inline(title.group(1)) if title else None,
        "posted_date": _norm_date(date.group(1)) if date else None,
        "body_text": ext.text(),
        "has_images": ext.images > 0,
        "attachments": attachments,
    }
