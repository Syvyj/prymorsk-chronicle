"""What Common Crawl (an archive independent of Wayback) holds for our sites, 2015–2022.

    python3 cc_survey.py          # resumable; index rows cached in cc_index/<domain>/<crawl>.jsonl
    python3 cc_survey.py report   # per domain: pages / images / PDFs, and how many Wayback never had

Index only: the page bodies are fetched later from Common Crawl's WARC files (one HTTP range request each).
"""
import glob, json, os, re, sys, time, urllib.request, urllib.error
from urllib.parse import quote, urlsplit

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'cc_index')
DOMAINS = ['mrprim.zp.ua', 'prim24.in.ua', 'primorsk.biz', 'primorsk.in.ua', 'primorsk.zp.ua', 'prym.in.ua',
           'primrda.gov.ua', 'primrada.gov.ua', 'rcdtprim.ucoz.ru', 'primschool3.ucoz.com', 'liceyprim96.ucoz.ua',
           'prim2school.ucoz.ua', 'primroo.ucoz.ua', 'tavriya.co.ua']
ARCHIVE_DIRS = {'mrprim.zp.ua': 'archive_mrprim', 'prim24.in.ua': 'archive_prim24', 'primorsk.biz': 'archive_pro_prim'}
UA = {'User-Agent': 'prymorsk-memory-archive (personal preservation)'}


def get(url, tries=5):
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read().decode('utf-8', 'ignore')
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return ''  # "no captures" for this crawl
        except Exception:
            pass
        time.sleep(15 * (n + 1))  # the index server answers 502/503 under load
    return None


def crawls():
    c = json.loads(get('https://index.commoncrawl.org/collinfo.json'))
    return [x['id'] for x in c if '2015' <= x['id'][8:12] <= '2022']


def survey():
    for crawl in crawls():
        for d in DOMAINS:
            path = os.path.join(OUT, d, crawl + '.jsonl')
            if os.path.exists(path):
                continue
            base = f'https://index.commoncrawl.org/{crawl}-index?url={quote("*." + d)}&output=json'
            pages = get(base + '&showNumPages=true')
            if pages is None:
                print(f'{crawl} {d}: index unavailable, retry later', flush=True)
                continue
            n = json.loads(pages).get('pages', 1) if pages.strip().startswith('{') else 0
            rows, ok = [], True
            for p in range(n):
                body = get(base + f'&page={p}')
                if body is None:
                    ok = False
                    break
                rows += [l for l in body.splitlines() if l.startswith('{')]
                time.sleep(1)
            if ok:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                open(path, 'w').write('\n'.join(rows) + ('\n' if rows else ''))
                print(f'{crawl} {d}: {len(rows)}', flush=True)
            time.sleep(1)


def report():
    wb = set()  # every address the Wayback copies gave us
    for m in glob.glob(os.path.join(ROOT, 'mirror', '*', 'manifest.json')):
        wb |= {v['url'].split('://')[-1].removeprefix('www.').rstrip('/') for v in json.load(open(m)).values()}
    media = json.load(open(os.path.join(ROOT, 'media', 'manifest.json')))
    # the first three sites were saved by an older tool: archive_<site>/<encoded path>/index.html ('2F_3Fp_3D1016' = '/?p=1016')
    # ponytail: compare on letters and digits only; good enough for a count, not for matching single pages
    norm = lambda x: re.sub(r'%?2f|%?3f|%?3d|%?26|[^a-z0-9]', '', x.lower())
    arch = {d: {norm(x) for x in os.listdir(os.path.join(ROOT, a))} for d, a in ARCHIVE_DIRS.items()}
    for d in DOMAINS:
        rows = {}
        for f in glob.glob(os.path.join(OUT, d, '*.jsonl')):
            for l in open(f):
                try:
                    r = json.loads(l, strict=False)
                except ValueError:
                    continue  # a row split by a raw newline inside a URL
                if r.get('status') == '200':
                    rows.setdefault(r['url'], r)
        kind = lambda r: 'img' if r.get('mime', '').startswith('image') else 'pdf' if 'pdf' in r.get('mime', '') else 'page' if 'html' in r.get('mime', '') else 'other'
        key = lambda u: u.split('://')[-1].removeprefix('www.').rstrip('/')
        cnt = {}
        for u, r in rows.items():
            k = kind(r)
            if k == 'img':
                new = key(u).lower() not in media
            elif d in arch:
                new = norm(urlsplit(u).path + ('?' + urlsplit(u).query if urlsplit(u).query else '')) not in arch[d]
            else:
                new = key(u) not in wb
            cnt.setdefault(k, [0, 0])
            cnt[k][0] += 1
            cnt[k][1] += new
        print(f'{d:24}', '  '.join(f'{k}: {a} (нових {b})' for k, (a, b) in sorted(cnt.items())) or '—')


if __name__ == '__main__':
    report() if sys.argv[1:] == ['report'] else survey()
