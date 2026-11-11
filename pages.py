"""One static page per article (timeline/p/<id>.html) so search engines and link previews see each story.

The chronicle's reader stays as it is; these pages carry the same text with their own title, description,
Open Graph and JSON-LD. Called by extract_articles.py after the fragments are written; standalone:

    python3 pages.py                                   # from timeline/data.json + timeline/a/*.html
    SITE_URL=https://example.org/timeline python3 pages.py   # + absolute canonical/og:image and sitemap.xml
"""
import html, json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
TL = os.path.join(ROOT, 'timeline')
SITE = os.environ.get('SITE_URL', '').rstrip('/')  # where timeline/ will be served; unknown until publishing
MONTHS = 'січень лютий березень квітень травень червень липень серпень вересень жовтень листопад грудень'.split()
MONTHS_GEN = 'січня лютого березня квітня травня червня липня серпня вересня жовтня листопада грудня'.split()


def date_h(d, e=0):
    """Same wording as the chronicle's fmt(): e = how many days an estimated date may be off."""
    y, m, day = d.split('-')
    if not e:
        return f'{int(day)} {MONTHS_GEN[int(m) - 1]} {y}'
    if e <= 31:
        return f'≈ {int(day)} {MONTHS_GEN[int(m) - 1]} {y}'
    return f'≈ {MONTHS[int(m) - 1]} {y}' if e <= 400 else f'≈ {y}'


def meta():
    """Shared lookup tables (source names, topic colours, village coordinates) from timeline/meta.js."""
    js = open(os.path.join(TL, 'meta.js'), encoding='utf-8').read()
    assert '\nconst META = {\n' in js, 'timeline/meta.js must keep the line "const META = {": the chronicle loads it as a script'
    return json.loads(js[js.index('{'):js.rindex('}') + 1])


def absolute(url):
    """Page-relative (../) or site-root (/media/...) address as seen from timeline/p/."""
    if not SITE or re.match(r'https?://', url):
        return url
    if url.startswith('/'):
        return re.sub(r'/timeline$', '', SITE) + url
    return SITE + '/' + url.removeprefix('../')


def original(t):
    """Public copy of the original page: Wayback, the still-live site itself, or none (Common Crawl kept it, no public viewer)."""
    if not t.get('u') or t.get('ext') or t.get('ar') == 'cc':
        return ''
    return t['u'] if t.get('ar') == 'live' else f'https://web.archive.org/web/2022/{t["u"]}'


def video_posters():
    """YouTube id -> the poster of our Internet Archive copy (ia_upload.py sends the .jpg beside the .mp4)."""
    ia = os.path.join(ROOT, 'ia_uploads.jsonl')
    rows = map(json.loads, open(ia, encoding='utf-8')) if os.path.exists(ia) else []
    return {r['id']: f"https://archive.org/download/{r['identifier']}/{r['file'][:-4]}.jpg" for r in rows if r.get('ok')}


def build(timeline):
    tpl = open(os.path.join(TL, 'page.html'), encoding='utf-8').read()
    names, credit = meta()['SOURCES'], meta().get('CREDIT', {})
    out = os.path.join(TL, 'p')
    posters = video_posters()
    os.makedirs(out, exist_ok=True)
    live = {t['n'] + '.html' for t in timeline}
    # a reader who came from a post lands on one story: two or three steps further keep them in the chronicle
    by_md, by_src = {}, {}
    for t in timeline:
        if t.get('k'):
            continue
        if not t.get('e'):
            by_md.setdefault(t['d'][5:], []).append(t)
        by_src.setdefault(t['s'], []).append(t)
    for rows in by_src.values():
        rows.sort(key=lambda t: t['d'])
    at = {t['n']: i for rows in by_src.values() for i, t in enumerate(rows)}
    link = lambda a: f'<li><a href="{a["n"]}.html"><time>{date_h(a["d"], a.get("e", 0))}</time>{html.escape(a["t"])}</a></li>'

    def related(t):
        if t.get('k'):
            return ''
        others = [a for a in by_md.get(t['d'][5:], []) if a['d'][:4] != t['d'][:4]]
        others.sort(key=lambda a: (not a.get('ph'), abs(int(a['d'][:4]) - int(t['d'][:4]))))  # a photo first, the nearest years first
        others = sorted(others[:4], key=lambda a: a['d'])
        rows, i = by_src[t['s']], at[t['n']]
        same = [a for a in rows[max(0, i - 2):i] + rows[i + 1:i + 3]][:3]
        blocks = [(f'{date_h(t["d"]).split(" ", 2)[0]} {date_h(t["d"]).split(" ", 2)[1]} в інші роки', others),
                  (f'Ще з джерела «{html.escape(names.get(t["s"], t["s"]))}»' if not t.get('ext') else 'Поруч у хроніці', same)]
        return ''.join(f'<section class="more"><h2>{h}</h2><ul>{"".join(link(a) for a in rows)}</ul></section>' for h, rows in blocks if rows)

    for f in os.listdir(out):  # pages of articles that are gone must not stay reachable
        if f.endswith('.html') and f not in live:
            os.remove(os.path.join(out, f))
    for t in timeline:
        body = open(os.path.join(TL, 'a', t['n'] + '.html'), encoding='utf-8').read()
        hero, image = '', t.get('i') or '../hero.jpg'
        lead = re.match(r'\s*<img src="([^"]+)"[^>]*>\s*', body)
        if lead:  # lead photo becomes the header image, as in the reader
            hero, image, body = f'<img class="hero" src="{lead.group(1)}" alt="">', lead.group(1), body[lead.end():]
        elif not t.get('i') and (yt := re.search(r'youtube(?:-nocookie)?\.com/embed/([\w-]{11})', body)):
            # no photo but a video: the share card shows its frame, not the site's sea
            image = posters.get(yt.group(1)) or f'https://i.ytimg.com/vi/{yt.group(1)}/hqdefault.jpg'
        if os.path.exists(os.path.join(TL, 'og', t['n'] + '.jpg')):  # a share card the author made for a post (timeline/og/<id>.jpg) wins
            image = f'../og/{t["n"]}.jpg'
        source = t.get('ext') or names.get(t['s'], t['s'])
        # same standard as the reader: the credited source name above the headline links to the original,
        # all links to the source / Wayback sit together at the bottom
        wb = original(t)
        host, src = (t['ext'], t['u']) if t.get('ext') else (credit[t['s']], wb) if t['s'] in credit and wb else (None, None)
        a_ = lambda href, text: f'<a href="{html.escape(href)}" target="_blank" rel="noopener">{text} ↗</a>'
        source_html = a_(src, html.escape(host)).replace('<a ', '<a class="src" ', 1) if host else f'<span class="src">{html.escape(source)}</span>'
        wayback = ' · '.join(x for x in (
            host and a_(src, f'{"Повний текст" if t.get("ext") and not t.get("full") else "Джерело"}: {html.escape(host)}'),
            wb and wb != src and a_(wb, 'Оригінал на сайті' if t.get('ar') == 'live' else 'Оригінал у Wayback Machine')) if x)
        ld = {'@context': 'https://schema.org', '@type': 'NewsArticle', 'headline': t['t'][:110], 'inLanguage': 'uk',
              'publisher': {'@type': 'Organization', 'name': source}, 'image': absolute(image),
              'isPartOf': {'@type': 'WebSite', 'name': 'Приморськ. Хроніка громади'},
              **({'datePublished': t['d']} if t.get('d') and not t.get('e') else {}),
              **({'isBasedOn': t['u']} if t.get('u') else {})}
        fill = {
            'title': html.escape(t['t']), 'desc': html.escape((t.get('x') or t['t'])[:200]), 'image': html.escape(absolute(image)),
            # Cloudflare serves /p/<id>.html at /p/<id> (it redirects the .html form): the canonical address has no extension
            'canonical': f'<link rel="canonical" href="{SITE}/p/{t["n"]}">\n' if SITE else '',
            'jsonld': json.dumps(ld, ensure_ascii=False).replace('</', '<\\/'),
            # published builds link the Wayback original: raw archive copies (full names inside) are not deployed
            # the top link to the original page; none when only Common Crawl kept it (no public copy anywhere)
            'orig': (lambda href: f'<a href="{html.escape(href)}" target="_blank" rel="noopener">'
                                  f'{"Читати в джерелі ↗" if t.get("ext") else "Архівна сторінка ↗"}</a>' if href else '')(
                # a Facebook post (ar: fb) has no archived page anywhere: no button rather than a link to a 404
                '' if t.get('ar') == 'fb' else t['p'] if t.get('ext') or not SITE or not t.get('u') else wb),
            'hero': hero, 'date': t.get('d', ''), 'date_h': date_h(t['d'], t.get('e', 0)) if t.get('d') else '',
            'orig_title': f'<p class="orig-title" lang="ru">Оригінал: {html.escape(t["to"])}</p>' if t.get('to') else '',
            'source': source_html, 'body': body, 'id': t['n'], 'wayback': wayback, 'related': related(t),
        }
        page = re.sub(r'\{\{(\w+)\}\}', lambda m: fill[m.group(1)], tpl)
        with open(os.path.join(out, t['n'] + '.html'), 'w', encoding='utf-8') as f:
            f.write(page)
    extra = build_villages(timeline)
    build_book(timeline)
    if SITE:
        urls = ''.join(f'<url><loc>{SITE}/{u.removesuffix(".html")}</loc></url>\n' for u in extra + [f'p/{t["n"]}.html' for t in timeline])
        with open(os.path.join(TL, 'sitemap.xml'), 'w', encoding='utf-8') as f:
            f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                    f'<url><loc>{SITE}/</loc></url>\n<url><loc>{SITE}/chronicle</loc></url>\n<url><loc>{SITE}/holodomor</loc></url>\n<url><loc>{SITE}/memories</loc></url>\n<url><loc>{SITE}/mykytenko</loc></url>\n<url><loc>{SITE}/book</loc></url>\n{urls}</urlset>\n')
        robots = os.path.join(TL, 'robots.txt')
        lines = [l for l in open(robots, encoding='utf-8').read().splitlines() if not l.startswith('Sitemap:')]
        open(robots, 'w', encoding='utf-8').write('\n'.join(lines + [f'Sitemap: {SITE}/sitemap.xml']) + '\n')
    return len(timeline)


BOOK_TOPICS = {'Культура', 'Спорт', "Історія і пам'ять", 'Молодь і діти', 'Туризм і море'}
PAPERWORK = re.compile(r'^(Рішення|Розпорядження|Проект рішення|ПОВІДОМЛЕННЯ|Аналіз регуляторного|№\d|Оголошення|Повідомлення|До уваги|Увага|Графік|Тендер|Протокол|Порядок денний)', re.I)


SECTION_PAGE = re.compile(r'^(Головна( сторінка)?|Про (нас|мене|школу|блог)|Контакти|Новини|Фотогалерея|Фотоальбом|Наші досягнення|Мій блог|Вітаю на моєму блозі)\W*$', re.I)


def book_score(a):
    """What makes a story book-worthy: a real photo (council banners don't count), a video, a proper text, a place; paperwork ranks lower."""
    return ((4 if a.get('i') and not a.get('bn') else 0) + (1 if a.get('ph') else 0) + (2 if a.get('v') else 0) + (1 if a.get('vl') else 0)
            - (5 if a.get('w') else 0) - (1 if a.get('e') else 0) - (3 if PAPERWORK.search(a['t']) else 0)
            + (1 if set(a.get('c') or []) & BOOK_TOPICS else 0))


# the cover photo of each year's book, chosen by hand (a large, bright, human photo); other years: the best-ranked photo
BOOK_COVERS = {'2011': '0e04fbd5f7', '2012': '6f0d4a253a', '2013': '840e72eb41', '2014': '23634aba6f', '2015': '3b164a7ed6', '2016': 'dc275168f1',
               '2017': '69b015b8ed', '2018': '2e8682480c', '2019': '14f2ef30e7', '2020': 'd1f8d62f1d', '2021': 'fece44410d', '2022': '501da5bb39'}


def img_size(path):
    """(width, height) of a JPEG, PNG or GIF from its header, stdlib only; None if unknown."""
    try:
        with open(path, 'rb') as f:
            head = f.read(26)
            if head[:8] == b'\x89PNG\r\n\x1a\n':
                return int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big')
            if head[:6] in (b'GIF87a', b'GIF89a'):
                return int.from_bytes(head[6:8], 'little'), int.from_bytes(head[8:10], 'little')
            if head[:2] != b'\xff\xd8':
                return None
            f.seek(2)
            while True:
                b = f.read(1)
                while b and b != b'\xff':
                    b = f.read(1)
                while b == b'\xff':
                    b = f.read(1)
                if not b:
                    return None
                marker = b[0]
                if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                    f.read(3)
                    h, w = int.from_bytes(f.read(2), 'big'), int.from_bytes(f.read(2), 'big')
                    return w, h
                f.seek(int.from_bytes(f.read(2), 'big') - 2, 1)
    except OSError:
        return None


def book_photo(t):
    """A story's photo for the book with its pixel size (the layout picks a wide plate, a side photo or a small print by it)."""
    if not t.get('i') or t.get('bn'):
        return '', 0, 0
    size = img_size(os.path.join(ROOT, t['i'].lstrip('/').split('?')[0]).replace('%20', ' ')) or (0, 0)
    return t['i'], size[0], size[1]


def build_book(timeline, per_month=6, min_year=20):
    """timeline/book/<year>.json: the year's best stories month by month, so the Book of the Year loads kilobytes, not all of data.json."""
    out = os.path.join(TL, 'book')
    os.makedirs(out, exist_ok=True)
    news = [t for t in timeline if not t.get('k')]
    years = sorted({t['d'][:4] for t in news})
    index = []
    for y in years:
        items = [t for t in news if t['d'].startswith(y) and not t.get('e') and not SECTION_PAGE.match(t['t'])]  # a blog's front page is not an event
        if len(items) < min_year:
            continue
        topics, villages = {}, set()
        for t in items:
            for c in t.get('c') or []:
                topics[c] = topics.get(c, 0) + 1
            villages.update(t.get('vl') or [])
        ranked = sorted(items, key=book_score, reverse=True)
        by_id = {t['n']: t for t in items}
        cover = by_id.get(BOOK_COVERS.get(y)) or next((t for t in ranked if t.get('i') and not t.get('bn') and set(t.get('c') or []) - {'Влада'}), None) or \
            next((t for t in ranked if t.get('i') and not t.get('bn')), None)
        months = []
        for m in range(1, 13):
            month = [t for t in items if t['d'][5:7] == f'{m:02d}']
            if not month:
                continue
            best = sorted(sorted(month, key=book_score, reverse=True)[:per_month], key=lambda t: t['d'])
            lead = max(best, key=book_score)
            days = [0] * 31
            for t in month:
                days[int(t['d'][8:10]) - 1] += 1
            stories = []
            for t in [lead] + [b for b in best if b is not lead]:
                src, w, h = book_photo(t)
                stories.append({'n': t['n'], 'd': t['d'], 't': t['t'], 'x': t.get('x', '')[:320], 's': t['s'], 'i': src, 'w': w, 'h': h,
                                'v': bool(t.get('v')), 'lead': t is lead})
            months.append({'m': m, 'count': len(month), 'days': days, 'stories': stories})
        book = {'y': y, 'count': len(items), 'videos': sum(1 for t in items if t.get('v')), 'places': len(villages) + 1,
                'topics': sorted(topics.items(), key=lambda kv: -kv[1])[:8], 'cover': cover['i'] if cover else '', 'months': months}
        json.dump(book, open(os.path.join(out, f'{y}.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        index.append({'y': y, 'count': len(items)})
    json.dump(index, open(os.path.join(out, 'index.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    return index


TRANSLIT = dict(zip('абвгґдеєжзиіїйклмнопрстуфхцчшщьюя', 'a b v h g d e ie zh z y i i i k l m n o p r s t u f kh ts ch sh shch  iu ia'.split(' ')))


def slug(name):
    """Village page file name: Ukrainian national transliteration, no apostrophes."""
    w = name.split(' (')[0].lower().replace("'", '')
    w = re.sub(r'(^|\s)([єїйюя])', lambda m: m.group(1) + {'є': 'ye', 'ї': 'yi', 'й': 'y', 'ю': 'yu', 'я': 'ya'}[m.group(2)], w)  # word-initial forms
    return re.sub(r'[^a-z0-9]+', '-', ''.join(TRANSLIT.get(c, c) for c in w)).strip('-')


VILLAGE_TEXT = {'kind': 'паспорт села', 'kicker': 'Паспорт села', 'list_h': 'Хроніка села', 'others_h': 'Інші села громади'}
INST_TEXT = {'kind': 'паспорт закладу', 'kicker': 'Паспорт закладу', 'list_h': 'Хроніка закладу', 'others_h': 'Інші заклади громади'}
# schools and centres: their own site (if it was rescued) + mentions in local sources
# ponytail: "школа №3" also matches a №3 school of another town mentioned in a local article; regional media are excluded
SCHOOL = r'(?:школ\w*|ЗОШ|СЗШ|СШ|гімназі\w*|гимнази\w*)\s*(?:І-ІІІ\s*ст\w*\.?\s*)?№\s?'
INSTITUTIONS = {
    'Школа №1': ((), SCHOOL + r'1(?!\d)'),
    'Гімназія №2': (('school2', 'gymn2_library', 'blog_pe_gymn2'), SCHOOL + r'2(?!\d)'),
    'Школа №3': (('school3', 'school3_health'), SCHOOL + r'3(?!\d)'),
    'Болгарський ліцей': (('licey',), r'болгарськ\w*\s+(?:ліце|лице)|українсько-болгарськ\w*\s+(?:ліце|лице)|регіональн\w*\s+(?:ліце|лице)'),
    'Центр дитячої творчості': (('rcdt', 'cdut'), r'центр\w*\s+дитяч\w*\s+творчост|центр\w*\s+детск\w*\s+творчеств|\bР?ЦДТ\b'),
    'Відділ освіти': (('primroo', 'osvita_otg', 'rmc', 'fisra'), None),
}


def build_villages(timeline):
    """timeline/v/<slug>.html (villages) and timeline/z/<slug>.html (schools, centres): everything the archive holds, no invented facts."""
    import collections
    coords = meta()['GEO']
    by_v = collections.defaultdict(list)
    for t in timeline:
        for v in t.get('vl') or []:
            by_v[v].append(t)
    pages = passports(by_v, 'v', VILLAGE_TEXT, coords, lambda v: f'Жили в селі {v.split(" (")[0]}?')
    json.dump({v: f'v/{slug(v)}.html' for v in by_v}, open(os.path.join(TL, 'villages.json'), 'w'), ensure_ascii=False)  # map popups link here
    by_i = collections.defaultdict(list)
    for t in timeline:
        text = None
        for name, (own, rx) in INSTITUTIONS.items():
            if t['s'] in own:
                by_i[name].append(t)
            elif rx and t['s'] != 'regional':
                text = text or t['t'] + ' ' + open(os.path.join(TL, 'a', t['n'] + '.html'), encoding='utf-8').read()
                if re.search(rx, text, re.I):
                    by_i[name].append(t)
    # school / centre passports stay for local use: not linked from the portal, not in the sitemap (author's call)
    passports(by_i, 'z', INST_TEXT, {}, lambda v: f'Вчились чи працювали тут ({v})?', own={k: v[0] for k, v in INSTITUTIONS.items()})
    json.dump({v: f'z/{slug(v)}.html' for v in by_i}, open(os.path.join(TL, 'institutions.json'), 'w'), ensure_ascii=False)
    return pages


def passports(by_v, sub, text, coords, cta, own=None):
    import collections
    tpl = open(os.path.join(TL, 'village.html'), encoding='utf-8').read()
    names = sorted(by_v, key=lambda v: -len(by_v[v]))
    out = os.path.join(TL, sub)
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(os.path.join(out, f))
    all_geo = [[v.split(' (')[0], coords[v], f'{slug(v)}.html'] for v in names if v in coords]
    e = html.escape
    for v in names:
        items = sorted(by_v[v], key=lambda t: t.get('d', ''), reverse=True)
        short, aka = (v.split(' (') + [''])[:2]
        photos = sorted((t for t in items if t.get('i') and not t.get('bn')), key=lambda t: t['s'] not in (own or {}).get(v, ()))  # own site's photos first
        dated = [t for t in items if t.get('d')]
        years = collections.Counter(t['d'][:4] for t in dated)
        y0, y1 = (min(years), max(years)) if years else ('', '')
        peak = max(years.values()) if years else 1
        bars = ''.join(f'<a href="#y{y}" style="height:{max(4, 100 * years[str(y)] // peak)}%" title="{y}: {years[str(y)]}" aria-label="{y}: {years[str(y)]}"></a>'
                       if years[str(y)] else '<span style="flex:1"></span>' for y in range(int(y0 or 0), int(y1 or -1) + 1))
        topics = collections.Counter(c for t in items for c in t.get('c') or []).most_common(6)
        stat = lambda n, label: f'<div class="stat"><b>{n}</b><span>{label}</span></div>'
        stats = (stat(len(items), 'матеріалів у хроніці') + stat(len(photos), 'з фото') +
                 stat(sum(1 for t in items if t.get('v')), 'з відео') + (stat(f'{y0}–{y1}', 'роки згадок') if y0 else ''))
        row = lambda t: (f'<li><a href="../p/{t["n"]}.html">{f"""<img src="{e(t["i"])}" alt="" loading="lazy">""" if t.get("i") else ""}'
                         f'<span><time datetime="{t.get("d", "")}">{date_h(t["d"], t.get("e", 0)) if t.get("d") else ""}</time>'
                         f'<span class="t">{e(t["t"])}</span></span></a></li>')
        hist = [t for t in items if t.get('k') == 'history']
        groups = collections.defaultdict(list)
        for t in items:
            groups[t.get('d', '')[:4] or 'Без дати'].append(t)
        body = ''.join(f'<div class="year" id="y{y}">{y}</div><ul class="list">{"".join(map(row, g))}</ul>' for y, g in groups.items())
        seen, gallery = set(), []
        for t in photos:
            if t['i'] not in seen and len(gallery) < 12:
                seen.add(t['i'])
                gallery.append(f'<a href="../p/{t["n"]}.html" title="{e(t["t"])}"><img src="{e(t["i"])}" alt="{e(t["t"])}" loading="lazy"></a>')
        desc = f'{short}{f" ({aka})" if aka else ""}, Приморська громада: {len(items)} матеріалів архіву' + (f' за {y0}–{y1} роки' if y0 else '') + ', фото, відео.'
        fill = {
            **text, 'cta': e(cta(v)),
            'name': e(short), 'name_js': json.dumps(short, ensure_ascii=False), 'desc': e(desc),
            'aka': f'<p class="aka">Також: {e(aka.rstrip(")"))}</p>' if aka else '',
            'canonical': f'<link rel="canonical" href="{SITE}/{sub}/{slug(v)}">\n' if SITE else '',
            'image': e(absolute(photos[0]['i'] if photos else '../hero.jpg')), 'hero': e(photos[0]['i'] if photos else '../hero.jpg'),
            'stats': stats, 'years': bars, 'y0': y0, 'y1': y1,
            'topics': ''.join(f'<span class="chip">{e(c)} · {n}</span>' for c, n in topics),
            'history': f'<h2>Історія</h2><ul class="list">{"".join(map(row, hist))}</ul>' if hist else '',
            'gallery': f'<h2>Фото</h2><div class="gallery">{"".join(gallery)}</div>' if len(gallery) >= 3 else '',
            'list': body, 'geo': json.dumps(coords.get(v)),
            'all_geo': json.dumps([g for g in all_geo if g[0] != short], ensure_ascii=False),
            'others': ''.join(f'<a href="{slug(o)}.html">{e(o.split(" (")[0])} · {len(by_v[o])}</a>' for o in names if o != v),
        }
        with open(os.path.join(out, f'{slug(v)}.html'), 'w', encoding='utf-8') as f:
            f.write(re.sub(r'\{\{(\w+)\}\}', lambda m: fill[m.group(1)], tpl))
    return [f'{sub}/{slug(v)}.html' for v in names]


if __name__ == '__main__':
    assert slug("Софіївка (Болгарка, Коларівка)") == 'sofiivka' and slug("Підспір'я") == 'pidspiria' and slug("В'ячеславка") == 'viacheslavka' and slug('Гюнівка') == 'hiunivka' and slug("Юр'ївка") == 'yurivka' and slug('Школа №3') == 'shkola-3'
    assert SECTION_PAGE.match('Головна сторінка') and not SECTION_PAGE.match('Головна подія року')
    assert img_size(os.path.join(TL, 'coat.png')) == (190, 192) and img_size(os.path.join(TL, 'apple-touch-icon.png'))
    assert date_h('2017-03-05') == '5 березня 2017' and date_h('2017-03-05', 90) == '≈ березень 2017' and date_h('2017-03-05', 500) == '≈ 2017'
    print('pages:', build(json.load(open(os.path.join(TL, 'data.json'), encoding='utf-8'))))
