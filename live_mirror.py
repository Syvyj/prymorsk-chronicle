"""Copy still-live uCoz sites of the community straight from uCoz, before the free hosting drops them.

    python3 live_mirror.py              # every site in LIVE, resumable
    python3 live_mirror.py nelgivka     # one site

Same layout as wayback_mirror.py: mirror/<name>/<slug>.html + manifest.json {slug: {url, ts, live}}, so
extract_articles.py reads them the same way (and drops news dated after 31.03.2022).
Polite: one request per second, HTML pages of the site's own host only.
"""
import json, os, re, sys, time, urllib.request, urllib.error
from collections import deque
from urllib.parse import urljoin, urldefrag, urlsplit
from wayback_mirror import slug, SKIP, OUT

LIVE = {
    'nelgivka': 'nelgivka-school.ucoz.ua', 'inzivka': 'inzovka-zosh.ucoz.ua', 'yeliseivka': 'nvkeleseevka.at.ua',
    'borysivka': 'schoolborisovka.ucoz.ru', 'orlivka': 'orlovkaschool.ucoz.net', 'primorskstep': 'primorskstep.at.ua',
    'cdut': 'cdut.ucoz.net', 'irc': 'rpmpk.ucoz.ua', 'osvita_otg': 'primzp45.ucoz.net', 'teacher_tanya': 'example-teacher.ucoz.ua',
}
# uCoz service pages: login, registration, search, guestbook, user profiles, file downloads, print versions
UCOZ_SKIP = re.compile(r'/index/(8|3|1|0-3)\b|/search|/gb|/index/0-\d+\?|/register|/user/|/load/0-0-0-\d+-20|\?ssid=|print|'
                       r'/(news|blog)/\d{4}-\d\d(-\d\d)?$|/stuff/|/board/|/dir/|/forum/0-0-1-34|rss|/tags/|\.(jpe?g|png|gif|pdf|docx?|xlsx?|pptx?|zip|rar|mp[34])$', re.I)
UA = {'User-Agent': 'Mozilla/5.0 (prymorsk-memory-archive; preservation of a community site)'}
LIMIT = 6000
PAUSE = 1.0


def fetch(url):
    for n in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                if 'html' not in r.headers.get('Content-Type', ''):
                    return None
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404, 410):
                return None
        except Exception:
            pass
        time.sleep(10 * (n + 1))
    return None


def crawl(name, host):
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    mpath = os.path.join(d, 'manifest.json')
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    seen = {m['url'] for m in manifest.values()}
    queue = deque([f'http://{host}/'] + [m['url'] for m in manifest.values() if not m.get('missing')])  # resume: re-read links
    queued = set(queue)
    today = time.strftime('%Y%m%d%H%M%S')
    fetched = 0
    while queue and len(manifest) < LIMIT:
        url = queue.popleft()
        s = slug(url)
        path = os.path.join(d, s + '.html')
        if url in seen and os.path.exists(path):
            body = open(path, 'rb').read()  # already saved: only harvest its links
        else:
            body = fetch(url)
            time.sleep(PAUSE)
            fetched += 1
            manifest[s] = {'url': url, 'ts': today, 'live': True, **({} if body else {'missing': True})}
            if body:
                open(path, 'wb').write(body)
            if fetched % 50 == 0:
                json.dump(manifest, open(mpath, 'w'), ensure_ascii=False, indent=0)
                print(f'  {name}: {len(manifest)} pages, {len(queue)} queued', flush=True)
        if not body:
            continue
        for href in re.findall(rb'href=["\']([^"\'#]+)', body):
            u = urldefrag(urljoin(url, href.decode('latin-1')))[0]
            p = urlsplit(u)
            if p.scheme in ('http', 'https') and p.netloc.lower().removeprefix('www.') == host and \
                    not SKIP.search(u) and not UCOZ_SKIP.search(u):
                u = f'http://{host}{p.path}' + (f'?{p.query}' if p.query else '')
                if u not in queued:
                    queued.add(u)
                    queue.append(u)
    json.dump(manifest, open(mpath, 'w'), ensure_ascii=False, indent=0)
    print(f'{name} ({host}): {len(manifest)} pages', flush=True)


# Blogspot blogs of community institutions: the content is in static pages; only the pages that tell about school life
BLOGS = {
    'gymn2_library': ('example-school-library', {'Головна', 'Виставки в бібліотеці', 'Бібліотечний журфікс', 'Про нас', 'Нова українська школа'}),
    'school3_health': ('example-school-health', {'Спортивне життя школи 2018', 'Наші досягнення', 'Фотогалерея', 'Оздоровчі заходи', 'У здоровому тілі - здоровий дух'}),
    # teachers' blogs no longer kept up (the author's rule: abandoned ones are saved, living ones are left to their owners)
    'blog_math_prim': ('example-teacher-blog-1', None), 'blog_pe_gymn2': ('example-teacher-blog-2', None), 'blog_labour': ('example-teacher-blog-3', None),
    'blog_primary': ('example-teacher-blog-4', None), 'blog_art': ('example-teacher-blog-5', None), 'blog_bulgarian': ('example-teacher-blog-6', None),
    'blog_english': ('example-teacher-blog-7', None), 'blog_ukrainian': ('example-teacher-blog-8', None),
}


def blogspot(name, blog, keep):
    """Blogger's own JSON feed gives every page and post at once; each kept one becomes a mirror page."""
    d = os.path.join(OUT, name)
    os.makedirs(d, exist_ok=True)
    manifest = {}
    for kind in ('pages', 'posts'):
        body = fetch_json(f'https://{blog}.blogspot.com/feeds/{kind}/default?alt=json&max-results=500')
        for e in body['feed'].get('entry', []):
            title = e['title']['$t'].strip()
            if kind == 'pages' and keep is not None and title not in keep:
                continue
            url = next(l['href'] for l in e['link'] if l['rel'] == 'alternate')
            s = slug(url)
            page = (f'<html><head><meta charset="utf-8"><title>{title}</title></head><body>'
                    f'<div class="post-body">{e["content"]["$t"]}</div></body></html>')
            open(os.path.join(d, s + '.html'), 'w', encoding='utf-8').write(page)
            manifest[s] = {'url': url, 'ts': re.sub(r'\D', '', e['published']['$t'][:19]), 'live': True}
    json.dump(manifest, open(os.path.join(d, 'manifest.json'), 'w'), ensure_ascii=False, indent=0)
    print(f'{name} ({blog}.blogspot.com): {len(manifest)} pages', flush=True)


def fetch_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.loads(r.read())


if __name__ == '__main__':
    if sys.argv[1:] == ['--blogs']:
        for name, (blog, keep) in BLOGS.items():
            blogspot(name, blog, keep)
        sys.exit()
    assert UCOZ_SKIP.search('http://x.ucoz.ua/index/8-0-1') and not UCOZ_SKIP.search('http://x.ucoz.ua/news/2017-03-03-131') and UCOZ_SKIP.search('http://x.ucoz.ua/news/2204-04')
    for name, host in LIVE.items():
        if not sys.argv[1:] or name in sys.argv[1:]:
            crawl(name, host)
