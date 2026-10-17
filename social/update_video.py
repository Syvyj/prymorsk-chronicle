"""Square 1080x1080 update animation for Facebook (2026-10): frames with PIL -> mp4 with ffmpeg, soundtrack from sound.py.

    .venv/bin/python social/update_video.py     # needs pillow (.venv) and ffmpeg; writes social/prym-update.mp4 + update-still.png
Numbers, villages and texts are the constants below (OLD, NEW, ROWS).
"""
import os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(os.path.dirname(HERE), 'timeline')
W = H = 1080
FPS = 30
DUR = 12.0
GREEN, DEEP, AMBER, CREAM, MINT = (23, 79, 62), (12, 44, 34), (239, 181, 68), (255, 250, 242), (183, 213, 197)


def font(size, weight=800):
    f = ImageFont.truetype(os.path.join(HERE, 'Manrope.ttf'), size)
    f.set_variation_by_axes([weight])
    return f


MONO = lambda s: font(s, 700)
ease = lambda x: 1 - (1 - max(0.0, min(1.0, x))) ** 3
prog = lambda t, a, b: ease((t - a) / (b - a))

# background: the hero photo of the site under a deep green shade
bg = Image.open(os.path.join(SITE, 'hero.jpg' if os.path.exists(os.path.join(SITE, 'hero.jpg')) else 'hero-sm.jpg')).convert('RGB')
s = max(W / bg.width, H / bg.height)
bg = bg.resize((int(bg.width * s) + 1, int(bg.height * s) + 1)).crop((0, 0, W, H)).filter(ImageFilter.GaussianBlur(2))
shade = Image.new('RGB', (W, H), DEEP)
grad = Image.linear_gradient('L').resize((W, H)).point(lambda v: 150 + v * 90 // 255)
BG = Image.composite(shade, bg, grad)
coat = Image.open(os.path.join(SITE, 'coat.png')).convert('RGBA')
coat.thumbnail((76, 76))
ngo = Image.open(os.path.join(SITE, 'ngo-logo.png')).convert('RGBA')
ngo.thumbnail((76, 76))

ROWS = [("Маринівка", 102), ("Юр’ївка", 67), ("Преслав", 7), ("Приморськ, школа № 1", 6)]
OLD, NEW = 9558, 9749


def num(n):
    return f'{n:,}'.replace(',', ' ')


def text(d, xy, s, f, fill, alpha=1.0, anchor='la', track=0):
    if alpha <= 0:
        return
    if track:
        x, y = xy
        if anchor.startswith('r'):
            x -= sum(d.textlength(ch, font=f) + track for ch in s) - track
        for ch in s:
            d.text((x, y), ch, font=f, fill=tuple(fill) + (int(255 * alpha),))
            x += d.textlength(ch, font=f) + track
        return
    c = tuple(fill) + (int(255 * alpha),)
    d.text(xy, s, font=f, fill=c, anchor=anchor)


BRAND = (('ПРИМОРСЬК', 'Хроніка громади'), ('ПРОЄКТ ГО', '«Приморськ 24/7»'))


def header(lay, d, t, M=84, texts=None, fade=1.0):
    """The shared top: coat of arms + «Хроніка громади» left, NGO logo + name right, a divider between.
    texts: [((left label, left name), (right label, right name), opacity), ...] drawn instead of the brand (crossfades);
    fade: the whole header's opacity (another top can take its place)."""
    # coat: coat on a cream tile + label
    a = prog(t, 0.0, 0.6) * fade
    tile = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle((0, 0, 99, 99), 24, fill=CREAM + (int(255 * a),))
    c = coat.copy()
    c.putalpha(c.getchannel('A').point(lambda v: int(v * a)))
    tile.alpha_composite(c, ((100 - c.width) // 2, (100 - c.height) // 2))
    lay.alpha_composite(tile, (M, M))
    tiles_a = a
    # the NGO: logo tile on the right, name under it
    a = prog(t, 0.3, 0.9) * fade
    tile = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle((0, 0, 99, 99), 24, fill=CREAM + (int(255 * a),))
    c = ngo.copy()
    c.putalpha(c.getchannel('A').point(lambda v: int(v * a)))
    tile.alpha_composite(c, ((100 - c.width) // 2, (100 - c.height) // 2))
    lay.alpha_composite(tile, (W - M - 100, M))
    for (ll, ln), (rl, rn), o in texts or [(*BRAND, 1)]:
        text(d, (M + 128, M + 18), ll, MONO(20), AMBER, tiles_a * o, track=4)
        text(d, (M + 128, M + 48), ln, font(32), CREAM, tiles_a * o)
        text(d, (W - M - 128, M + 18), rl, MONO(20), AMBER, a * o, 'ra', track=4)
        text(d, (W - M - 128, M + 48), rn, font(32), CREAM, a * o, 'ra')
    d.line((W // 2, M + 12, W // 2, M + 88), fill=CREAM + (int(90 * a),), width=2)  # divider between the two



def frame(t):
    im = BG.copy().convert('RGBA')
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    M = 84
    header(lay, d, t)

    # title
    a = prog(t, 0.4, 1.1)
    y = 262 - 30 * (1 - a)
    text(d, (M, y), 'Архів поповнився', font(64), CREAM, a)
    # counter
    a = prog(t, 1.0, 1.5)
    n = round(OLD + (NEW - OLD) * prog(t, 1.4, 4.0))
    text(d, (M - 6, 330), num(n), font(186), AMBER if t > 4.0 else CREAM, a)
    text(d, (M, 548), 'новин і подій у хроніці', font(34, 600), MINT, a)
    # +191 pill
    a = prog(t, 4.0, 4.5)
    if a > 0:
        sc = 0.7 + 0.3 * a
        pw, ph = int(380 * sc), int(76 * sc)
        x0, y0 = W - M - pw, 430 - ph // 2
        d.rounded_rectangle((x0, y0, x0 + pw, y0 + ph), ph // 2, fill=AMBER + (int(255 * a),))
        text(d, (x0 + pw // 2, y0 + ph // 2), f'+{NEW - OLD} новий запис', font(int(40 * sc)), GREEN, a, 'mm')
    # villages: one by one, with bars
    text(d, (M, 636), 'НОВІ ДЖЕРЕЛА — САЙТИ СІЛЬСЬКИХ ШКІЛ', MONO(20), AMBER, prog(t, 4.6, 5.1), track=4)
    for i, (name, k) in enumerate(ROWS):
        st = 5.0 + i * 0.55
        a = prog(t, st, st + 0.5)
        y = 682 + i * 56
        text(d, (M, y), name, font(34, 700), CREAM, a)
        bw = int(330 * k / ROWS[0][1] * prog(t, st + 0.2, st + 1.0))
        if a > 0:
            d.rounded_rectangle((M + 470, y + 10, M + 470 + max(bw, 12), y + 34), 12, fill=AMBER + (int(255 * a),))
        text(d, (M + 470 + max(bw, 12) + 18, y), str(k), font(34), CREAM, a)
    # footer: address
    a = prog(t, 8.2, 8.9)
    y = H - M - 70 + 20 * (1 - a)
    d.rounded_rectangle((M, y, M + 470, y + 70), 18, fill=CREAM + (int(255 * a),))
    text(d, (M + 235, y + 35), 'prym.mydom.website', font(34), GREEN, a, 'mm')
    text(d, (W - M, y + 35), "Громада, яку ми пам’ятаємо", font(30, 600), MINT, a, 'rm')
    im.alpha_composite(lay)
    return im.convert('RGB')


if __name__ == '__main__':
    out = tempfile.mkdtemp()
    for i in range(int(DUR * FPS)):
        frame(i / FPS).save(os.path.join(out, f'{i:04d}.png'))
    frame(DUR).save(os.path.join(HERE, 'update-still.png'))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(out, '%04d.png'),
                    '-i', os.path.join(HERE, 'sounds', 'update-12s.wav'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18',
                    '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', os.path.join(HERE, 'prym-update.mp4')], check=True)
    print('ok')
