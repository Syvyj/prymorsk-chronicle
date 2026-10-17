"""Photos for the mirrored sites (mirror/<site>/*.html): only those in the article body and its lead photo.

    python3 mirror_images.py fetch   # find them, download from Wayback into media/ (resumable, shares media/manifest.json)
    python3 mirror_images.py link    # point <img> in the mirrored pages at the local files (idempotent)

Sidebar banners, counters and site logos are never fetched, so they stay remote and the cleaner drops them.
"""
import json, os, re, sys, time
from urllib.parse import urljoin, quote
import clean_article
from extract_articles import MIRRORS, BODY, read_html
from fetch_images import get, key, unsized, SYSTEM_RE, MANIFEST, ROOT

JUNK = re.compile(r'logo|icon|smil|emoti|/sm/|/\.s/|banner|baner|button|counter|informer|avatar|gravatar|pixel|blank\.gif|spacer', re.I)
LEAD = re.compile(r'<img\b[^>]*class="[^"]*wp-post-image[^>]*>|class="itemImage"[^>]*>\s*<a[^>]*>\s*<img\b[^>]*>', re.S)
# a preview inside a link to the full-size photo -> the full-size one
FULL_LINK = re.compile(r'<a\b[^>]*href\s*=\s*["\']([^"\']+\.(?:jpe?g|png|gif|webp))["\'][^>]*>\s*<img\b[^>]*?\s(?:data-src|src)\s*=\s*["\']([^"\']+)', re.I | re.S)


def full_size(raw):
    """preview src -> full-size src; uCoz also names previews /_nw/1/s123.jpg next to /_nw/1/123.jpg."""
    links = {m.group(2): m.group(1) for m in FULL_LINK.finditer(raw)}
    return lambda src: links.get(src) or re.sub(r'(/_(?:nw|pu|ph|bl|si)/.*/)s(\d+\.jpe?g)$', r'\1\2', src)


def pages():
    for site, (d, cls, rx, _) in MIRRORS.items():
        man = json.load(open(os.path.join(ROOT, 'mirror', d, 'manifest.json')))
        for s, m in man.items():
            if not m.get('missing') and re.search(rx, m['url']):
                yield site, os.path.join(ROOT, 'mirror', d, s + '.html'), m


def wanted(site, path, url):
    """Photo URLs of one page: <img> inside the body container + the post's lead photo."""
    raw = read_html(path)
    srcs = []
    for nth in range(60 if site == 'primorsk_forum' else 4):
        c = clean_article.Cleaner(BODY[site], os.path.dirname(path), nth)
        c.feed(raw)
        if not c.depth and not c.done and not c.out:
            break
        srcs += c.seen
    for tag in LEAD.findall(raw):
        m = re.search(r'\s(?:data-src|src)="([^"]+)"', tag[tag.rfind('<img'):])
        srcs += [m.group(1)] if m else []
    big = full_size(raw)
    ok = lambda s: s and not s.startswith(('data:', '/media/')) and not JUNK.search(s) and urljoin(url, s).startswith('http')
    return {urljoin(url, big(s)): urljoin(url, s) for s in srcs if ok(s) and ok(big(s))}  # full size -> preview (fallback)


def archived(hosts):
    """host -> keys of the images Wayback lists for it (None: listing failed, don't filter). Cached in media/cdx_mirror.json."""
    path = os.path.join(ROOT, 'media', 'cdx_mirror.json')
    cache = json.load(open(path)) if os.path.exists(path) else {}
    for h in sorted(hosts - cache.keys()):
        _, body = get(f'https://web.archive.org/cdx/search/cdx?url={h}&matchType=domain&filter=statuscode:200'
                      f'&filter=mimetype:image/.*&collapse=urlkey&fl=original&output=json&limit=200000')
        time.sleep(4)
        if body is not None:
            cache[h] = [key(r[0]) for r in json.loads(body)[1:]] if body.strip() else []
            json.dump(cache, open(path, 'w'))
    # a listing cut at the limit (big photo hosts like radikal.ru) proves nothing: don't filter those
    return {h: set(cache[h]) if h in cache and len(cache[h]) < 200000 else None for h in hosts}


def fetch():
    manifest = json.load(open(MANIFEST))
    todo = {}
    for site, path, m in pages():
        for u, preview in wanted(site, path, m['url']).items():
            k = key(u)
            if not SYSTEM_RE.search(k) and not manifest.get(k) and not manifest.get(unsized(k)):
                todo.setdefault(k, (m['ts'], u, preview, m.get('live')))
    held = archived({k.split('/')[0] for k, r in todo.items() if not r[3]})  # live sites: fetched from the site itself
    todo = {k: r for k, r in todo.items() if r[3] or held.get(k.split('/')[0]) is None
            or {key(r[1]), key(r[2])} & held[k.split('/')[0]]}  # ask Wayback only for photos it lists
    print(f'to download: {len(todo)}', flush=True)
    # ponytail: ~10 requests/min, shares Wayback with the district council mirror running alongside
    for i, (k, (ts, u, preview, live)) in enumerate(todo.items(), 1):
        rel = None
        for src in dict.fromkeys([u, preview]):  # Wayback often kept only the preview that was shown on the page
            cand = os.path.join('media', *key(src).split('/'))
            if os.path.exists(os.path.join(ROOT, cand)):
                rel = cand
                break
            ctype, data = get(src if live else f'https://web.archive.org/web/{ts}im_/{src}')
            time.sleep(1 if live else 6)
            if data and (ctype or '').startswith('image/'):
                os.makedirs(os.path.dirname(os.path.join(ROOT, cand)), exist_ok=True)
                open(os.path.join(ROOT, cand), 'wb').write(data)
                rel = cand
                break
        manifest[k] = rel
        if i % 20 == 0 or i == len(todo):
            json.dump(manifest, open(MANIFEST, 'w'), ensure_ascii=False)
            print(f'{i}/{len(todo)}  ok={sum(1 for v in list(todo)[:i] if manifest.get(v))}', flush=True)


def link():
    manifest = json.load(open(MANIFEST))
    stats = {'linked': 0, 'pages': 0}
    for site, path, m in pages():
        b = open(path, 'rb').read()
        enc = 'cp1251' if re.search(rb'charset=["\']?(windows-1251|cp1251)', b[:3000], re.I) else 'utf-8'
        raw = b.decode('latin-1')  # byte-exact round trip; addresses are decoded with the page's charset below
        want = {key(u) for u in wanted(site, path, m['url'])}
        big = full_size(raw)

        def fix(mt):
            tag = mt.group(0)
            src = re.search(r'\s(?:data-src|src)\s*=\s*["\']([^"\']+)', tag.replace(' src=', ' _src=', 1) if 'data-src' in tag else tag)
            if not src:
                return tag
            k = key(urljoin(m['url'], big(src.group(1)).encode('latin-1').decode(enc, 'ignore')))
            rel = manifest.get(k) or manifest.get(unsized(k))
            if k not in want or not rel:
                return tag
            stats['linked'] += 1
            tag = re.sub(r'\s(srcset|sizes|data-src)\s*=\s*(["\']).*?\2', '', tag, flags=re.S)
            return re.sub(r'\ssrc\s*=\s*(["\']).*?\1', f' src="/{quote(rel)}" data-wb-src="{src.group(1)}"', tag, count=1, flags=re.S)
        new = re.sub(r'<img\b(?![^>]*data-wb-src)[^>]*>', fix, raw, flags=re.S)
        if new != raw:
            stats['pages'] += 1
            open(path, 'wb').write(new.encode('latin-1'))
    print(stats)


if __name__ == '__main__':
    assert full_size('')('http://x.ucoz.ua/_pu/0/s22592105.jpg') == 'http://x.ucoz.ua/_pu/0/22592105.jpg'
    assert full_size('<a href="/a/big.jpg"><img src="/a/sm.jpg"></a>')('/a/sm.jpg') == '/a/big.jpg'
    {'fetch': fetch, 'link': link}[sys.argv[1]]()
