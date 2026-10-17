"""Assemble the folder that goes online: the portal shell, article pages, the photos they show — nothing private.

    SITE_URL=https://example.org python3 publish.py   # -> $PRYM_PUBLISH (default ../prymorsk-publish) (old copy replaced)

The site root is this folder: index.html at /, photos at /media/... (the paths in the pages are absolute).
Never copied: raw archive copies (archive_*, mirror/: full names inside), a/ fragments (the reader reads p/),
z/ school passports (not public, author's call), the mockup, caches, the video drive (videos play from the Internet Archive).
"""
import json, os, re, shutil, subprocess, sys
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
TL = os.path.join(ROOT, 'timeline')
OUT = os.environ.get('PRYM_PUBLISH', '../prymorsk-publish')
SHELL = ['index.html', 'book.html', 'meta.js', 'data.json', 'videos.json', 'villages.json', 'hero.jpg', 'hero-sm.jpg',
         'robots.txt', '404.html', 'sitemap.xml', 'donate-qr.svg', 'favicon.svg', 'favicon.ico', 'apple-touch-icon.png', 'ngo-logo.png', 'coat.png', 'fix.js', 'share.js']
DIRS = ['p', 'v', 'export']
LIMIT_FILES, LIMIT_SIZE = 20000, 25 * 2**20  # Cloudflare Pages: files per deploy, size of one file


def media_refs(text):
    return {unquote(m) for m in re.findall(r'["(]/(media/[^"\s)]+)', text)}


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
        missing = 0
        for m in sorted(media):  # only the photos and files the pages show
            src = os.path.join(ROOT, m.split('?')[0])
            if os.path.isfile(src):
                os.makedirs(os.path.dirname(os.path.join(OUT, m)), exist_ok=True)
                shutil.copy2(src, os.path.join(OUT, m.split('?')[0]))
            else:
                missing += 1
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


if __name__ == '__main__':
    assert media_refs('<img src="/media/a%20b.jpg"> url(/media/x.png)') == {'media/a b.jpg', 'media/x.png'}
    main()
