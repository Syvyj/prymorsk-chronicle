"""Mirror the HTML pages of lost local sites from the Wayback Machine, slowly and resumably.

    python3 wayback_mirror.py            # work through QUEUE in order
    python3 wayback_mirror.py primrda    # just one site

Pages land in mirror/<site>/<slug>.html (original HTML via the id_ endpoint, no Wayback toolbar)
and mirror/<site>/manifest.json maps slug -> {url, ts}. Photos are fetched later, like fetch_images.py does.
"""
import hashlib, json, os, re, sys, time
from urllib.parse import quote, unquote
from fetch_images import get  # same polite retry/backoff that survived Wayback's connection bans

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'mirror')
# kept for the community only, never published and never under the web server's folder
PRIVATE = {'primrada': os.environ.get('PRYM_ARCHIVE', '../prymorsk-archive') + '/private'}
# private archives: the most important documents first, drafts last
PRIORITY = [r'rishennya-rajonnoji-radi|/rishennya', r'e-deklaruvannia', r'poimenne-golosuvannya', r'byudzhet',
            r'selishchna-ta-silski-radi', r'dovidoma-meshkantsiv', r'novini|povidomlennya', r'kerivnitstvo', r'komunalna']
# not fetched at all: drafts of the same decisions that are kept in their final form (user's call)
PRIVATE_SKIP = re.compile(r'proekti-rishen')
# private archives cover 2016–2022 only: a year in the address outside that range means an older document (user's call)
OLD_YEAR = re.compile(r'(?<!\d)(19\d\d|200\d|201[0-5])(?!\d)')


def content_tail(url):
    """Joomla serves one article/list under many parent paths: the part from the last /<id>- segment identifies it."""
    p = unquote(url).split('://', 1)[-1].split('/', 1)[-1].rstrip('/').replace('.html', '')
    ids = list(re.finditer(r'(^|/)\d+-', p))
    return p[ids[-1].start():].lstrip('/') if ids else p
# (name, cdx url, matchType) — smallest and oldest first; the district council (20k+ pages, lots of personal data) last
QUEUE = [
    ('primorsk_zp', 'primorsk.zp.ua', 'domain'),
    ('imsu_history', 'imsu-zaporizhzhya.com/mista-i-sela-zaporizkoi-oblasti/primorskij-rajon/', 'prefix'),
    ('preslav_school', 'preslavzoh.wixsite.com/kz-preslav', 'prefix'),
    ('prim24_sub', 'blog1.prim24.in.ua', 'host'),
    ('prim24_sub', 'blog2.prim24.in.ua', 'host'),
    ('prym', 'prym.in.ua', 'domain'),
    ('travel_mrprim', 'travel.mrprim.zp.ua', 'host'),
    ('primorsk_in', 'primorsk.in.ua', 'domain'),
    ('rcdt', 'rcdtprim.ucoz.ru', 'domain'),
    ('school3', 'primschool3.ucoz.com', 'domain'),
    ('licey', 'liceyprim96.ucoz.ua', 'domain'),
    ('school2', 'prim2school.ucoz.ua', 'domain'),
    ('primrda', 'primrda.gov.ua', 'domain'),
    ('primroo', 'primroo.ucoz.ua', 'domain'),
    ('tavriya', 'tavriya.co.ua/index.php/primorsk', 'prefix'),
    ('primrada', 'primrada.gov.ua', 'domain'),
    # village school and district sites on uCoz that no longer answer (the live ones: live_mirror.py)
    ('yelyzavetivka', 'elizavetovkakz.at.ua', 'domain'),
    ('kolarivka', 'kznvk-kolarovka.ucoz.ua', 'domain'),
    ('banivka', 'banovka.ucoz.ua', 'domain'),
    ('radolivka', 'kz-radolovka.ucoz.ru', 'domain'),
    ('zelenivka', 'zelenovka.ucoz.ru', 'domain'),
    ('partyzany', 'partizanzosh.ucoz.net', 'domain'),
    ('rmc', 'kz-rmc.ucoz.ua', 'domain'),
    ('fisra', 'fisra-prim-roo.ucoz.ua', 'domain'),
    # found later through the osvita.ua school catalogue (2026-10): only their news and articles are fetched
    ('marynivka', 'mzosh.ucoz.ua', 'domain'),
    ('yurivka', 'ubzh.ucoz.ua', 'domain'),
    ('school1', 'prim1school.at.ua', 'domain'),
    ('preslav_bzosh', 'preslavzoh.ucoz.ua', 'domain'),
]
# sites whose other captures are uCoz calendars, logins and comment pages: fetch only what the chronicle reads
NEWS = re.compile(r'/(news|blog)/[^?]*\d{4}-\d{2}-\d{2}-\d+$|/publ/[^?]*\d+-\d+-\d+$')
ONLY = {'marynivka': NEWS, 'yurivka': NEWS, 'school1': NEWS, 'preslav_bzosh': NEWS}
# navigation / technical URLs that are not content
SKIP = re.compile(r'(\?|&)(tmpl=component|print=|format=(feed|pdf|raw)|replytocom|share=|lang=ru|task=|view=login|option=com_mailto)|'
                  r'/(feed|rss|wp-json|wp-admin|wp-login|xmlrpc|tag|author|search|login|register|cgi-bin)(/|\?|$)|'
                  r'\.(css|js|jpg|jpeg|png|gif|ico|pdf|doc|docx|xls|zip|rar|mp3|mp4|swf)(\?|$)', re.I)
PAUSE = 4  # seconds between requests; Wayback refuses connections above ~15/min


def slug(url):
    s = re.sub(r'^https?://(www\.)?', '', unquote(url)).rstrip('/')
    s = re.sub(r'[^\w.-]+', '_', s)[:120]
    return f'{s}_{hashlib.md5(url.encode()).hexdigest()[:6]}'


def listing(url, match):
    """All captured pages, in 60k-row chunks (CDX resumeKey), so big sites are not cut at the first chunk."""
    rows, resume = [], ''
    while True:
        cdx = (f'https://web.archive.org/cdx/search/cdx?url={quote(url)}&matchType={match}&filter=statuscode:200'
               f'&filter=mimetype:text/html&collapse=urlkey&fl=timestamp,original&output=json&limit=60000&showResumeKey=true'
               + (f'&resumeKey={quote(resume)}' if resume else ''))
        _, body = get(cdx)
        if body is None:
            sys.exit(f'CDX failed for {url}; re-run later')
        chunk = json.loads(body)[1:] if body.strip() else []
        resume = chunk[-1][0] if len(chunk) >= 2 and chunk[-2] == [] else ''  # [..., [], [resumeKey]]
        rows += [r for r in chunk if len(r) == 2]
        if not resume:
            return [(ts, u) for ts, u in rows if not SKIP.search(u)]
        time.sleep(PAUSE)


def rank(url):
    return next((i for i, p in enumerate(PRIORITY) if re.search(p, url)), len(PRIORITY))


def mirror(name, url, match):
    d = os.path.join(PRIVATE.get(name, OUT), name)
    os.makedirs(d, exist_ok=True)
    mpath = os.path.join(d, 'manifest.json')
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    cache = os.path.join(d, f'_cdx_{slug(url)}.json')
    if os.path.exists(cache):
        rows = json.load(open(cache))
    else:
        rows = listing(url, match)
        json.dump(rows, open(cache, 'w'))
        time.sleep(PAUSE)
    todo = [(ts, u) for ts, u in rows if slug(u) not in manifest and (name not in ONLY or ONLY[name].search(u))]
    if name in PRIVATE:
        have = {content_tail(m['url']) for m in manifest.values() if not m.get('missing')}
        todo = [(ts, u) for ts, u in todo if not PRIVATE_SKIP.search(u) and not OLD_YEAR.search(unquote(u))
                and content_tail(u) not in have and not have.add(content_tail(u))]  # first address of each page only
    if name in PRIVATE:
        todo.sort(key=lambda r: rank(r[1]))
    print(f'{name} ({url}): {len(rows)} pages, {len(todo)} to fetch', flush=True)
    for i, (ts, u) in enumerate(todo, 1):
        ctype, data = get(f'https://web.archive.org/web/{ts}id_/{u}')
        s = slug(u)
        if data and 'html' in (ctype or ''):
            open(os.path.join(d, s + '.html'), 'wb').write(data)
            manifest[s] = {'url': u, 'ts': ts}
        else:
            manifest[s] = {'url': u, 'ts': ts, 'missing': True}
        if i % 25 == 0 or i == len(todo):
            json.dump(manifest, open(mpath, 'w'), ensure_ascii=False, indent=0)
            print(f'  {name}: {i}/{len(todo)}', flush=True)
        time.sleep(PAUSE)


def retry(name):
    """Pages that failed at the first capture: try up to 3 other captures of the same address."""
    d = os.path.join(PRIVATE.get(name, OUT), name)
    mpath = os.path.join(d, 'manifest.json')
    manifest = json.load(open(mpath))
    todo = [(s, m) for s, m in manifest.items() if m.get('missing') and not m.get('retried')]
    print(f'{name}: {len(todo)} missing pages to retry', flush=True)
    for i, (s, m) in enumerate(todo, 1):
        _, body = get(f'https://web.archive.org/cdx/search/cdx?url={quote(m["url"])}&filter=statuscode:200&fl=timestamp&output=json&limit=10')
        time.sleep(PAUSE)
        stamps = [r[0] for r in (json.loads(body)[1:] if body and body.strip() else []) if r[0] != m['ts']][-3:]
        for ts in stamps:
            ctype, data = get(f'https://web.archive.org/web/{ts}id_/{m["url"]}')
            time.sleep(PAUSE)
            if data and 'html' in (ctype or ''):
                open(os.path.join(d, s + '.html'), 'wb').write(data)
                manifest[s] = {'url': m['url'], 'ts': ts}
                break
        else:
            manifest[s]['retried'] = True
        if i % 25 == 0 or i == len(todo):
            json.dump(manifest, open(mpath, 'w'), ensure_ascii=False, indent=0)
            print(f'  {name}: {i}/{len(todo)} ok={sum(1 for x, _ in todo[:i] if not manifest[x].get("missing"))}', flush=True)


if __name__ == '__main__':
    assert content_tail('https://primrada.gov.ua/silski-radi/zelenivska-s-r/216-rishennya-rajonnoji-radi/sklikannya/sesiya-46.html?start=4') == \
        content_tail('https://primrada.gov.ua/rishennya-rajonnoji-radi/216-rishennya-rajonnoji-radi/sklikannya/sesiya-46.html?start=4')
    assert NEWS.search('http://ubzh.ucoz.ua/news/2019-05-24-120') and NEWS.search('http://prim1school.at.ua/publ/1-1-0-12')
    assert not NEWS.search('http://ubzh.ucoz.ua/news/2019-05') and not NEWS.search('http://ubzh.ucoz.ua/publ/1')
    if sys.argv[1:2] == ['--retry']:  # python3 wayback_mirror.py --retry school2 tavriya
        for n in sys.argv[2:]:
            retry(n)
        sys.exit()
    only = sys.argv[1:]
    for name, url, match in QUEUE:
        if not only or name in only:
            mirror(name, url, match)
    print('mirror queue finished', flush=True)
