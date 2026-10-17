"""Facebook cover for the chronicle: 1640x624 (FB's recommended size), the site's look.

    .venv/bin/python social/fb_cover.py     # -> social/fb-cover.png (+ fb-cover-safe.png with the crop guides, for checking)
Everything that matters sits in the centre: phones crop the sides, and the page avatar covers the lower left on desktop.
"""
import os
from PIL import Image, ImageDraw, ImageFilter
import update_video as u

W, H = 1640, 624
SAFE_X = 230            # phones show roughly the middle 1180 px of the width


def make(guides=False):
    bg = Image.open(os.path.join(u.SITE, 'hero.jpg')).convert('RGB')
    s = max(W / bg.width, H / bg.height)
    bg = bg.resize((int(bg.width * s) + 1, int(bg.height * s) + 1))
    top = int((bg.height - H) * .55)
    bg = bg.crop((0, top, W, top + H)).filter(ImageFilter.GaussianBlur(1.2))
    # the tide: deep green from the bottom and the edges, the photo breathing in the middle
    shade = Image.new('RGB', (W, H), u.DEEP)
    v = Image.linear_gradient('L').resize((W, H)).point(lambda p: 105 + p * 120 // 255)
    edge = Image.linear_gradient('L').rotate(90, expand=True).resize((W, H))
    edge = Image.eval(edge, lambda p: abs(p - 128) * 2)  # 0 in the centre, 255 at both sides
    mask = Image.blend(v, edge.point(lambda p: 90 + p * 140 // 255), .35)
    im = Image.composite(shade, bg, mask).convert('RGBA')

    d = ImageDraw.Draw(im)
    cx = W // 2
    u.text(d, (cx, 118), 'АРХІВ ГРОМАДИ · 2004–2022', u.MONO(24), u.AMBER, 1, 'ma', track=0)
    u.text(d, (cx, 160), 'Приморськ.', u.font(170), u.CREAM, 1, 'ma')
    u.text(d, (cx, 362), "Громада, яку ми пам’ятаємо", u.font(58), u.AMBER, 1, 'ma')
    # the address as a button, and what is inside
    bw, bh, by = 470, 72, 466
    d.rounded_rectangle((cx - bw // 2, by, cx + bw // 2, by + bh), 20, fill=u.CREAM)
    u.text(d, (cx, by + bh // 2), 'prym.mydom.website', u.font(34), u.GREEN, 1, 'mm')
    u.text(d, (cx, by + bh + 22), 'Хроніка громади: понад 9 700 новин міста й сіл, фото та відео', u.font(24, 600), u.MINT, 1, 'ma')
    if guides:  # where phones crop and where the avatar sits
        for x in (SAFE_X, W - SAFE_X):
            d.line((x, 0, x, H), fill=(255, 0, 0, 255), width=2)
        d.rectangle((40, H - 150, 380, H), outline=(255, 0, 0, 255), width=2)
    return im.convert('RGB')


if __name__ == '__main__':
    make().save(os.path.join(u.HERE, 'fb-cover.png'))
    make(guides=True).save(os.path.join(u.HERE, 'fb-cover-safe.png'))
    print('ok')
