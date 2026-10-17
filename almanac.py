"""The 2021 almanac of the Prymorsk local historians' union (ГО «Спілка краєзнавців Приморська») as articles.

    .venv/bin/python almanac.py path/to/almanac.pdf   # needs pypdf + pillow (.venv only)

Writes almanac/almanac.json (read by extract_articles.py with plain Python) and the photos to media/almanac/.
The author (founder of the union) asked for these articles to replace the history block (2026-10).
"""
import html, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'almanac')
MEDIA = os.path.join(ROOT, 'media', 'almanac')
DATE = '2021-09-15'
# wide character margin: justified lines wrapped around a photo stay one line, not loose words
PARAMS = None  # the edition went to print (PDF metadata)
# (slug, Ukrainian title, original title if Russian, author, first and last PDF page; printed page = PDF page - 2)
ARTICLES = [
    ('200-rokiv', 'Чи 200 років тобі, моє місто?', '', 'С. В. Дульцев', 5, 6),
    ('nohaitsi', 'Ногайці в історії міста Ногайськ', 'Ногайцы в истории города Ногайск', 'В. В. Грибовський', 7, 23),
    ('frantsuzy', 'Французи їдуть у Приазов\'я', 'Французы едут в Приазовье', 'С. В. Дульцев', 24, 28),
    ('denysov', 'Як генерал Денисов ногайську землю отримав', '', 'С. В. Дульцев', 29, 30),
    ('troitska-tserkva', 'До історії Свято-Троїцької церкви села Обіточне: 1808–1917',
     'К истории Свято-Троицкой церкви села Обиточное: 1808–1917', 'Т. Д. Порохня', 31, 44),
    ('shliakh-do-khramu', 'Довгий шлях до храму', '', 'С. В. Дульцев', 45, 47),
    ('kosovski', 'Історія родини священиків Косовських', 'История семьи священников Косовских', 'Т. Д. Порохня', 48, 55),
    ('karnafel', 'Жила в Ногайську родина Карнафель', 'Жила в Ногайске семья Карнафель', 'Т. Д. Порохня', 56, 67),
    ('dobra-pamiat', 'Життя, що залишило добру пам\'ять', 'Жизнь, оставившая добрую память', 'Т. Д. Порохня', 68, 76),
]
END = re.compile(r'[.!?:;…»"”)\]]$')


def tidy(t):
    t = re.sub(r'[ \t\xa0]{2,}', ' ', t)
    t = re.sub(r'(?<=[а-яіїєґa-z])-\n(?=[а-яіїєґa-z])', '', t)  # "Гри-\nбовський"
    t = re.sub(r'\s*\n\s*', ' ', t)
    t = re.sub(r'\s+([,.;:!?)])', r'\1', t)
    t = re.sub(r'(?<=[а-яіїєґ]{2})([.!?])(?=[А-ЯІЇЄҐ][а-яіїєґ])', r'\1 ', t)  # "проблему.У 1831" (not initials "М.С.Воронцов")
    return re.sub(r'([,;])(?=[А-ЯІЇЄҐа-яіїєґA-Za-z])', r'\1 ', t).strip()


def box_text(box, body_size):
    """The box's text; footnote marks (smaller digits inside body text) as <sup>."""
    from pdfminer.layout import LTChar
    out = []
    for line in box:
        for c in line:
            ch = c.get_text()
            small = isinstance(c, LTChar) and c.size < body_size * 0.8 and ch.isdigit()
            out.append(f'\x01{ch}\x02' if small else ch)
    t = tidy(html.escape(''.join(out)))
    return re.sub(r'\x02\x01', '', t).replace('\x01', '<sup>').replace('\x02', '</sup>')


def kind(box):
    """body | heading | caption | note | skip, by the typesetting (InDesign styles of this edition)."""
    from pdfminer.layout import LTChar
    chars = [c for line in box for c in line if isinstance(c, LTChar) and c.get_text().strip()]
    if not chars:
        return 'skip', 0
    size = sorted(c.size for c in chars)[len(chars) // 2]
    fonts = ' '.join({c.fontname for c in chars})
    if 'Minion' in fonts or 'Arial-Bold' in fonts or size >= 16:
        return 'skip', size  # page number, rubric ("Духовні джерела"), the headline
    if size <= 10.5:
        return ('caption' if 'Bold' in fonts else 'note'), size
    if 'Bold' in fonts:
        return ('byline' if 'Italic' in fonts else 'heading'), size
    return 'body', size


def article_html(pages, photos_by_page):
    from pdfminer.layout import LTTextBoxHorizontal
    blocks, notes = [], []
    for number, layout in pages:
        boxes = sorted((b for b in layout if isinstance(b, LTTextBoxHorizontal)), key=lambda b: (-round(b.y1), b.x0))
        body = 12.0
        for b in boxes:
            k, size = kind(b)
            if k in ('skip', 'byline'):
                continue
            t = box_text(b, size if k == 'note' else body)  # in a footnote only its own number is small
            if not t or re.fullmatch(r'\d{1,3}', t):
                continue
            if re.fullmatch(r'(?i)(источни\w*|джерела)\s+(и|і|та)\s+(литератур\w*|література):?', t):
                t, k = 'Джерела та література', 'heading'
            if k == 'heading' and (len(t) > 120 or '<sup>' in t or '[' in t):
                k = 'body'  # a whole paragraph set in bold for emphasis
            if k == 'heading':
                blocks.append(f'<h3>{t}</h3>')
            elif k == 'caption':
                blocks.append(f'<p class="caption"><em>{t}</em></p>')
            elif k == 'note':
                notes.append(f'<li>{t}</li>' if not re.match(r'(Джерела|Источники|ИСТОЧНИКИ|Література|Литература)', t, re.I) else f'</ol><h3>{t}</h3><ol>')
            elif blocks and blocks[-1].startswith('<p>') and not END.search(re.sub(r'<[^>]+>', '', blocks[-1][3:-4])) and t[:1].islower():
                blocks[-1] = blocks[-1][:-4] + ' ' + t + '</p>'  # a paragraph that runs on past a photo or a page break
            else:
                blocks.append(f'<p>{t}</p>')
        blocks += [f'<figure><img src="/{src}" alt="" loading="lazy"></figure>' for src in photos_by_page.get(number, [])]
    if notes:
        blocks.append('<h3>Примітки та джерела</h3><ol class="notes">' + ''.join(notes) + '</ol>')
    return re.sub(r'<ol class="notes"></ol>|<ol></ol>', '', '\n'.join(blocks))


def main(pdf):
    from pypdf import PdfReader
    from pdfminer.high_level import extract_pages
    reader = PdfReader(pdf)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(MEDIA, exist_ok=True)
    cover = reader.pages[0].images[0].image.convert('RGB')
    cover.thumbnail((900, 1300))
    cover.save(os.path.join(MEDIA, 'cover.jpg'), quality=85)
    shutil.copyfile(pdf, os.path.join(MEDIA, 'almanakh-2021.pdf'))
    items = []
    for slug, title, original, author, a, b in ARTICLES:
        photos = {}
        layouts = list(zip(range(a, b + 1), extract_pages(pdf, page_numbers=range(a - 1, b), laparams=PARAMS)))
        for page in range(a, b + 1):
            p = reader.pages[page - 1]
            for k, im in enumerate(p.images):
                try:
                    img = im.image.convert('RGB')
                except Exception:
                    continue
                if min(img.size) < 150:
                    continue
                img.thumbnail((1400, 1400))
                rel = f'media/almanac/{slug}-{page}-{k}.jpg'
                img.save(os.path.join(ROOT, rel), quality=85)
                photos.setdefault(page, []).append(rel)
        body = article_html(layouts, photos)
        items.append({'slug': slug, 'title': title, 'original': original, 'author': author, 'date': DATE,
                      'pages': f'{a - 2}–{b - 2}', 'html': body})
        print(f'{slug}: {len(re.findall("<p>", body))} paragraphs, {len(re.findall("<h3>", body))} headings, '
              f'{sum(len(v) for v in photos.values())} photos')
    json.dump(items, open(os.path.join(OUT, 'almanac.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    from pdfminer.layout import LAParams
    PARAMS = LAParams(line_margin=0.5, char_margin=20.0, word_margin=0.1)
    assert tidy('Гри-\nбовський  сказав ,що') == 'Грибовський сказав, що'
    main(sys.argv[1])
