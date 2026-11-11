"""The Facebook posts of «Приморськ 24/7» that the author let into the chronicle (step 2 after fb_import.py).

    .venv/bin/python fb_posts.py      # makes the photos (media/fb/<post>/<k>.jpg) and checks the selection; extract_articles.py reads the rest

mirror/fb/posts.json (fb_import.py: texts already masked) and mirror/fb/selection.json (the author's ticks on review/fb.html:
`on` = a record of its own under the prim24 source, `add` = its photos go under the matching prim24 article). Photos are
re-encoded from the export at up to 1600 px with no metadata (Facebook kept the uploader's IP in EXIF). Videos play from
the Internet Archive (fb_videos.py puts them there and lists them in mirror/fb/ia.json); one not uploaded yet is left out.
"""
import html, json, os, re

ROOT = os.path.dirname(os.path.abspath(__file__))
FB = os.path.join(ROOT, 'mirror', 'fb')
EXPORT = os.environ.get('FB_EXPORT', 'facebook-export')  # the folder of a Facebook "Download your information" export
MEDIA = os.path.join(ROOT, 'media', 'fb')


def load():
    if not os.path.exists(os.path.join(FB, 'selection.json')):
        return {}, {'on': [], 'add': []}
    return {p['id']: p for p in json.load(open(os.path.join(FB, 'posts.json'), encoding='utf-8'))}, json.load(open(os.path.join(FB, 'selection.json')))


def photo(p, k):
    """The web copy of a post's k-th photo: /media/fb/<post>/<k>.jpg, made once."""
    rel = f'media/fb/{p["id"]}/{k}.jpg'
    dst = os.path.join(ROOT, rel)
    if not os.path.exists(dst):
        from PIL import Image, ImageOps  # only to make a missing photo: ./build.sh runs on the system python without pillow
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        im = ImageOps.exif_transpose(Image.open(os.path.join(os.path.dirname(EXPORT), p['photos'][k]['src']))).convert('RGB')
        im.thumbnail((1600, 1600))
        im.save(dst, 'JPEG', quality=82, optimize=True)  # a new file: no EXIF, no IP
    return '/' + rel


def figures(p):
    return ''.join(f'<figure><img src="{photo(p, k)}" alt="" loading="lazy"></figure>\n' for k in range(len(p['photos'])))


def players(p):
    ia = json.load(open(os.path.join(FB, 'ia.json'))) if os.path.exists(os.path.join(FB, 'ia.json')) else {}
    out = ''
    for k in range(len(p['videos'])):
        if (src := ia.get(f"{p['id']}-{k}.mp4")):
            out += (f'<figure class="video"><video controls preload="none" playsinline poster="{src[:-4]}.jpg" src="{src}"></video>'
                    '<figcaption>Відео зі сторінки «Приморськ 24/7» у Facebook · копія в Internet Archive</figcaption></figure>\n')
    return out


def body(p):
    """The post as an article: its paragraphs, then its videos and photos."""
    paras = [re.sub(r'\n', '<br>', html.escape(b.strip())) for b in re.split(r'\n\s*\n', p['text']) if b.strip()]
    return ''.join(f'<p>{b}</p>\n' for b in paras) + players(p) + figures(p)


def records():
    """(post, body html) for each post the author let in, oldest first."""
    posts, sel = load()
    return [(posts[i], body(posts[i])) for i in sorted(sel['on'], key=lambda i: posts[i]['date']) if i in posts]


def extra_photos():
    """{chronicle id of a prim24 article: html of the photos the matching posts add}"""
    posts, sel = load()
    out = {}
    for i in sel['add']:
        p = posts.get(i)
        if p and p['photos'] and p['match'] and p['match'].get('n'):
            out[p['match']['n']] = out.get(p['match']['n'], '') + figures(p)
    return out


if __name__ == '__main__':
    recs = records()
    extra = extra_photos()
    print(len(recs), 'posts,', sum(len(p['photos']) for p, _ in recs), 'photos,', sum(1 for p, _ in recs if p['videos']), 'with videos (not yet);',
          len(extra), 'prim24 articles get photos')
