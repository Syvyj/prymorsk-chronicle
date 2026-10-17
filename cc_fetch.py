"""Pages Wayback never had but Common Crawl kept: council posts (mrprim.zp.ua/?p=N) and ПРО Приморськ (content.php?id=N).

    python3 cc_fetch.py          # needs cc_index/ from cc_survey.py; resumable
    python3 cc_fetch.py --docs   # adopted documents of the district administration / council -> private

One HTTP range request per page from Common Crawl's WARC files, ~1 per second.
Public posts -> mirror/cc_<site>/ (extract_articles.py reads them as the original site);
council documents (decisions, sessions, orders) -> the private folder, never the portal.
"""
import glob, gzip, json, os, re, sys, time, urllib.request
from wayback_mirror import slug, OUT
from tools.legacy.move_council_docs import is_doc

ROOT = os.path.dirname(os.path.abspath(__file__))
PRIVATE = os.environ.get('PRYM_ARCHIVE', '../prymorsk-archive') + '/private/mrprim_docs_cc'
UA = {'User-Agent': 'prymorsk-memory-archive (personal preservation)'}
# CC domain -> (our mirror dir, id pattern in the URL, id pattern in the paths we already hold)
SITES = {
    'mrprim.zp.ua': ('cc_mrprim', r'/\?p=(\d+)$', r'p(?:=|_3D)(\d+)'),
    'primorsk.biz': ('cc_pro_prim', r'pro\.primorsk\.biz/content\.php\?id=(\d+)$', r'id(?:=|_3D)(\d+)'),
    'primrda.gov.ua': ('cc_primrda', r'primrda\.gov\.ua/(?:news|kulturni_zakhodi|gordist_primorskogo_raionu)/(\d+)-',
                       r'primrda\.gov\.ua(?::80)?/(?:news|kulturni_zakhodi|gordist_primorskogo_raionu)/(\d+)-'),
}
SITE_OF = {'cc_mrprim': 'archive_mrprim', 'cc_pro_prim': 'archive_pro_prim', 'cc_primrda': 'primrda'}


def have(site, rx):
    """ids we hold already: public articles + the council documents moved to private storage."""
    ids = set()
    for a in json.load(open(os.path.join(ROOT, 'articles.json'))):
        if a['site'] == site and (m := re.search(rx, a.get('url') or a['path'])):
            ids.add(m.group(1))
    idx = os.environ.get('PRYM_ARCHIVE', '../prymorsk-archive') + '/private/mrprim_docs/index.json'
    if site == 'archive_mrprim' and os.path.exists(idx):
        ids |= {m.group(1) for r in json.load(open(idx)) if (m := re.search(rx, r['url']))}
    return ids


def body(r):
    o, n = int(r['offset']), int(r['length'])
    req = urllib.request.Request('https://data.commoncrawl.org/' + r['filename'], headers={**UA, 'Range': f'bytes={o}-{o + n - 1}'})
    for k in range(4):
        try:
            rec = gzip.decompress(urllib.request.urlopen(req, timeout=60).read())
            return rec.split(b'\r\n\r\n', 2)[2]  # WARC headers, HTTP headers, page
        except Exception:
            time.sleep(10 * (k + 1))
    return None


def title(page):
    t = re.search(rb'<title>(.*?)</title>', page, re.S | re.I)
    return re.split(r'\s+(?:&#8211;|–)\s+Приморськ', t.group(1).decode('utf-8', 'ignore').strip())[0] if t else ''


def fetch(domain, d, url_rx, have_rx):
    known = have(SITE_OF[d], have_rx)
    best = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'cc_index', domain, '*.jsonl'))):
        for l in open(f):
            try:
                r = json.loads(l, strict=False)
            except ValueError:
                continue
            m = re.search(url_rx, r['url'])
            # the last capture before the occupation; later ones may already be the occupiers' version
            if r.get('status') == '200' and m and m.group(1) not in known and r['timestamp'] < '20220401' \
                    and r['timestamp'] > best.get(m.group(1), {}).get('timestamp', ''):
                best[m.group(1)] = r
    out = os.path.join(OUT, d)
    os.makedirs(out, exist_ok=True)
    os.makedirs(PRIVATE, exist_ok=True)
    mpath, ppath = os.path.join(out, 'manifest.json'), os.path.join(PRIVATE, 'index.json')
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    private = json.load(open(ppath)) if os.path.exists(ppath) else []
    done = {m['url'] for m in manifest.values()} | {p['url'] for p in private}
    todo = [r for r in best.values() if r['url'] not in done]
    print(f'{domain}: {len(best)} pages Wayback lacks, {len(todo)} to fetch', flush=True)
    for i, r in enumerate(todo, 1):
        page = body(r)
        time.sleep(1)
        if page is None:
            continue
        s = slug(r['url'])
        if d == 'cc_mrprim' and is_doc(title(page)):
            open(os.path.join(PRIVATE, s + '.html'), 'wb').write(page)
            private.append({'url': r['url'], 'ts': r['timestamp'], 'title': title(page), 'file': s + '.html'})
        else:
            open(os.path.join(out, s + '.html'), 'wb').write(page)
            manifest[s] = {'url': r['url'], 'ts': r['timestamp'], 'cc': True}
        if i % 25 == 0 or i == len(todo):
            json.dump(manifest, open(mpath, 'w'), ensure_ascii=False, indent=0)
            json.dump(private, open(ppath, 'w'), ensure_ascii=False, indent=0)
            print(f'  {i}/{len(todo)}  public {len(manifest)}  private {len(private)}', flush=True)


if __name__ == '__main__':
    assert is_doc('Рішення №221 від 20.08.21р.: Про внесення змін') and not is_doc('Вітаємо з Днем Незалежності')
    for domain, (d, url_rx, have_rx) in SITES.items():
        if sys.argv[1:] != ['--docs'] and (not sys.argv[1:] or d in sys.argv[1:]):
            fetch(domain, d, url_rx, have_rx)


# adopted documents of the district state administration and the district council (docs_registry.py reads them)
DOCS = {
    'rda_cc': ('primrda.gov.ua', r'/uploads/\d{4}/\d\d/\d{6}N\d+[PD]\d*\.pdf$|/rozporiadzhennia_golovi_raiderzhadministratsii|/pasporti_biudzhetnikh_program'),
    'primrada_cc': ('primrada.gov.ua', r'/files/(rozporiadjenia/)?sesia\d+/rozporiadjenia_\d+\.pdf$|/files/passport_budjet_prog/'),
}


def fetch_docs(name, domain, rx):
    out = os.path.join(os.environ.get('PRYM_ARCHIVE', '../prymorsk-archive') + '/private', name)
    os.makedirs(out, exist_ok=True)
    ipath = os.path.join(out, 'index.json')
    index = json.load(open(ipath)) if os.path.exists(ipath) else []
    done = {r['url'] for r in index}
    best = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'cc_index', domain, '*.jsonl'))):
        for l in open(f):
            try:
                r = json.loads(l, strict=False)
            except ValueError:
                continue
            if r.get('status') == '200' and re.search(rx, r['url']) and '2016' <= r['timestamp'] < '20220401' \
                    and r['timestamp'] > best.get(r['url'], {}).get('timestamp', ''):
                best[r['url']] = r
    todo = [r for u, r in best.items() if u not in done]
    print(f'{name}: {len(best)} documents, {len(todo)} to fetch', flush=True)
    for i, r in enumerate(todo, 1):
        data = body(r)
        time.sleep(1)
        if data is None:
            continue
        ext = '.pdf' if 'pdf' in r.get('mime', '') else '.html'
        f = slug(r['url']) + ext
        open(os.path.join(out, f), 'wb').write(data)
        index.append({'url': r['url'], 'ts': r['timestamp'], 'file': f})
        if i % 25 == 0 or i == len(todo):
            json.dump(index, open(ipath, 'w'), ensure_ascii=False, indent=0)
            print(f'  {i}/{len(todo)}', flush=True)


def wayback_docs(name, domain, rx):
    """The same documents Wayback kept and Common Crawl did not (1 request / 5 s, Wayback's pace)."""
    out = os.path.join(os.environ.get('PRYM_ARCHIVE', '../prymorsk-archive') + '/private', name)
    ipath = os.path.join(out, 'index.json')
    index = json.load(open(ipath)) if os.path.exists(ipath) else []
    have = {re.sub(r'^https?://(www\.)?|:80(?=/)', '', r['url']) for r in index}
    cdx = urllib.request.urlopen(urllib.request.Request(
        f'https://web.archive.org/cdx/search/cdx?url={domain}/&matchType=prefix&filter=statuscode:200&collapse=urlkey'
        f'&fl=original,timestamp&limit=100000', headers=UA), timeout=300).read().decode()
    todo = [l.split() for l in cdx.splitlines() if len(l.split()) == 2 and re.search(rx, l.split()[0])
            and re.sub(r'^https?://(www\.)?|:80(?=/)', '', l.split()[0]) not in have and '2016' <= l.split()[1] < '20220401']
    print(f'{name}: {len(todo)} more from Wayback', flush=True)
    for i, (u, ts) in enumerate(todo, 1):
        try:
            data = urllib.request.urlopen(urllib.request.Request(f'https://web.archive.org/web/{ts}id_/{u}', headers=UA), timeout=120).read()
        except Exception:
            data = None
        time.sleep(5)
        if not data:
            continue
        f = slug(u) + ('.pdf' if u.lower().endswith('.pdf') else '.html')
        open(os.path.join(out, f), 'wb').write(data)
        index.append({'url': u, 'ts': ts, 'file': f, 'wayback': True})
        if i % 20 == 0 or i == len(todo):
            json.dump(index, open(ipath, 'w'), ensure_ascii=False, indent=0)
            print(f'  {i}/{len(todo)}', flush=True)


if __name__ == '__main__' and sys.argv[1:] == ['--docs']:
    for name, (domain, rx) in DOCS.items():
        fetch_docs(name, domain, rx)
        wayback_docs(name, domain, rx)
