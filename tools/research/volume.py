"""게시판별 최근 N일 공지량 실측. 호스트당 순차 요청 + 1초 간격.

사용법: python volume.py boards.txt out/volume.json [일수=30]
"""
import sys, re, ssl, json, time, datetime, urllib.request, urllib.parse, html
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

ctx = ssl.create_default_context()  # 2026-11-13 기준 수집 대상 호스트 모두 인증서 검증 통과
UA = 'Mozilla/5.0 (team17 notice research; low-rate)'
DAYS = int(sys.argv[3]) if len(sys.argv) > 3 else 30
UNTIL = datetime.date.today().isoformat()
SINCE = (datetime.date.today() - datetime.timedelta(days=DAYS)).isoformat()
MAXPAGE = 10

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    t = time.time()
    with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
        return r.read().decode('utf-8', 'replace'), time.time() - t

def norm(d):
    d = d.replace('.', '-')
    if re.match(r'^\d\d-\d\d-\d\d$', d):
        d = '20' + d
    return d

def parse_rows(h):
    rows = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S):
        m = re.search(r'bidx=(\d+)', tr) or re.search(r'[?&]idx=(\d+)', tr)
        if not m:
            continue
        dm = re.search(r'(20\d\d[-.]\d\d[-.]\d\d|\b\d\d\.\d\d\.\d\d\b)', tr)
        tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)
        first = re.sub(r'<[^>]+>|\s', '', tds[0]) if tds else ''
        pinned = not first.isdigit()
        a = re.search(r'<a[^>]*>(.*?)</a>', tr, re.S)
        title = html.unescape(re.sub(r'<[^>]+>|\s+', ' ', a.group(1)).strip()) if a else ''
        hasfile = bool(re.search(r'class="file[^"]*"[^>]*>\s*<(img|span|i|a)', tr))
        href = re.search(r"href=['\"]([^'\"]*(?:bidx|idx)=\d+[^'\"]*)", tr)
        rows.append(dict(id=m.group(1), date=norm(dm.group(1)) if dm else None,
                         pinned=pinned, title=title, file=hasfile,
                         href=html.unescape(href.group(1)) if href else None))
    if not rows:  # 카드형(blog_list) 레이아웃
        for blk in re.split(r'<div class="list">', h)[1:]:
            m = re.search(r'bidx=(\d+)', blk)
            if not m:
                continue
            dm = re.search(r'20\d\d-\d\d-\d\d', blk)
            a = re.search(r'<h2[^>]*>\s*<a[^>]*>(.*?)</a>', blk, re.S)
            title = html.unescape(re.sub(r'<[^>]+>|\s+', ' ', a.group(1)).strip()) if a else ''
            href = re.search(r"href=['\"]([^'\"]*bidx=\d+[^'\"]*)", blk)
            rows.append(dict(id=m.group(1), date=dm.group(0) if dm else None,
                             pinned='ico_notice' in blk.split('</h2>')[0], title=title, file=False,
                             href=html.unescape(href.group(1)) if href else None))
    return rows

def board(line):
    site, label, url = line.split('|', 2)
    seen, recent, pins, times, pages, err = {}, [], 0, [], 0, None
    for p in range(1, MAXPAGE + 1):
        u = url + ('&' if '?' in url else '?') + f'page={p}'
        try:
            h, dt = get(u); times.append(dt)
        except Exception as e:
            err = str(e)[:60]; break
        time.sleep(1)
        rows = parse_rows(h); pages = p
        new = [r for r in rows if r['id'] not in seen]
        if not [r for r in new if not r['pinned']] and p > 1:
            break
        for r in new:
            seen[r['id']] = r
            if r['pinned'] and p == 1:
                pins += 1
            if r['date'] and r['date'] >= SINCE and r['date'] <= UNTIL:
                r['view'] = urllib.parse.urljoin(u, r['href']) if r['href'] else None
                recent.append(r)
        normal = [r for r in new if not r['pinned'] and r['date']]
        if normal and min(r['date'] for r in normal) < SINCE:
            break
    return dict(site=site, label=label, url=url, err=err, pages=pages, rows=len(seen),
                pins=pins, recent=recent, avg_s=round(sum(times)/len(times), 2) if times else None)

lines = [l.strip() for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
byhost = defaultdict(list)
for l in lines:
    byhost[urllib.parse.urlparse(l.split('|', 2)[2]).netloc].append(l)

def host_job(ls):
    return [board(l) for l in ls]

out = []
with ThreadPoolExecutor(6) as ex:
    for res in ex.map(host_job, byhost.values()):
        out.extend(res)
        for b in res:
            print(f"{b['site']}|{b['label']}|recent={len(b['recent'])} pins={b['pins']} rows={b['rows']} pages={b['pages']} t={b['avg_s']} {b['err'] or ''}", flush=True)
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
