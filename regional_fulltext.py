"""Fetch full texts of regional news listed in regional_news*.jsonl.

Allowed: state bodies' sites (official information / news of the day) and media whose editors agreed
(reporter-ua.com, mig.com.ua, 06137.com.ua, zp-pravda.info; condition: a link to the original at the top).
zp-pravda.info exists only in the Wayback Machine: its pages are fetched there (id_ = original HTML).
Everyone else keeps headline + excerpt + link (see extract_articles.py).

    python3 regional_fulltext.py     # resumable; pages cached in regional_pages/<host>/<slug>.html
"""
import glob, hashlib, json, os, re, time, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'regional_pages')
ALLOWED = re.compile(r'(^|\.)(zoda\.gov\.ua|zor\.gov\.ua|zp\.gov\.ua|reporter-ua\.com|mig\.com\.ua|06137\.com\.ua|zp-pravda\.info)$')
WAYBACK = re.compile(r'^https?://web\.archive\.org/web/(\d+)[a-z_]*/(.+)$')


def origin_host(url):
    """Host of the original site, also for web.archive.org/web/<ts>/<url> links."""
    m = WAYBACK.match(url)
    return re.sub(r'^https?://(www\.)?', '', m.group(2) if m else url).split('/')[0].split(':')[0]


def fetch_url(url):
    m = WAYBACK.match(url)
    return f'https://web.archive.org/web/{m.group(1)}id_/{m.group(2)}' if m else url
PAUSE = 3


def page_path(url):
    host = re.sub(r'^https?://(www\.)?', '', url).split('/')[0]
    return os.path.join(OUT, host, hashlib.md5(url.encode()).hexdigest() + '.html')


if __name__ == '__main__':
    urls = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'regional_news*.jsonl'))):
        for line in open(f, encoding='utf-8'):
            r = json.loads(line)
            host = origin_host(r['url'])
            if ALLOWED.search(host) and r['url'] not in urls and r.get('date', '') < '2023-01-01':
                urls.append(r['url'])
    todo = [u for u in urls if not os.path.exists(page_path(u))]
    print(f'{len(urls)} allowed pages, {len(todo)} to fetch', flush=True)
    for i, u in enumerate(todo, 1):
        try:
            req = urllib.request.Request(fetch_url(u), headers={'User-Agent': 'Mozilla/5.0 (prymorsk-memory-archive; personal preservation)'})
            body = urllib.request.urlopen(req, timeout=40).read()
        except urllib.error.HTTPError as e:
            body = b'' if e.code in (404, 410) else None
        except Exception:
            body = None
        if body is not None:  # network errors are retried on the next run
            os.makedirs(os.path.dirname(page_path(u)), exist_ok=True)
            open(page_path(u), 'wb').write(body)
        if i % 25 == 0:
            print(f'{i}/{len(todo)}', flush=True)
        time.sleep(PAUSE + (2 if WAYBACK.match(u) else 0))  # Wayback bans bursts sooner
    print('done', flush=True)
