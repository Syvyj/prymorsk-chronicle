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


def build(timeline):
    tpl = open(os.path.join(TL, 'page.html'), encoding='utf-8').read()
    names, credit = meta()['SOURCES'], meta().get('CREDIT', {})
    out = os.path.join(TL, 'p')
    os.makedirs(out, exist_ok=True)
    live = {t['n'] + '.html' for t in timeline}
    for f in os.listdir(out):  # pages of articles that are gone must not stay reachable
        if f.endswith('.html') and f not in live:
            os.remove(os.path.join(out, f))
    for t in timeline:
        body = open(os.path.join(TL, 'a', t['n'] + '.html'), encoding='utf-8').read()
        hero, image = '', t.get('i') or '../hero.jpg'
        lead = re.match(r'\s*<img src="([^"]+)"[^>]*>\s*', body)
        if lead:  # lead photo becomes the header image, as in the reader
            hero, image, body = f'<img class="hero" src="{lead.group(1)}" alt="">', lead.group(1), body[lead.end():]
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
                t['p'] if t.get('ext') or not SITE or not t.get('u') else wb),
            'hero': hero, 'date': t.get('d', ''), 'date_h': date_h(t['d'], t.get('e', 0)) if t.get('d') else '',
            'orig_title': f'<p class="orig-title" lang="ru">Оригінал: {html.escape(t["to"])}</p>' if t.get('to') else '',
            'source': source_html, 'body': body, 'id': t['n'], 'wayback': wayback,
        }
        page = re.sub(r'\{\{(\w+)\}\}', lambda m: fill[m.group(1)], tpl)
        with open(os.path.join(out, t['n'] + '.html'), 'w', encoding='utf-8') as f:
            f.write(page)
    extra = build_villages(timeline)
    if SITE:
        urls = ''.join(f'<url><loc>{SITE}/{u.removesuffix(".html")}</loc></url>\n' for u in extra + [f'p/{t["n"]}.html' for t in timeline])
        with open(os.path.join(TL, 'sitemap.xml'), 'w', encoding='utf-8') as f:
            f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                    f'<url><loc>{SITE}/</loc></url>\n{urls}</urlset>\n')
        robots = os.path.join(TL, 'robots.txt')
        lines = [l for l in open(robots, encoding='utf-8').read().splitlines() if not l.startswith('Sitemap:')]
        open(robots, 'w', encoding='utf-8').write('\n'.join(lines + [f'Sitemap: {SITE}/sitemap.xml']) + '\n')
    return len(timeline)


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
    assert date_h('2017-03-05') == '5 березня 2017' and date_h('2017-03-05', 90) == '≈ березень 2017' and date_h('2017-03-05', 500) == '≈ 2017'
    print('pages:', build(json.load(open(os.path.join(TL, 'data.json'), encoding='utf-8'))))
