"""Turn an archived article body into clean HTML: text, headings, lists, tables, existing photos, YouTube.

Drops share buttons, reactions, view counters, print/e-mail links, prev/next, author boxes, related posts, ads,
and captions of photos that were not recovered.
"""
import os, re, html, shutil
from html.parser import HTMLParser
from urllib.parse import unquote, quote

ROOT = os.path.dirname(os.path.abspath(__file__))
VOID = {'br', 'img', 'hr', 'input', 'meta', 'link', 'source', 'wbr', 'area', 'col', 'embed', 'param', 'track'}
KEEP = {'hr', 'p', 'br', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'blockquote', 'strong', 'em', 'a', 'img', 'figure',
        'figcaption', 'table', 'thead', 'tbody', 'tr', 'td', 'th', 'iframe'}
RENAME = {'b': 'strong', 'i': 'em', 'h1': 'h3', 'h5': 'h4', 'h6': 'h4', 'div': 'p'}
DROP_TAGS = {'script', 'style', 'noscript', 'noindex', 'form', 'button', 'select', 'textarea', 'svg', 'footer', 'aside', 'nav'}
# class / id tokens of widgets (Jetpack sharing & likes, FeelBox, AddThis, author box, related posts, meta line)
DROP_CLASS = re.compile(r'^(sharedaddy|sd-.*|robots-nocontent|jp-relatedposts.*|printfriendly|pf-button.*|likes-widget.*|'
                        r'post-likes-widget.*|feelbox.*|add_?this.*|author_box.*|v-s|d-t|posted-on|byline|entry-meta|'
                        r'entry-footer|share-.*|sharing-.*|myGrid|wp-block-buttons|yarpp.*|pagenav|pager|navigation)$', re.I)
CAPTION_CLASS = re.compile(r'^(text_photo|wp-caption-text|gallery-caption)$')
# whole paragraphs/list items that are site furniture
JUNK_LINE = re.compile(r'^((?:english|polish|russian|ukrainian)(?:\s+(?:english|polish|russian|ukrainian))*|'  # translator widget
                       r'поделиться ссылкой:?|поділитися( цим| з друзями)?:?|share this:?|like this:?|like loading\.*|'
                       r'подобається( це:| завантаження…)?|чи сподобався вам цей матеріал\??|у захваті|чудово|нічого собі|'
                       r'сумно|злість|print|печать|друк( матеріалу)?|e-?mail|по электронной почте|facebook|twitter|google|'
                       r'telegram|pocket|pinterest|vk\.com|більше|попередня|наступна|перегляди:\s*\d+|просмотров:\s*\d+|'
                       r'про автора|переглянути всі матеріали автора|останні матеріали|no biography available at this time|'
                       r'visit the author’s website|реклама|також вам буде цікаво:?|click to share on .*|натисніть, щоб.*|'
                       r'помилка в тексті\?.*|якщо ви помітили помилку.*|всього коментарів:.*|'
                       r'присоединяйтесь к нам в facebook и вконтакте|понравилась статья\? тогда поддержи нас, жми:|'
                       r'фото: pexels\.com|tweet|розповідай друзям:?|расскажи друзьям:?|'
                       r'\d{1,2}\.\d{2}\.\d{4}\s*\|\s*автор:.*|автор: admin|оставить комментарий|комментарии закрыты\.?)$', re.I)
# links to private people's social profiles (facebook events/groups stay)
PERSONAL_PROFILE = re.compile(r'//(www\.|m\.)?(vk\.com|ok\.ru|instagram\.com|facebook\.com/(?!events/|groups/))', re.I)
# contact lines like "Костянтин Осадчий – ВК та ФБ"
CONTACT_LINE = re.compile(r"^((\S+\s+){1,2}\S+\s*[–—-]\s*(ВК|ФБ|VK|FB)(\s*(та|і|,)\s*(ВК|ФБ|VK|FB))*\s*)+$")
# photo credits: meaningless once the photo itself is gone
CREDIT_LINE = re.compile(r'^(фото|ілюстрація|иллюстрация|джерело фото|источник фото)(\s+(з сайту|с сайта)\s*|\s*[:—–-]\s*)\S.{0,80}$', re.I)


class Cleaner(HTMLParser):
    def __init__(self, cls, page_dir, nth=0):
        super().__init__(convert_charrefs=True)
        self.cls, self.page_dir, self.nth = cls, page_dir, nth  # nth: which occurrence of the container to take
        self.depth = 0          # depth inside the body container
        self.done = False
        self.skip = 0           # >0 while inside a dropped subtree
        self.stack = []         # (tag, emitted_tag|None, dropped?)
        self.out = []
        self.last_img_ok = True
        self.seen = []          # every photo address inside the container (mirror_images.py downloads them)

    def local_img(self, src):
        if not src or src.startswith('data:'):
            return None
        if src.startswith('/media/'):
            f = os.path.join(ROOT, unquote(src[1:].split('?')[0]))
        elif not re.match(r'(https?:)?//', src):
            f = os.path.join(self.page_dir, unquote(src.split('?')[0]))
        else:
            return None
        if not (os.path.isfile(f) and os.path.getsize(f) > 2000):
            return None
        return published(f)

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        a = dict(attrs)
        if not self.depth:
            if self.cls in (a.get('class') or '').split():
                if self.nth:
                    self.nth -= 1
                    return
                self.depth = 1
                self.stack.append((tag, None, False))  # the container itself; done when it closes
            return
        tokens = (a.get('class') or '').split() + ([a['id']] if a.get('id') else [])
        root_drop = not self.skip and (tag in DROP_TAGS or any(DROP_CLASS.match(t) for t in tokens) or
                                       (any(CAPTION_CLASS.match(t) for t in tokens) and not self.last_img_ok))
        if tag not in VOID:
            self.depth += 1
            self.stack.append((tag, None, root_drop))
            if root_drop:
                self.skip += 1
        if self.skip:
            return
        name = RENAME.get(tag, tag)
        if tag == 'img':
            self.seen.append(a.get('data-src') or a.get('src') or '')
            src = self.local_img(a.get('src'))
            self.last_img_ok = bool(src)
            if src:
                self.out.append(f'<img src="{src}" alt="{html.escape(a.get("alt") or "")}" loading="lazy">')
            return
        if tag == 'br':
            self.out.append('<br>')
            return
        if tag == 'iframe':
            src = a.get('src') or ''
            m = re.search(r'youtube(?:-nocookie)?\.com/embed/([\w-]{11})', src)
            if m:
                self.out.append(f'<iframe src="https://www.youtube-nocookie.com/embed/{m.group(1)}" loading="lazy" allowfullscreen>')
                self.stack[-1] = (tag, 'iframe', False)
            return
        if name not in KEEP:
            return
        attr = ''
        if name == 'a':
            href = a.get('href') or ''
            if not re.match(r'https?://', href) or re.search(r'share=|share\.php|/#print|mailto', href) or PERSONAL_PROFILE.search(href):
                return  # unwrap internal/dead/share links and personal social profiles, keep their text
            attr = f' href="{html.escape(href)}" rel="noopener" target="_blank"'
        if name in ('td', 'th') and a.get('colspan'):
            attr = f' colspan="{html.escape(a["colspan"])}"'
        self.out.append(f'<{name}{attr}>')
        self.stack[-1] = (tag, name, False)

    def handle_endtag(self, tag):
        if tag in VOID or not self.depth or self.done:
            return
        # tolerate broken nesting: ignore stray closers, otherwise pop until the matching open tag
        if not any(t == tag for t, _, _ in self.stack):
            return
        while self.stack:
            t, emitted, dropped = self.stack.pop()
            self.depth -= 1
            if dropped:
                self.skip -= 1
            elif emitted and not self.skip:
                self.out.append(f'</{emitted}>')
            if t == tag:
                break
        if not self.stack:
            self.done = True

    def handle_data(self, data):
        if self.depth and not self.skip and not self.done:
            data = data.replace('¬†', ' ').replace('¬', '')  # mangled nbsp (C2 A0 read as Mac Roman)
            data = re.sub(r'(Переглядів|Перегляди|Просмотров):\s*\d+\.?\s*', '', data)
            data = SHORTCODE.sub('', data)
            data = re.sub(r'\b\d{1,2}\.\d{2}\.\d{4}\s*\|\s*Автор:\s*\S+', '', data)  # primorsk.in.ua byline
            self.out.append(html.escape(data))


# leftover WordPress/Joomla shortcodes whose plugins are gone: [yjsgfa name="fa fa-search"], [tab_item title="…"], [/tab]
SHORTCODE = re.compile(r'\[/?[a-z_][\w-]*(?:\s[^\]]{0,300})?\]')


BLOCK = r'(?:p|li|h2|h3|h4|figcaption|td|th|blockquote)'


def published(f):
    """Site path of a local photo; one under a raw archive copy (never published) is copied into media/ first."""
    rel = os.path.relpath(f, ROOT)
    if rel.startswith('archive_'):
        pub = os.path.join('media', '_pages', rel)
        if not os.path.exists(os.path.join(ROOT, pub)):
            os.makedirs(os.path.dirname(os.path.join(ROOT, pub)), exist_ok=True)
            shutil.copyfile(f, os.path.join(ROOT, pub))
        rel = pub
    return '/' + quote(rel)


def tidy(h):
    h = SHORTCODE.sub('', h)
    # the site editor's own selection markers, saved as visible text
    h = re.sub(r'&lt;span data-mce-type=&quot;bookmark&quot;.*?&lt;/span&gt;|\ufeff', '', h, flags=re.S)
    h = balance_p(h)
    # "17.03.2009 | Автор: admin" byline, possibly split by tags
    h = re.sub(r'\b\d{1,2}\.\d{2}\.\d{4}\s*\|\s*(?:<[^>]+>\s*)*Автор:\s*(?:<[^>]+>\s*)*[^<\s]+(?:\s*</[^>]+>)*', '', h)  # again on the joined HTML: a shortcode can be split across text chunks
    h = re.sub(r'<p>\s*</p>|<p>(?=\s*<p>)', '', h)
    # drop junk paragraphs / items (compare on visible text)
    has_img = '<img' in h
    def junk(m):
        text = html.unescape(re.sub(r'<[^>]+>', '', m.group(0))).strip()
        return '' if JUNK_LINE.match(text) or CONTACT_LINE.match(text) or (not has_img and CREDIT_LINE.match(text)) else m.group(0)
    for _ in range(2):
        # innermost blocks only: content may not open another block
        h = re.sub(rf'<({BLOCK})\b[^>]*>(?:(?!<{BLOCK}[\s>]).)*?</\1>', junk, h, flags=re.S)
    # remove now-empty containers, repeatedly
    for _ in range(4):
        h = re.sub(r'<(p|li|ul|ol|figure|figcaption|blockquote|strong|em|h[234]|a[^>]*)>[\s\xa0]*(<br>[\s\xa0]*)*</(p|li|ul|ol|figure|figcaption|blockquote|strong|em|h[234]|a)>', '', h)
    # layout tables (every row has a single cell) are page scaffolding, not data: unwrap them
    def unwrap(m):
        rows = re.findall(r'<tr>(.*?)</tr>', m.group(0), re.S)
        if rows and all(len(re.findall(r'<t[dh][\s>]', r)) <= 1 for r in rows):
            return re.sub(r'</?(table|thead|tbody|tr|td|th)\b[^>]*>', '', m.group(0))
        return m.group(0)
    for _ in range(3):
        h = re.sub(r'<table>(?:(?!<table>).)*?</table>', unwrap, h, flags=re.S)
    h = re.sub(r'<p>(\s|<br>|&nbsp;)*</p>', '', h)  # empty paragraphs left by removed junk
    h = re.sub(r'^(\s|<br>|</p>)+', '', h)
    h = re.sub(r'(<br>\s*){3,}', '<br><br>', h)
    h = re.sub(r'[ \t\xa0]{2,}', ' ', h)
    h = re.sub(r'\n\s*\n+', '\n', h)
    return h.strip()


PARA_BREAKER = re.compile(r'(</?p>|<(?:h[1-6]|ul|ol|figure|blockquote|table|div|hr)\b[^>]*>)')


def balance_p(h):
    """Old sites nest <p> in <p> and leave stray </p>: a browser turns each stray one into an empty paragraph."""
    out, open_ = [], False
    for tok in PARA_BREAKER.split(h):
        if tok == '<p>':
            out.append('</p><p>' if open_ else '<p>')
            open_ = True
        elif tok == '</p>':
            if open_:
                out.append(tok)
            open_ = False
        elif tok and PARA_BREAKER.fullmatch(tok):  # a block element closes an open paragraph
            out.append(('</p>' if open_ else '') + tok)
            open_ = False
        else:
            out.append(tok)
    return ''.join(out) + ('</p>' if open_ else '')


# hosts of our sources that are gone (checked 2026-10): a link there leads nowhere
DEAD = re.compile(r'^https?://(?:[\w-]+\.)*(?:mrprim\.zp\.ua|prim24\.in\.ua|primorsk\.biz|primorsk\.in\.ua|primorsk\.zp\.ua|'
                  r'primrda\.gov\.ua|primrada\.gov\.ua|prym\.in\.ua|tavriya\.co\.ua|liceyprim96\.ucoz\.ua|prim2school\.ucoz\.ua|'
                  r'primroo\.ucoz\.ua|zelenovka\.ucoz\.ru|partizanzosh\.ucoz\.net|kz-rmc\.ucoz\.ua|fisra-prim-roo\.ucoz\.ua|'
                  r'kz-radolovka\.ucoz\.ru|elizavetovkakz\.at\.ua)(?::80)?(/[^"]*)?$', re.I)


def dead_links(h):
    """A link to a vanished site: our own copy of the file if we have one, else plain text;
    a paragraph that was only such a link (navigation, "download") goes away."""
    def local(href):
        m = DEAD.match(html.unescape(href))
        if not m:
            return None
        rel = os.path.join('media', re.sub(r'^https?://(www\.)?|:80(?=/)', '', html.unescape(href)).split('?')[0])
        return '/' + quote(rel) if os.path.isfile(os.path.join(ROOT, rel)) else ''

    def para(m):
        loc = local(m.group(1))
        if loc is None or loc or re.search(r'<h[1-6]|<img', m.group(2)):
            return m.group(0)
        return ''
    h = re.sub(r'<p>\s*<a href="([^"]+)"[^>]*>(.*?)</a>\s*</p>', para, h, flags=re.S)

    def link(m):
        loc = local(m.group(1))
        if loc is None:
            return m.group(0)
        return m.group(0).replace(f'href="{m.group(1)}"', f'href="{loc}"', 1) if loc else m.group(2)
    h = re.sub(r'<a href="([^"]+)"[^>]*>(.*?)</a>', link, h, flags=re.S)
    # a "download the route" heading whose file is lost
    h = re.sub(r'<h[2-4]>[^<]*завантажити[^<]*</h[2-4]>(?!\s*<p>\s*<a href="/media/)', '', h, flags=re.I)
    return re.sub(r'<p>\s*</p>', '', h)


def clean(raw, cls, page_path, drop_title=None, tries=1, join=False):
    """tries > 1: the container class repeats (navigation, article, comments) — keep the one with most text.
    join: take every occurrence instead (forum thread: one block per post), separated by rules."""
    best, parts = '', []
    for nth in range(tries):
        c = Cleaner(cls, os.path.dirname(page_path), nth)
        c.feed(raw)
        h = tidy(''.join(c.out))
        if join:
            if not h:
                break
            parts.append(h if h.startswith('<') else f'<p>{h}</p>')
        elif len(to_text(h)) > len(to_text(best)):
            best = h
    h = '\n<hr>\n'.join(parts) if join else best
    if drop_title:  # many sites repeat the title as the first heading/paragraph of the body
        first = re.search(r'<(h[234]|p)>(.*?)</\1>', h, re.S)
        if first and html.unescape(re.sub(r'<[^>]+>', '', first.group(2))).strip() == drop_title.strip():
            h = (h[:first.start()] + h[first.end():]).strip()
    return re.sub(r'^(\s|<br>|</p>|<p>\s*</p>)+', '', dead_links(h))  # also what the dropped title left behind


# end-of-post blocks of the old CMS themes: tags, rubric, "see also" lists of other posts — no value in the archive
TAIL = re.compile(r'(?:<(?:p|h[2-4]|div|ul|li)>|<br>)\s*(?:<(?:strong|b|em|span)>\s*)*'
                  r'(?:Метки|Мітки|Теги|Теґи|Tags|Рубрик[аи]|Посмотрите также|Смотрите также|Дивіться також|'
                  r'Похожие (?:записи|новости|статьи)|Схожі (?:записи|новини|статті)|Другие новости|Інші новини)\s*:?(?=[\s<:]|$)', re.I)


def cut_tail(h):
    """Everything from the first tail block on goes, if a real text (200+ chars) stands before it."""
    m = TAIL.search(h)
    return h[:m.start()].rstrip() if m and len(to_text(h[:m.start()])) >= 200 else h


def to_text(h):
    t = re.sub(r'<br>', '\n', h)
    t = re.sub(r'</(p|li|h[234]|tr|figcaption|blockquote)>', '\n', t)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    return re.sub(r'\s*\n\s*', '\n', t).strip()


if __name__ == '__main__':
    assert JUNK_LINE.match('Поділитися з друзями:') and JUNK_LINE.match('Перегляди: 24') and not JUNK_LINE.match('ВИРІШИЛА:')
    assert SHORTCODE.sub('', '[yjsgfa name=”fa fa-heart-o”] 100% Приморська [ПІБ приховано] [1]') == ' 100% Приморська [ПІБ приховано] [1]'
    assert tidy('<p>Звертайтесь</p><p>Костянтин Осадчий – ВК та ФБ Олексій Зайченко – ВК та ФБ</p>') == '<p>Звертайтесь</p>'
    assert PERSONAL_PROFILE.search('https://vk.com/id19802304') and not PERSONAL_PROFILE.search('https://www.facebook.com/events/1')
    assert tidy('<br>\n<p></p>\n<img src="/m.jpg">') == '<img src="/m.jpg">'
    assert tidy('<p>Фотовиставка відкрилась</p>') == '<p>Фотовиставка відкрилась</p>'
    body = '<p>' + 'Текст статті. ' * 20 + '</p>'
    assert cut_tail(body + '<p>Метки:<a>Бердянск</a></p><h3>Посмотрите также</h3><ul><li>Інше</li></ul><p>Рубрика: Болгары</p>') == body
    assert cut_tail(body + '<br>Метки:<a href="/tag/x">Бердянск</a><br>') == body
    assert balance_p('<p> <p>a</p> </p></p><p><h2>b</h2></p>') == '<p> </p><p>a</p> <p></p><h2>b</h2>'  # empty ones are dropped later in tidy()
    assert dead_links('<p><a href="http://www.prym.in.ua/?cat=29" rel="noopener">Завітай</a></p><p>x <a href="http://prym.in.ua/?p=1">тут</a></p>') == '<p>x тут</p>'
    assert dead_links('<p><a href="http://www.prym.in.ua/?page_id=790"><h3>№1 Будинок</h3></a></p>') == '<p><h3>№1 Будинок</h3></p>'
    assert dead_links('<p><a href="https://example.org/">ok</a></p>') == '<p><a href="https://example.org/">ok</a></p>'
    assert cut_tail('<p>Коротко.</p><p>Теги: x</p>') == '<p>Коротко.</p><p>Теги: x</p>'  # nothing before it: keep
    assert tidy('<p>Фото: unsplash.com</p>') == ''
    assert tidy('<p>Текст</p><ul><li>Facebook</li><li>Twitter</li></ul><p> </p>') == '<p>Текст</p>'
    print('ok')


# ── Typing slips of the sources (author's call 2026-10: fix the mechanical ones everywhere, keep the wording) ──
_LAT = 'AaBCcEeHIiKMOoPpTXxy'
_CYR = 'АаВСсЕеНІіКМОоРрТХху'
_LAT2CYR = str.maketrans(_LAT, _CYR)
_WORD = re.compile(r"[A-Za-zА-ЯІЇЄҐа-яіїєґ'’ʼ]+")
_ROMAN = re.compile(r'^[IVXLCDMІХ]{1,7}$')
_PREFIX = re.compile(r"^(з|роз|без|від|під|над|об|між|пів|через|перед|пред|із|зі)(?=[єїя])", re.I)
_NOT_PREFIXED = {'зять', 'зятя', 'зятю', 'зятем', 'зяті', 'зятів', 'зяб', 'обід', 'між'}


def _apostrophe(w):
    """м'ясо, п'ять, дев'ять, об'єднання, з'явився, зв'язок; not свято, цвях, різдвяний (a consonant before the labial)."""
    if re.search(r"[ыэъё'’ʼ]", w, re.I) or w.lower() in _NOT_PREFIXED:
        return w
    w = re.sub(r'(?i)^(з|роз|по|пов|ви)(в)(?=яз)', r"\1\2’", w)  # зв'язок, розв'язати, пов'язаний
    m = _PREFIX.match(w)
    if m and len(w) > len(m.group(1)) + 2:
        w = w[:m.end()] + '’' + w[m.end():]
    out = []
    for i, ch in enumerate(w):
        out.append(ch)
        if ch.lower() in 'бпвмф' and i + 1 < len(w) and w[i + 1].lower() in 'яєї':
            prev = w[i - 1].lower() if i else ''
            if not prev or prev in 'аеєиіїоуюяр':
                out.append('’')
    return ''.join(out)


def fix_typos(h, ukrainian=True):
    """Latin look-alike letters inside Cyrillic words, mixed-alphabet Roman numerals, missing apostrophes (Ukrainian
    texts only), doubled spaces. Text between tags only; links, addresses and Russian words stay untouched."""
    def word(m):
        w = m.group(0)
        lat, cyr = re.search(r'[A-Za-z]', w), re.search(r'[А-ЯІЇЄҐа-яіїєґ]', w)
        if lat and cyr:
            if _ROMAN.match(w):
                return w.replace('І', 'I').replace('Х', 'X')  # "ХVІ", "IІ" -> XVI, II
            if not re.search(f'[A-Za-z]', w.translate(_LAT2CYR)):
                w = w.translate(_LAT2CYR)  # "Oбласні", "Kультурно"
        if ukrainian and not lat:
            w = re.sub(r'(?i)(захис)т(ни)', r'\1\2', w)  # "захистників" -> "захисників" ("захистити" stays)
            return _apostrophe(w)
        return w
    parts = re.split(r'(<[^>]+>)', h)
    for k in range(0, len(parts), 2):
        if parts[k] and not re.search(r'https?://|www\.', parts[k]):
            parts[k] = re.sub(r'(?<=\S) {2,}(?=\S)', ' ', _WORD.sub(word, parts[k]))
    return ''.join(parts)


# ── Privacy: people who stayed under occupation must not be searchable by name or phone ──────────
_NAME = r"[А-ЯІЇЄҐ][а-яіїєґ'’-]+"
_SP = r"(?:\s|<br>)*"  # cleaned HTML may break a line between "гр." and the name
CITIZEN = re.compile(rf"\b(гр\.+,?|громадян(?:ин|ину|ці|ки|ам|и|ка)?)((?:{_SP}(?:України|РФ|Росії))+)?{_SP}"
                     rf"(?!Примор|Україн|Запоріз|Бердян|Міськ|Громад|Росі)({_NAME}\s+[А-ЯІЇЄҐ]\.\s?[А-ЯІЇЄҐ]\.|{_NAME}(?:\s+{_NAME}){{0,2}})")
# sole proprietors and applicants are private people too
PRIVATE_ROLE = re.compile(rf"\b(ФОП|СПД|ФОП-|фізичн\w* особ\w*[- –]підприєм\w*|заявник\w*:?|орендар\w*:?)\s*"
                          rf"(?!Примор|Україн|Запоріз|Бердян|Міськ|Громад|ТОВ|ПП\b)({_NAME}\s+[А-ЯІЇЄҐ]\.\s?[А-ЯІЇЄҐ]\.|{_NAME}(?:\s+{_NAME}){{1,2}})")
_S = r'(?:[\s-]|&nbsp;|<[^>]+>){0,3}'  # separators as people type them, markup in between included ("<b>(067)</b><b> 406-70-94</b>")
_OP = r'(?:\+?38[\s-]?)?\(?0(?:39|50|63|66|67|68|73|91|92|93|94|95|96|97|98|99)\)?' + _S
MOBILE = re.compile(_OP + rf'(?:\d{{3}}{_S}\d{{2}}{_S}\d{{2}}|\d{{2}}{_S}\d{{2}}{_S}\d{{3}})\b')
CARD = re.compile(r'\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b')
EMAIL = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
PUBLIC_MAIL = re.compile(r'(gov\.ua|zp\.ua|\.org|lobbyx|ukrtel)$|^(mr\.?prim|prim(adm|rdk)|.*(rada|adm|prim)\w*@)', re.I)


def mask_private(h, site):
    h = MOBILE.sub('[телефон приховано]', h)
    h = CARD.sub('[номер картки приховано]', h)
    h = EMAIL.sub(lambda m: m.group(0) if PUBLIC_MAIL.search(m.group(0)) else '[email приховано]', h)
    if site in ('archive_mrprim', 'primrda'):  # council / district decisions about individual residents (land, aid, permits)
        h = CITIZEN.sub(lambda m: f'{m.group(1)}{m.group(2) or ""} [ПІБ приховано]', h)
        h = PRIVATE_ROLE.sub(lambda m: f'{m.group(1)} [ПІБ приховано]', h)
    return h


assert mask_private('гр. України Зінчук Олександр Петрович', 'archive_mrprim') == 'гр. України [ПІБ приховано]'
assert mask_private('громадянці Шевченко О.М. надати', 'archive_mrprim') == 'громадянці [ПІБ приховано] надати'
assert mask_private('громадяни Приморської громади', 'archive_mrprim') == 'громадяни Приморської громади'
assert mask_private('(заявник, орендар: ФОП Муравйов А.С.; адреса', 'archive_mrprim') == '(заявник, орендар: ФОП [ПІБ приховано]; адреса'
assert mask_private('гр. РФ Терзієва Г.І.; гр..Петренко Д.А.; гр. України\nДячук А.В.', 'archive_mrprim') == 'гр. РФ [ПІБ приховано]; гр.. [ПІБ приховано]; гр. України [ПІБ приховано]'
assert mask_private('гр.<br>України Бєлова Н.А.;', 'archive_mrprim') == 'гр.<br>України [ПІБ приховано];'
assert mask_private('тел. 099-771-82-59, 7-30-95', 'x') == 'тел. [телефон приховано], 7-30-95'
assert mask_private('тел. 050-592--1751, (067) 406-70-94, 050-066- 66-90, 095 43 54 501, картка 5168 7573 3935 9194', 'x') == \
    'тел. [телефон приховано], [телефон приховано], [телефон приховано], [телефон приховано], картка [номер картки приховано]'
assert fix_typos('Oбласні заходи, IІ квартал, ХVІ фестиваль') == 'Обласні заходи, II квартал, XVI фестиваль'
assert fix_typos('обєднатися, памяті, сімя, мясо, пять, девять, звязок, зявився, підїзд') == \
    'об’єднатися, пам’яті, сім’я, м’ясо, п’ять, дев’ять, зв’язок, з’явився, під’їзд'
assert fix_typos('Дня захистників, захистити') == 'Дня захисників, захистити'
assert fix_typos('свято, цвях, різдвяний, пюре, бюджет, зять, мавпячий, обід') == 'свято, цвях, різдвяний, пюре, бюджет, зять, мавпячий, обід'
assert fix_typos('объединиться, пять', ukrainian=False) == 'объединиться, пять'
assert fix_typos('<a href="http://x.ua/obiednannia">обєднання</a>') == '<a href="http://x.ua/obiednannia">об’єднання</a>'
assert mask_private('<strong>(067)</strong><strong> 406-70-94</strong>', 'x') == '<strong>[телефон приховано]</strong>'
assert mask_private('тел. 061-377-30-95 (приймальня)', 'x') == 'тел. 061-377-30-95 (приймальня)'
assert mask_private('mrprim@ukr.net someone@example.com vb@zp.dsns.gov.ua', 'x') == 'mrprim@ukr.net [email приховано] vb@zp.dsns.gov.ua'
