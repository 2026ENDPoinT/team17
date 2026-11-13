"""volume.py 결과를 요약한다: 고유 글 수, 하루 평균, 게시판 순위, 같은 제목 중복.

사용법: python summarize.py out/volume.json [일수=30]  (volume.py에 준 일수와 같게)
"""
import json
import sys
from collections import defaultdict

data = json.load(open(sys.argv[1], encoding='utf-8'))
days = int(sys.argv[2]) if len(sys.argv) > 2 else 30

ids = defaultdict(set)      # bidx -> 게시판들
titles = defaultdict(set)   # 제목 -> bidx들
per_board = []
for b in data:
    key = f"{b['site']}|{b['label']}"
    normal = [r for r in b['recent'] if not r['pinned']]
    per_board.append((len(normal), key))
    for r in b['recent']:
        ids[r['id']].add(key)
        titles[r['title'].strip()].add(r['id'])

def grad_only(boards):
    return all('대학원' in k or k.startswith('gsp|') for k in boards)
undergrad = sum(1 for boards in ids.values() if not grad_only(boards))

print(f"게시판 {len(data)}개, 오류 {sum(1 for b in data if b['err'])}개")
print(f"고유 글(bidx) {len(ids)}건 (하루 {len(ids)/days:.1f}), 학부 대상 {undergrad}건 (하루 {undergrad/days:.1f})")
print(f"새 글 0건 게시판: {sum(1 for n, _ in per_board if n == 0)}개")
empty = [b['site'] + '|' + b['label'] for b in data if b['rows'] == 0]
print(f"목록을 하나도 못 읽은 게시판: {empty}")

print("\n새 글 많은 게시판 상위 15")
for n, k in sorted(per_board, reverse=True)[:15]:
    print(f"  {n:4d}  {k}")

dups = {t: s for t, s in titles.items() if len(s) > 1}
print(f"\n같은 제목, 다른 bidx: {len(dups)}종, 사본 {sum(len(s) - 1 for s in dups.values())}건")
for t, s in sorted(dups.items(), key=lambda x: -len(x[1]))[:10]:
    print(f"  {len(s):2d}  {t[:60]}")
