"""Assemble the folder that goes online: the portal shell, article pages, the photos they show — nothing private.

    SITE_URL=https://example.org python3 publish.py   # -> $PRYM_PUBLISH (default ../prymorsk-publish) (old copy replaced)

The site root is this folder: index.html at /, photos at /media/... (the paths in the pages are absolute).
Never copied: raw archive copies (archive_*, mirror/: full names inside), a/ fragments (the reader reads p/),
z/ school passports (not public, author's call), the mockup, caches, the video drive (videos play from the Internet Archive).
"""
import hashlib, json, os, re, shutil, subprocess, sys
import paths
from urllib.parse import quote, unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
TL = os.path.join(ROOT, 'timeline')
OUT = paths.PUBLISH
SHELL = ['index.html', 'chronicle.html', 'book.html', 'meta.js', 'chronicle.json', 'home.json', 'videos.json', 'villages.json', 'hero.jpg', 'hero-sm.jpg',
         'robots.txt', '404.html', 'sitemap.xml', 'holodomor.html', 'holodomor.json', 'holodomor-og.jpg', 'holodomor-village.webp', 'holodomor-shoes.webp', 'holodomor-book.webp', 'holodomor-candle.webp', 'memories.html', 'memories-map.json', 'memories-og.jpg', 'mykytenko.html', 'mykytenko-og.jpg', 'donate-qr.svg', 'favicon.svg', 'favicon.ico', 'apple-touch-icon.png', 'ngo-logo.png', 'coat.png', 'coat-hi.png', 'fix.js', 'human.js', 'share.js', '_headers']
DIRS = ['p', 'v', 'export', 'book', 'day', 'maps', 'fonts', 'mykytenko', 'og', 'search']
LIMIT_FILES, LIMIT_SIZE = 20000, 25 * 2**20  # Cloudflare Pages: files per deploy, size of one file


def media_refs(text):
    return {unquote(m) for m in re.findall(r'''(?<![\w.])/(media/[^"'\s)<>]+)''', text)}


LATIN = {'а': ['a'], 'б': ['b'], 'в': ['v'], 'г': ['g', 'h'], 'ґ': ['g'], 'д': ['d'], 'е': ['e'], 'є': ['e', 'je', 'ye', 'ie'], 'ж': ['zh'],
         'з': ['z'], 'и': ['i', 'y'], 'і': ['i'], 'ї': ['i', 'ji', 'yi'], 'й': ['j', 'y', 'i'], 'к': ['k'], 'л': ['l'], 'м': ['m'], 'н': ['n'],
         'о': ['o'], 'п': ['p'], 'р': ['r'], 'с': ['s'], 'т': ['t'], 'у': ['u'], 'ф': ['f'], 'х': ['kh', 'h'], 'ц': ['c', 'ts'], 'ч': ['ch'],
         'ш': ['sh'], 'щ': ['shh', 'shch', 'sch'], 'ь': [''], 'ю': ['ju', 'yu', 'iu'], 'я': ['ja', 'ya', 'ia'], 'ы': ['y'], 'э': ['e'],
         'ё': ['e', 'jo', 'yo'], 'ъ': [''], "'": ['']}


def latin_names():
    """First names of names.py as file names spell them: «Ілля» -> illja, illya, illia."""
    import names
    out = set()
    for n in names.FIRST_SET:
        forms = ['']
        for ch in n.lower():
            forms = [f + v for f in forms for v in LATIN.get(ch, [ch])][:64]
        out |= {f for f in forms if len(f) >= 4}
    return out


def named(filename, first):
    """A file name with a person in it: a first name among other words (stasjuk_marina_primorska_tg.jpg)."""
    words = [w for w in re.split(r'[^a-z]+', os.path.splitext(filename)[0].lower()) if w]
    return len(words) > 1 and any(w in first for w in words)


def hide_names(out):
    """Published photos whose file name carries a person's name get a neutral name; every page and data file follows.
    ponytail: a first name spelled in Latin letters is the only sign; a surname alone or an odd spelling stays."""
    first, renamed = latin_names(), {}
    for dp, _, fs in os.walk(os.path.join(out, 'media')):
        for f in fs:
            if named(f, first):
                renamed[f] = 'f-' + hashlib.md5(f.encode()).hexdigest()[:10] + os.path.splitext(f)[1].lower()
                os.rename(os.path.join(dp, f), os.path.join(dp, renamed[f]))
    if renamed:
        rx = re.compile('/(' + '|'.join(sorted({re.escape(k) for f in renamed for k in (f, quote(f))}, key=len, reverse=True)) + r')(?=["\s)?&<\\]|$)')
        for dp, _, fs in os.walk(out):
            for f in fs:
                if f.endswith(('.html', '.json', '.xml', '.js')):
                    text = open(os.path.join(dp, f), encoding='utf-8').read()
                    new = rx.sub(lambda m: '/' + renamed[unquote(m.group(1))], text)
                    if new != text:
                        open(os.path.join(dp, f), 'w', encoding='utf-8').write(new)
    return renamed


def main():
    site = os.environ.get('SITE_URL', '').rstrip('/')
    if not site.startswith('https://'):
        sys.exit('SITE_URL=https://… is needed: canonical links, sitemap and the Internet Archive videos depend on it')
    env = {**os.environ, 'SITE_URL': site}
    # the published flavour of the generated files, then the local one back (local preview keeps working)
    for cmd in (['pages.py'], ['video_download.py', '--index']):
        subprocess.run([sys.executable, *cmd], cwd=ROOT, env=env, check=True)
    try:
        if os.path.exists(OUT):
            shutil.rmtree(OUT)
        os.makedirs(OUT)
        media = set()
        for f in SHELL:
            shutil.copy2(os.path.join(TL, f), OUT)
            if f.endswith(('.html', '.json')):
                media |= media_refs(open(os.path.join(TL, f), encoding='utf-8').read())
        for d in DIRS:
            shutil.copytree(os.path.join(TL, d), os.path.join(OUT, d))
            for dp, _, fs in os.walk(os.path.join(TL, d)):
                media |= {m for f in fs if f.endswith('.html') for m in media_refs(open(os.path.join(dp, f), encoding='utf-8').read())}
        # /chronicle is a copy of the home page: its own address and title for search engines (the page sets the same title by script)
        ch = os.path.join(OUT, 'chronicle.html')
        page = open(ch, encoding='utf-8').read()
        assert '<link rel="canonical" href="https://prym.mydom.website/">' in page and '<title>Приморськ. Хроніка громади</title>' in page
        page = page.replace('<link rel="canonical" href="https://prym.mydom.website/">', f'<link rel="canonical" href="{site}/chronicle">') \
                   .replace('<title>Приморськ. Хроніка громади</title>', '<title>Уся хроніка · Приморськ. Хроніка громади</title>')
        open(ch, 'w', encoding='utf-8').write(page)
        missing = 0
        for m in sorted(media):  # only the photos and files the pages show
            src = os.path.join(ROOT, m.split('?')[0])
            if os.path.isfile(src):
                os.makedirs(os.path.dirname(os.path.join(OUT, m)), exist_ok=True)
                shutil.copy2(src, os.path.join(OUT, m.split('?')[0]))
            else:
                missing += 1
        print(f'photos renamed (a name in the file name): {len(hide_names(OUT))}')
        check(missing)
    finally:
        local = {k: v for k, v in os.environ.items() if k != 'SITE_URL'}
        for cmd in (['pages.py'], ['video_download.py', '--index']):
            subprocess.run([sys.executable, *cmd], cwd=ROOT, env=local, check=True)
        if os.path.exists(os.path.join(TL, 'sitemap.xml')):
            os.remove(os.path.join(TL, 'sitemap.xml'))


def check(missing):
    files = [os.path.join(dp, f) for dp, _, fs in os.walk(OUT) for f in fs]
    big = [f for f in files if os.path.getsize(f) > LIMIT_SIZE]
    raw = [f for f in files if f.endswith('.html') and re.search(r'(?:href|src)="/(?:archive_|mirror/)', open(f, encoding='utf-8').read())]
    size = sum(os.path.getsize(f) for f in files) / 2**20
    print(f'{OUT}: {len(files)} files, {size:.0f} MB; photos not found: {missing}')
    assert len(files) < LIMIT_FILES, f'{len(files)} files: over the hosting limit'
    assert not big, f'files over 25 MB: {big[:3]}'
    assert not raw, f'pages that point into the raw archive copies: {raw[:3]}'
    private = [d for d in ('a', 'z', 'mirror', 'private') if os.path.exists(os.path.join(OUT, d))] + \
              [f for f in files if re.search(r'\.(?:docx?|xlsx?|rtf|zip|rar)$', f, re.I) or  # photos of raw pages (media/_pages) are fine
               '/archive_' in f and not re.search(r'\.(?:jpe?g|png|gif|webp)$', f, re.I)]
    assert not private, f'never published: {private[:3]}'
    sitemap = open(os.path.join(OUT, 'sitemap.xml'), encoding='utf-8').read()  # a page added to SHELL but not to the sitemap in pages.py
    unlisted = [f for f in os.listdir(OUT) if f.endswith('.html') and f not in ('404.html', 'index.html') and f'/{f[:-5]}</loc>' not in sitemap]
    assert not unlisted, f'pages missing from the sitemap (pages.py): {unlisted}'
    first = latin_names()
    assert not [f for f in files if '/media/' in f and named(os.path.basename(f), first)], 'a name in a photo file name'
    leaks = privacy_leaks(os.path.join(OUT, 'p'))
    assert not leaks, f'{len(leaks)} article pages with a full name, a phone or a private e-mail, e.g. ' + '; '.join(leaks[:5])


def privacy_leaks(folder):
    """Article pages that still show what names.py / mask_private hide: a first name with a full surname, a mobile number,
    a private e-mail. A pair counts only if names.shorten would change it in its own context (streets, famous people stay)."""
    import html as html_, names, clean_article
    pair = re.compile(rf'\b({names.WORD})[ \xa0]+({names.WORD}|{names.CAPS})\b(?![а-яіїєґ])')
    inline = r'</?(?:br|strong|em|b|i|a|span|u)\b[^>]*>'  # inside a line: a space; any other tag ends the line
    out = []
    for f in sorted(os.listdir(folder)):
        page = open(os.path.join(folder, f), encoding='utf-8').read()
        page = re.sub(r'(?s)<script\b.*?</script>', '', page)
        text = html_.unescape(re.sub(r'<[^>]+>', '\n', re.sub(inline, ' ', page)))
        found = [m.group(0) for m in clean_article.MOBILE.finditer(text)] + \
                [m.group(0) for m in clean_article.EMAIL.finditer(text) if not clean_article.PUBLIC_MAIL.search(m.group(0))]
        for m in pair.finditer(text):
            if bool(names.first_name(m.group(1))) != bool(names.first_name(m.group(2))) and not names.PATRONYMIC.match(m.group(2)):
                seg = text[max(0, m.start() - 25):m.end() + 25]
                if m.group(0) not in names.shorten(seg):
                    found.append(m.group(0))
        if found:
            out.append(f'{f}: {", ".join(found[:3])}')
    return out


if __name__ == '__main__':
    assert media_refs('<img src="/media/a%20b.jpg"> url(/media/x.png)') == {'media/a b.jpg', 'media/x.png'}
    assert media_refs("<img src='/media/a.jpg' srcset=\"/media/b.jpg 1x, /media/c.jpg 2x\"> https://x.org/media/no.jpg") == {'media/a.jpg', 'media/b.jpg', 'media/c.jpg'}
    _first = latin_names()
    assert named('sadovij_budinochok_stasjuk_marina_primorskij_cdjut.jpg', _first) and named('10_slivin_jaroslav.jpg', _first)
    assert not named('marina.jpg', _first) and not named('dsc08914.jpg', _first) and not named('more_i_step_2019.jpg', _first)
    main()
