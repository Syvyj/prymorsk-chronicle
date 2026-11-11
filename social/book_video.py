"""The Book of the Year as a square video: the cover, then the year month by month, a page turning on every month.

    .venv/bin/python social/book_video.py 2017      # one year  -> timeline/book/video/2017.mp4 (+ social/book-2017.png still)
    .venv/bin/python social/book_video.py           # every year that has a book
Data: timeline/book/<year>.json (pages.py). Look and sounds: update_video.py and sound.py (no third-party media but the archive's photos).
The site's «Поділитися відео» button shares these files.
"""
import json, math, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFilter
import update_video as u
import sound as snd
from day_video import wrap, MONTHS as MONTHS_GEN

ROOT = os.path.dirname(u.HERE)
BOOK = os.path.join(ROOT, 'timeline', 'book')
W = H = u.W
FPS = 30
PREVIEW, PREVIEW_DIR = None, tempfile.gettempdir()
MONTHS = 'січень лютий березень квітень травень червень липень серпень вересень жовтень листопад грудень'.split()
PAPER, PAPER_2, INK, MUTED, CLOTH, CLOTH_2, GOLD, GOLD_2 = (251, 246, 234), (243, 234, 214), (27, 42, 36), (107, 114, 107), (29, 90, 71), (19, 63, 50), (229, 194, 122), (180, 138, 60)
TABLE = (233, 225, 208)
PW, PH = 700, 960                       # a page, portrait, centred on the table
PX, PY = (W - PW) // 2, (H - PH) // 2 + 10
COVER_T, OPEN_T, MONTH_T, TURN_T, FINAL_T = 2.6, .8, 1.9, .5, 5.0


def plural(n, one, few, many):
    a, b = n % 10, n % 100
    return one if a == 1 and b != 11 else few if 2 <= a <= 4 and not 12 <= b <= 14 else many


def textc(d, cx, y, s, f, fill, track=0):
    """Text centred on cx with letter spacing (PIL's anchor can't centre tracked text)."""
    w = sum(d.textlength(ch, font=f) for ch in s) + track * (len(s) - 1)
    x = cx - w / 2
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + track


def rot_aa(im, deg):
    """Rotate without stair-stepped edges: rotate at 3x, then scale back down."""
    big = im.resize((im.width * 3, im.height * 3), Image.LANCZOS).rotate(deg, expand=True, resample=Image.BICUBIC)
    return big.resize((big.width // 3, big.height // 3), Image.LANCZOS)


def photo(path, w, h, radius=14):
    try:
        im = Image.open(os.path.join(ROOT, path.lstrip('/'))).convert('RGB')
    except Exception:
        return None
    s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    im = im.crop((x, y, x + w, y + h)).convert('RGBA')
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=255)
    im.putalpha(m)
    return im


def table():
    bg = Image.new('RGB', (W, H), TABLE)
    g = Image.radial_gradient('L').resize((W, H))
    return Image.composite(Image.new('RGB', (W, H), (205, 194, 170)), bg, g.point(lambda v: min(255, v * 1.1))).convert('RGBA')


COAT = Image.open(os.path.join(ROOT, 'timeline', 'coat-hi.png')).convert('RGBA')


def cover_page(book):
    p = Image.new('RGBA', (PW, PH), CLOTH + (255,))
    grad = Image.linear_gradient('L').resize((PW, PH)).point(lambda v: v * 120 // 255)
    p = Image.composite(Image.new('RGBA', (PW, PH), CLOTH_2 + (255,)), p, grad)
    d = ImageDraw.Draw(p)
    d.rounded_rectangle((34, 34, PW - 34, PH - 34), 12, outline=GOLD + (140,), width=3)
    d.rectangle((18, 0, 28, PH), fill=(0, 0, 0, 60))                          # the spine's hinge
    coat = COAT.copy()
    coat.thumbnail((140, 140), Image.LANCZOS)
    p.alpha_composite(coat, ((PW - coat.width) // 2, 64))
    textc(d, PW // 2, 222, 'ПРИМОРСЬК', u.font(34, 800), GOLD, track=9)
    ph = photo(book['cover'] or '/timeline/hero-sm.jpg', 520, 390, 3)
    if ph:
        frame = Image.new('RGBA', (548, 418), PAPER + (255,))
        frame.alpha_composite(ph, (14, 14))
        frame = rot_aa(frame, 1.4)
        shadow = Image.new('RGBA', (frame.width + 60, frame.height + 60), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rectangle((30, 40, frame.width + 30, frame.height + 40), fill=(0, 0, 0, 120))
        shadow = shadow.filter(ImageFilter.GaussianBlur(14))
        p.alpha_composite(shadow, ((PW - shadow.width) // 2, 278))
        p.alpha_composite(frame, ((PW - frame.width) // 2, 290))
    u.text(d, (PW // 2, 836), book['y'], u.font(170), GOLD, 1, 'ms')
    textc(d, PW // 2, 858, 'КНИГА РОКУ', u.font(36, 800), GOLD, track=10)
    return p


def paper():
    p = Image.new('RGBA', (PW, PH), PAPER + (255,))
    g = Image.linear_gradient('L').rotate(90, expand=True).resize((PW, PH)).point(lambda v: max(0, v - 200) * 3)
    return Image.composite(Image.new('RGBA', (PW, PH), PAPER_2 + (255,)), p, g)


def title_page(book):
    p = paper()
    d = ImageDraw.Draw(p)
    u.text(d, (60, 70), 'Хроніка громади Приморська', u.font(24, 600), GOLD_2, 1)
    u.text(d, (48, 120), book['y'], u.font(230), u.GREEN, 1)
    for k, line in enumerate(wrap(d, f"Рік громади у {book['count']} {plural(book['count'], 'історії', 'історіях', 'історіях')}, місяць за місяцем.", u.font(34, 700), PW - 120)):
        u.text(d, (60, 400 + k * 44), line, u.font(34, 700), INK, 1)
    for k, (n, label) in enumerate([(book['count'], 'записів у хроніці'), (book['videos'], 'відеосюжетів'),
                                    (book['places'], 'населених пунктів'), (len(book['months']), 'місяців у книзі')]):
        x, y = 60 + (k % 2) * 300, 560 + (k // 2) * 170
        u.text(d, (x, y), str(n), u.font(84), u.GREEN, 1)
        u.text(d, (x + 4, y + 100), label, u.font(26, 600), MUTED, 1)
    return p


def calendar(p, d, book, m, x0, y0, width):
    """The month's calendar: a dot on every day with records, larger for busier days; dark = in the book."""
    import calendar as cal
    first, length = cal.monthrange(int(book['y']), m['m'])
    in_book = {int(s['d'][8:10]) for s in m['stories']}
    cw = width / 7
    for k, wd in enumerate('пн вт ср чт пт сб нд'.split()):
        u.text(d, (x0 + cw * k + cw / 2, y0), wd, u.font(19, 700), MUTED, 1, 'ma')
    top, rh, mx = y0 + 42, 50, max(1, max(m['days']))
    dots = Image.new('RGBA', p.size, (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    for day in range(1, length + 1):
        i = first + day - 1
        cx, cy = x0 + cw * (i % 7) + cw / 2, top + rh * (i // 7) + rh / 2
        n = m['days'][day - 1]
        if n:
            r = 12 + 10 * (n / mx) ** .5
            dd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(23, 79, 62, 235) if day in in_book else (23, 79, 62, 46))
    p.alpha_composite(dots)
    for day in range(1, length + 1):
        i = first + day - 1
        cx, cy = x0 + cw * (i % 7) + cw / 2, top + rh * (i // 7) + rh / 2
        n = m['days'][day - 1]
        if n:
            u.text(d, (cx, cy), str(day), u.font(20, 700), (255, 255, 255) if day in in_book else INK, 1, 'mm')
        else:
            u.text(d, (cx, cy), str(day), u.font(20, 600), (190, 182, 165), 1, 'mm')
    return top + rh * ((first + length + 6) // 7)


def mounted(src, w_px, h_px, tilt):
    """A weak photo as a small mounted print: white border, black photo corners, a slight tilt; never enlarged past the file."""
    ph = photo(src, w_px, h_px, 0)
    if not ph:
        return None
    pad = 10
    card = Image.new('RGBA', (w_px + 2 * pad, h_px + 2 * pad), (255, 253, 247, 255))
    card.alpha_composite(ph, (pad, pad))
    cd = ImageDraw.Draw(card)
    c = 26
    cd.polygon([(0, 0), (c, 0), (0, c)], fill=(43, 42, 38, 220))
    cd.polygon([(card.width, card.height), (card.width - c, card.height), (card.width, card.height - c)], fill=(43, 42, 38, 220))
    sh = Image.new('RGBA', (card.width + 40, card.height + 40), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((20, 26, card.width + 20, card.height + 26), fill=(60, 45, 20, 90))
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    sh.alpha_composite(card, (20, 20))
    return rot_aa(sh, tilt)


def month_page(book, m):
    """A month as the book shows it: the name, the calendar, then the lead record with its day in the margin."""
    p = paper()
    d = ImageDraw.Draw(p)
    head = f"Книга року {book['y']}"
    hf = u.font(23, 700)
    textc(d, PW - 56 - (sum(d.textlength(c, font=hf) for c in head) + 1.5 * (len(head) - 1)) / 2, 40, head, hf, MUTED, track=1.5)
    u.text(d, (46, 184), MONTHS[m['m'] - 1], u.font(118), u.GREEN, 1, 'ls')
    u.text(d, (56, 204), f"{m['count']} {plural(m['count'], 'запис', 'записи', 'записів')} у хроніці, {len(m['stories'])} у книзі", u.font(24, 600), MUTED, 1)
    y = calendar(p, d, book, m, 56, 258, PW - 112) + 24
    d = ImageDraw.Draw(p)
    d.line((56, y, PW - 56, y), fill=(224, 211, 184), width=2)
    y += 26
    lead = m['stories'][0]
    day, mg = int(lead['d'][8:10]), MONTHS_GEN[m['m'] - 1]
    u.text(d, (150, y - 6), str(day), u.font(76), u.GREEN, 1, 'ra')
    u.text(d, (150, y + 78), mg, u.font(19, 600), MUTED, 1, 'ra')
    bx, bw = 176, PW - 56 - 176
    good = lead['i'] and lead['w'] >= 480 and lead['w'] >= lead['h']
    weak = lead['i'] and 150 <= lead['w'] and not good
    tw = bw - 214 if weak else bw
    if weak:
        pw_ = min(180, lead['w'])
        im = mounted(lead['i'], pw_, int(pw_ / max(.75, min(1.5, lead['w'] / lead['h']))), 1.6)
        if im:
            p.alpha_composite(im, (PW - 56 - im.width + 16, y - 16))
    f = u.font(34)
    lines = wrap(d, lead['t'], f, tw)[:4 if weak else 3]
    for k, line in enumerate(lines):
        u.text(d, (bx, y + k * 42), line, f, INK, 1)
    yy = y + len(lines) * 42 + 12
    if good:
        h = min(int(bw / 1.6), PH - 60 - yy)
        im = photo(lead['i'], bw, h, 10) if h > 90 else None
        if im:
            p.alpha_composite(im, (bx, yy + 4))
            yy += h + 16
    g = u.font(24, 500)
    room = (PH - 64 - yy) // 34
    shown = wrap(d, lead['x'], g, tw)[:max(0, min(room, 4 if good else 8))]
    for k, line in enumerate(shown):
        u.text(d, (bx, yy + k * 34), line, g, MUTED, 1)
    yy += len(shown) * 34 + 22
    # a second record of the month, text only, when the page still has room for it
    if len(m['stories']) > 1 and PH - 64 - yy >= 150:
        nxt = sorted(m['stories'][1:], key=lambda s_: s_['d'])[0]
        d.line((bx, yy, PW - 56, yy), fill=(224, 211, 184), width=2)
        yy += 22
        u.text(d, (150, yy - 4), str(int(nxt['d'][8:10])), u.font(58), u.GREEN, 1, 'ra')
        u.text(d, (150, yy + 60), MONTHS_GEN[m['m'] - 1], u.font(17, 600), MUTED, 1, 'ra')
        f2 = u.font(30)
        l2 = wrap(d, nxt['t'], f2, bw)[:2]
        for k, line in enumerate(l2):
            u.text(d, (bx, yy + k * 38), line, f2, INK, 1)
        yy += len(l2) * 38 + 8
        for k, line in enumerate(wrap(d, nxt['x'], g, bw)[:max(0, min((PH - 64 - yy) // 34, 3))]):
            u.text(d, (bx, yy + k * 34), line, g, MUTED, 1)
    return p


def shadowed():
    sh = Image.new('RGBA', (PW + 80, PH + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((40, 50, PW + 40, PH + 50), fill=(0, 0, 0, 110))
    return sh.filter(ImageFilter.GaussianBlur(22))


def turn(base, old, new, p):
    """A page turning over its left edge: the old page narrows to the spine (shaded), the new one lies under it."""
    im = base.copy()
    im.alpha_composite(new, (PX, PY))
    w = int(PW * math.cos(p * math.pi / 2))
    if w > 2:
        sq = old.resize((w, PH))
        shade = Image.new('RGBA', (w, PH), (0, 0, 0, int(110 * p)))
        sq.alpha_composite(shade)
        sq.putalpha(old.getchannel('A').resize((w, PH)))
        im.alpha_composite(sq, (PX, PY))
    return im


def make(y):
    book = json.load(open(os.path.join(BOOK, f'{y}.json'), encoding='utf-8'))
    base = table()
    base.alpha_composite(shadowed(), (PX - 40, PY - 40))
    pages = [cover_page(book), title_page(book)] + [month_page(book, m) for m in book['months']]
    # timeline: cover held, then each page held MONTH_T after a turn of TURN_T
    seq, t = [], 0.0
    seq.append(('hold', 0, t, COVER_T)); t += COVER_T
    for k in range(1, len(pages)):
        seq.append(('turn', k, t, OPEN_T if k == 1 else TURN_T)); t += OPEN_T if k == 1 else TURN_T
        seq.append(('hold', k, t, MONTH_T if k > 1 else 2.0)); t += MONTH_T if k > 1 else 2.0
    final_at = t
    dur = t + FINAL_T

    held = {}

    def frame(tt):
        if tt >= final_at:  # the finale: the closed book shrinks back, the invitation appears
            a = u.prog(tt, final_at, final_at + .8)
            im = u.BG.copy().convert('RGBA')
            lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            u.header(lay, d, 99)
            steps = [final_at + k * .7 for k in range(4)]
            a0 = u.prog(tt, steps[0], steps[0] + .7)
            u.text(d, (W // 2, 330 - 30 * (1 - a0)), f'Книга року {y}', u.font(76), u.CREAM, a0, 'ma')
            a1 = u.prog(tt, steps[1], steps[1] + .7)
            u.text(d, (W // 2, 440 + 20 * (1 - a1)), 'Гортай її повністю на сайті:', u.font(40, 600), u.MINT, a1, 'ma')
            u.text(d, (W // 2, 494 + 20 * (1 - a1)), 'місяць за місяцем, історія за історією', u.font(40, 600), u.MINT, a1, 'ma')
            a2 = u.prog(tt, steps[2], steps[2] + .7)
            bw, bh, yy = 520, 84, 640 + 20 * (1 - a2)
            d.rounded_rectangle((W // 2 - bw // 2, yy, W // 2 + bw // 2, yy + bh), 22, fill=u.CREAM + (int(255 * a2),))
            u.text(d, (W // 2, yy + bh // 2), 'prym.mydom.website', u.font(38), u.GREEN, a2, 'mm')
            a3 = u.prog(tt, steps[3], steps[3] + .9)
            u.text(d, (W // 2, 780 + 14 * (1 - a3)), "Громада, яку ми пам’ятаємо", u.font(34, 600), u.MINT, a3, 'ma')
            im.alpha_composite(lay)
            out = im.convert('RGB')
            if a < 1:  # fade from the last page into the finale
                last = frame(final_at - .001)
                out = Image.blend(last, out, a)
            return out
        kind, k, st, ln = next(s for s in seq if s[2] <= tt < s[2] + s[3])
        if kind == 'hold':
            if k not in held:
                im = base.copy()
                im.alpha_composite(pages[k], (PX, PY))
                held[k] = im.convert('RGB')
            # a slow push-in while the page is held, sub-pixel smooth: an affine map, not integer resizes
            p_ = (tt - st) / ln
            z = 1 + .022 * (p_ * p_ * (3 - 2 * p_))
            c = W / 2
            return held[k].transform((W, H), Image.AFFINE, (1 / z, 0, c - c / z, 0, 1 / z, c - c / z), resample=Image.BICUBIC)
        p = (tt - st) / ln
        p = p * p * (3 - 2 * p)
        return turn(base, pages[k - 1], pages[k], p).convert('RGB')

    # sound: the pad, a chime with the cover, a soft page sound + a note on every turn (rising, then turning back), the chord at the end
    track = snd.track(dur)
    snd.pad(track, dur)
    snd.chime(track, .6)
    scale = [440.0, 493.88, 554.37, 659.25, 739.99, 880.0]
    import random
    rnd = random.Random(3)
    for n, (kind, k, st, ln) in enumerate(s for s in seq if s[0] == 'turn'):
        snd.add(track, st, .25, lambda x: math.exp(-x * 18) * (rnd.random() * 2 - 1) * .5, .1)   # the paper
        f = scale[n % len(scale)] if (n // len(scale)) % 2 == 0 else scale[-1 - n % len(scale)]
        snd.add(track, st + ln * .6, 2.2, snd.bell(f), .14)
    for k, f in enumerate([880.0, 987.77, 1108.73]):
        snd.add(track, final_at + k * .7 + .05, 2.5, snd.bell(f), .16)
    snd.chord(track, final_at + 2.1)

    if PREVIEW:
        for tt in PREVIEW:
            frame(min(tt, dur - .01)).save(os.path.join(PREVIEW_DIR, f'bk-{tt:05.1f}.png'))
        return dur
    tmp = tempfile.mkdtemp()
    snd.OUT = tmp
    snd.save(track, 'track.wav')
    for i in range(int(dur * FPS)):
        frame(i / FPS).save(os.path.join(tmp, f'{i:05d}.png'))
    frame(COVER_T * .5).save(os.path.join(u.HERE, f'book-{y}.png'))
    os.makedirs(os.path.join(BOOK, 'video'), exist_ok=True)
    out = os.path.join(BOOK, 'video', f'{y}.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, '%05d.png'), '-i', os.path.join(tmp, 'track.wav'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '22', '-preset', 'slow', '-c:a', 'aac', '-b:a', '160k', '-shortest',
                    '-movflags', '+faststart', out], check=True)
    subprocess.run(['rm', '-rf', tmp])
    return out


if __name__ == '__main__':
    years = sys.argv[1:] or [r['y'] for r in json.load(open(os.path.join(BOOK, 'index.json')))]
    for y in years:
        print(make(y), flush=True)
