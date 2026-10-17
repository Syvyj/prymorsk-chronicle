"""Recover article photos from the Wayback Machine and link them into the local archives.

    python3 fetch_images.py fetch   # list archived images via CDX, download into media/ (resumable)
    python3 fetch_images.py link    # point <img> tags in archive_*/ at downloaded files (idempotent)

Rewritten tags keep the original URL in data-wb-src, so `link` can be re-run after more downloads.
"""
import json, os, re, sys, time, glob
import urllib.request, urllib.error
from urllib.parse import urlsplit, unquote, quote

ROOT = os.path.dirname(os.path.abspath(__file__))
MEDIA = os.path.join(ROOT, 'media')
MANIFEST = os.path.join(MEDIA, 'manifest.json')  # key -> local path (relative to ROOT) or null if failed
SITES = {'archive_mrprim': 'mrprim.zp.ua', 'archive_prim24': 'prim24.in.ua', 'archive_pro_prim': 'pro.primorsk.biz'}
IMG_RE = r'.*\.(jpe?g|png|gif|webp|bmp)(\?.*)?$'
CDX_QUERIES = [
    ('mrprim.zp.ua', 'domain'), ('prim24.in.ua', 'domain'), ('pro.primorsk.biz', 'host'),
    *[(f'i{i}.wp.com/{h}/', 'prefix') for i in range(4) for h in
      ('www.mrprim.zp.ua', 'mrprim.zp.ua', 'www.prim24.in.ua', 'prim24.in.ua')],
]
# theme/plugin/CMS assets: icons and buttons, not article photos
SYSTEM_RE = re.compile(r'/(wp-content/(themes|plugins)|wp-includes|wp-admin|templates|modules|plugins|components|media/(jui|system|yendifvideoshare))/')
UA = {'User-Agent': 'Mozilla/5.0 (prymorsk-archive; personal preservation)'}


def get(url, tries=6):
    # Cyrillic / spaces in file names: http.client only sends ASCII; existing %-escapes are kept
    url = quote(url, safe=":/?&=%#+,;@!$'()*~[]")
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
                return r.headers.get('Content-Type', ''), r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return None, None
            wait = 120 if e.code == 429 else 10 * (n + 1)
        except urllib.error.URLError as e:
            # Wayback answers a burst with "connection refused" for several minutes
            wait = 300 if 'refused' in str(e.reason).lower() else 10 * (n + 1)
            print(f'  network: {e.reason}, waiting {wait}s', flush=True)
        except Exception:
            wait = 10 * (n + 1)
        time.sleep(wait)
    return None, None


def key(url):
    """Normalize any form of an image URL (wayback-wrapped, wp.com CDN, www, query) to host/path."""
    m = re.search(r'web\.archive\.org/web/\d+[a-z_]*/(.+)', url)
    if m:
        url = m.group(1)
    if url.startswith('//'):
        url = 'http:' + url
    if not re.match(r'https?:/', url):
        url = 'http://' + url
    url = re.sub(r'^(https?:)/+', r'\1//', url)
    u = urlsplit(url)
    host, path = u.netloc.lower().split(':')[0], unquote(u.path)
    if re.fullmatch(r'i\d\.wp\.com', host):
        host, _, path = path.lstrip('/').partition('/')
        path = '/' + path
    return (host.removeprefix('www.') + path).lower()


def unsized(k):
    return re.sub(r'-\d+x\d+(?=\.\w+$)', '', k)


def fetch():
    os.makedirs(MEDIA, exist_ok=True)
    manifest = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    cdx_cache = os.path.join(MEDIA, 'cdx.json')
    if os.path.exists(cdx_cache):
        rows = json.load(open(cdx_cache))
    else:
        rows = []
        for url, match in CDX_QUERIES:
            cdx = (f'https://web.archive.org/cdx/search/cdx?url={quote(url)}&matchType={match}'
                   f'&filter=statuscode:200&filter=original:{quote(IMG_RE)}&collapse=urlkey&fl=timestamp,original&output=json')
            _, body = get(cdx)
            if body is None:
                sys.exit(f'CDX failed for {url}, not caching; re-run later')
            got = json.loads(body)[1:] if body.strip() else []
            print(f'CDX {url}: {len(got)}')
            rows += got
            time.sleep(3)
        json.dump(rows, open(cdx_cache, 'w'))
    todo = {}  # key -> (timestamp, original); prefer captures without query string
    for ts, orig in rows:
        k = key(orig)
        if SYSTEM_RE.search(k):
            continue
        if not manifest.get(k) and (k not in todo or '?' in todo[k][1]):  # failed ones are retried on re-run
            todo[k] = (ts, orig)
    print(f'to download: {len(todo)} (already done: {len(manifest)})')

    # ponytail: ~15 requests/min — Wayback refuses connections above that; ~2.5h for 2k images
    for i, (k, (ts, orig)) in enumerate(todo.items(), 1):
        rel = os.path.join('media', *k.split('/'))
        if not os.path.exists(os.path.join(ROOT, rel)):
            ctype, data = get(f'https://web.archive.org/web/{ts}im_/{orig}')
            if data and ctype.startswith('image/'):
                os.makedirs(os.path.dirname(os.path.join(ROOT, rel)), exist_ok=True)
                with open(os.path.join(ROOT, rel), 'wb') as f:
                    f.write(data)
            else:
                rel = None
            time.sleep(4)
        manifest[k] = rel
        if i % 20 == 0 or i == len(todo):
            json.dump(manifest, open(MANIFEST, 'w'), ensure_ascii=False)
            print(f'{i}/{len(todo)}  ok={sum(1 for v in manifest.values() if v)}', flush=True)


def link():
    manifest = json.load(open(MANIFEST))
    lookup = {}
    for k, rel in manifest.items():
        if rel:
            lookup.setdefault(unsized(k), rel)
            lookup[k] = rel
    attr = lambda tag, name: (re.search(rf'\s{name}\s*=\s*(["\'])(.*?)\1', tag, re.S) or [None, None, None])[2]
    stats = {'linked': 0, 'missing': 0}

    def fix(tag, site, page_dir):
        src = attr(tag, 'data-wb-src') or attr(tag, 'src')
        if not src or src.startswith('data:'):
            return tag
        if not re.match(r'(https?:)?//', src) and not src.startswith('/'):
            if os.path.exists(os.path.join(page_dir, unquote(src.split('?')[0]))):
                return tag  # already a local file next to the page
            src = f'http://{site}/{src}'
        cands = [src, attr(tag, 'data-orig-file') or '']
        rel = next((lookup.get(k) or lookup.get(unsized(k)) for k in map(key, filter(None, cands))
                    if lookup.get(k) or lookup.get(unsized(k))), None)
        if not rel:
            stats['missing'] += 1
            return tag
        stats['linked'] += 1
        tag = re.sub(r'\s(srcset|sizes|data-wb-src)\s*=\s*(["\']).*?\2', '', tag, flags=re.S)
        tag = re.sub(r'\ssrc\s*=\s*(["\']).*?\1', f' src="/{quote(rel)}" data-wb-src="{src}"', tag, count=1, flags=re.S)
        return tag

    for d, site in SITES.items():
        for path in glob.glob(os.path.join(ROOT, d, '**', 'index.html'), recursive=True):
            html = open(path, encoding='utf-8', errors='ignore').read()
            new = re.sub(r'<img\b[^>]*>', lambda m: fix(m.group(0), site, os.path.dirname(path)), html, flags=re.S)
            if new != html:
                open(path, 'w', encoding='utf-8').write(new)
    print(stats)


if __name__ == '__main__':
    assert key('http://web.archive.org/web/2017im_/https://i2.wp.com/www.prim24.in.ua/a/B.jpg?w=1') == 'prim24.in.ua/a/b.jpg'
    assert key('https:/www.mrprim.zp.ua/%D1%88.jpg') == 'mrprim.zp.ua/ш.jpg'
    assert unsized('x/photo-300x200.jpg') == 'x/photo.jpg'
    assert quote('http://a.ua/uploads/громадська рада, 7.jpg?x=1', safe=":/?&=%#+,;@!$'()*~[]").isascii()
    {'fetch': fetch, 'link': link}[sys.argv[1]]()
