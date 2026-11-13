"""volume.py 결과에서 글을 표본 추출해 본문을 분석한다: 본문 길이, 이미지, 첨부, 개인정보 패턴, 마감일 패턴.

사용법: python views.py out/volume.json out/views.json
호스트당 최대 6건을 무작위로 고르고(시드 17), 요청 간격은 1초다.
"""
import html
import json
import random
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

ctx = ssl.create_default_context()
UA = 'Mozilla/5.0 (team17 notice research; low-rate)'
random.seed(17)

def get(u):
    req = urllib.request.Request(u, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        return r.read().decode('utf-8', 'replace')

def analyze(u):
    try:
        h = get(u)
    except Exception as e:
        return dict(url=u, err=str(e)[:60])
    m = re.search(r'<td[^>]*class="cont"[^>]*>(.*?)</td>\s*</tr>', h, re.S)
    body = m.group(1) if m else ''
    files = re.findall(r"downloadfile\('[^']*',\s*'[^']*',\s*'([^']*)'", h)
    text = html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<(script|style)[^>]*>.*?</\1>', '', body, flags=re.S)))
    text = re.sub(r'\s+', ' ', text).strip()
    imgs = len(re.findall(r'<img', body))
    links = re.findall(r'href="(https?://[^"]+)"', body)
    return dict(url=u, found=bool(m), textlen=len(text), imgs=imgs,
                files=[f.rsplit('.', 1)[-1].lower() for f in files if '.' in f],
                email=bool(re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', text)),
                phone=bool(re.search(r'0\d{1,2}[-) ]\d{3,4}-\d{4}', text)),
                stuid=bool(re.search(r'\b(19|20)\d{6}\b|\d{2}\*{2,}\d+|[가-힣]\*[가-힣]', text)),
                forms=sum(1 for link in links if re.search(r'forms\.gle|docs\.google\.com/forms|naver\.me|form\.office|survey', link)),
                deadline=bool(re.search(r'(까지|마감|기한|~\s*\d{1,2}[./]\d{1,2}|신청\s*기간|접수\s*기간)', text)),
                sample=text[:80])

data = json.load(open(sys.argv[1], encoding='utf-8'))
byhost = defaultdict(list)
for b in data:
    for r in b['recent']:
        if r.get('view') and not r['pinned']:
            byhost[urllib.parse.urlparse(r['view']).netloc].append((b['site'], b['label'], r['view']))
pool = []
for host, items in byhost.items():
    random.shuffle(items)
    pool.extend(items[:6])          # 호스트당 최대 6건 → 학과 편중 방지

def job(items):
    out = []
    for site, label, u in items:
        r = analyze(u)
        r['site'] = site
        r['label'] = label
        out.append(r)
        time.sleep(1)
    return out

groups = defaultdict(list)
for it in pool:
    groups[urllib.parse.urlparse(it[2]).netloc].append(it)
res = []
with ThreadPoolExecutor(6) as ex:
    for o in ex.map(job, groups.values()):
        res.extend(o)
json.dump(res, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

ok = [r for r in res if r.get('found')]
n = len(ok)
print('sampled', len(res), 'parsed', n, 'errors', sum(1 for r in res if r.get('err')))
def pct(k):
    return f"{sum(1 for r in ok if k(r))}/{n} ({100*sum(1 for r in ok if k(r))//max(n,1)}%)"
print('본문 100자 미만', pct(lambda r: r['textlen'] < 100))
print('본문 100자 미만 + 첨부 있음', pct(lambda r: r['textlen'] < 100 and r['files']))
print('본문 100자 미만 + 이미지 있음(포스터형)', pct(lambda r: r['textlen'] < 100 and r['imgs']))
print('첨부 있음', pct(lambda r: r['files']))
print('이미지 있음', pct(lambda r: r['imgs']))
print('이메일 포함', pct(lambda r: r['email']))
print('전화번호 포함', pct(lambda r: r['phone']))
print('학번/마스킹 이름 패턴', pct(lambda r: r['stuid']))
print('외부 신청폼 링크', pct(lambda r: r['forms']))
print('마감·기간 표현', pct(lambda r: r['deadline']))
print('첨부 확장자', Counter(e for r in ok for e in r['files']).most_common(10))
lens = sorted(r['textlen'] for r in ok)
print('본문 길이 중앙값', lens[n // 2] if n else '-', '90%', lens[int(n * .9)] if n else '-')
print('본문 미검출 사이트', sorted({r['site'] for r in res if not r.get('found') and not r.get('err')}))
