"""30-second square update for Facebook (2026-10-25): the chronicle grew by the «Приморськ 24/7» Facebook posts, and the map
of memories and dreams has its first real records. Frames with PIL -> mp4 with ffmpeg; the chronicle's own sound kit.

    .venv/bin/python social/update_memories_video.py     # needs pillow; writes social/prym-update-10-25.mp4 + update-10-25-still.png

Part one is the standard update (update_video.py: the counter, the +N pill, the topics); part two crossfades onto the live
map (memories-map-square.png, a screenshot of /memories) with the counts of memories and dreams and two of the records.
"""
import os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont
import update_video as uv
from update_video import W, H, FPS, CREAM, AMBER, MINT, GREEN, text, rrect, header, font, MONO, prog, num, records
import sound
from memories_video import walking_pad

HERE = os.path.dirname(os.path.abspath(__file__))
DUR = 30.0
OUT = 'prym-update-10-25.mp4'
OLD, NEW = 9897, 10374  # records in the chronicle before and after the Facebook posts
ROWS = [('Молодь і діти', 65), ('Благоустрій і ЖКГ', 63), ('Громадські ініціативи', 40), ("Історія і пам’ять", 32)]
ROWS_LABEL = 'ПРО ЩО НОВІ ЗАПИСИ'
MEMORIES, DREAMS = 14, 12  # all the lights on the map, the author's first ones included
QUOTES = [('Пам’ятаю як зовсім маленька бігала на город і їла смачну зелену черешню, поки мама не бачила.', 'Ксенія Т., Приморськ', 'Спогад'),
          ('Хочу привезти онука в рідний дім. Щоб він побачив наше море.', 'Оксана К., Приморськ', 'Мрія')]
INK, SOFT, BLUE, ORANGE = (58, 49, 39), (110, 96, 78), (93, 143, 189), (224, 150, 47)
MAK = lambda s: ImageFont.truetype(os.path.join(HERE, '..', 'timeline', 'fonts', 'Mak-SemiBoldHigh.otf'), s)
MAP = Image.open(os.path.join(HERE, 'memories-map-square.png')).convert('RGB')  # taken at twice the video's size: crisp up close
SWITCH = 12.8  # the crossfade from the counter to the map


def plural(n, one, few, many):
    return one if n % 10 == 1 and n % 100 != 11 else few if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else many


def counter(t):
    """Part one: as in update_video.frame, without its footer (the address comes at the very end)."""
    im = uv.BG.copy().convert('RGBA')
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    M = 84
    header(lay, d, t)
    a = prog(t, 0.4, 1.1)
    text(d, (W // 2, 262 - 30 * (1 - a)), 'Архів поповнився', font(64), CREAM, a, 'ma')
    a = prog(t, 1.0, 1.5)
    n = round(OLD + (NEW - OLD) * prog(t, 1.4, 4.0))
    text(d, (W // 2, 330), num(n), font(186), AMBER if t > 4.0 else CREAM, a, 'ma')
    text(d, (W // 2, 548), 'записів у хроніці', font(34, 600), MINT, a, 'ma')
    a = prog(t, 4.0, 4.5)
    if a > 0:
        sc = 0.7 + 0.3 * a
        label = f'+{NEW - OLD} {records(NEW - OLD)}'
        pw, ph = int((d.textlength(label, font=font(40)) + 64) * sc), int(76 * sc)
        x0, y0 = W // 2 - pw // 2, 648 - ph // 2  # its own row under the number: beside it, it covered the last digits
        rrect(lay, (x0, y0, x0 + pw, y0 + ph), ph // 2, AMBER + (int(255 * a),))
        text(d, (x0 + pw // 2, y0 + ph // 2), label, font(int(40 * sc)), GREEN, a, 'mm')
    lw = sum(d.textlength(ch, font=MONO(20)) + 4 for ch in ROWS_LABEL) - 4
    text(d, (W // 2 - lw / 2, 716), ROWS_LABEL, MONO(20), AMBER, prog(t, 5.2, 5.7), track=4)
    X = (W - 880) // 2  # the topics table, centred as a whole (names left, bars and numbers right)
    for i, (name, k) in enumerate(ROWS):
        st = 5.6 + i * 0.55
        a = prog(t, st, st + 0.5)
        y = 762 + i * 56
        text(d, (X, y), name, font(34, 700), CREAM, a)
        bw = int(330 * k / ROWS[0][1] * prog(t, st + 0.2, st + 1.0))
        if a > 0:
            rrect(lay, (X + 470, y + 10, X + 470 + max(bw, 24), y + 34), 12, AMBER + (int(255 * a),))
        text(d, (X + 470 + max(bw, 12) + 18, y), str(k), font(34), CREAM, a)
    im.alpha_composite(lay)
    return im


def memories(t):
    """Part two: the map slowly coming closer to the town, the counts, two records, the address."""
    # a slow, even push towards Приморськ (about 680, 690 of 1080): linear in time, and the crop box in fractions of a
    # pixel (whole-pixel boxes made the picture jump a pixel now and then)
    p = max(0.0, min(1.0, (t - SWITCH) / (DUR - SWITCH)))
    s, k = MAP.width / W, 1 + .14 * p
    cx, cy = (540 + 140 * .6 * p) * s, (540 + 150 * .6 * p) * s
    half = MAP.width / k / 2
    cx, cy = (min(max(c, half), MAP.width - half) for c in (cx, cy))  # the box never leaves the picture
    bg = MAP.resize((W, H), Image.BICUBIC, box=(cx - half, cy - half, cx + half, cy + half)).convert('RGBA')
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    M = 70
    # the top card: the name and the counts
    a = prog(t, SWITCH + .8, SWITCH + 1.6)
    top, ch = M - 20 * (1 - a), 300
    rrect(lay, (M, top, W - M, top + ch), 28, (255, 251, 242, int(236 * a)))
    # the title, the line and the chips as one block, centred in the card both ways (measured, not guessed)
    f, fa, fs = MAK(84), MAK(52), font(30, 600)
    tb = d.textbbox((0, 0), 'Спогади мрії', font=f, anchor='ls')  # with the descender of р and д
    sb = d.textbbox((0, 0), 'вже світяться на мапі громади', font=fs, anchor='ls')
    block = (tb[3] - tb[1]) + 16 + (sb[3] - sb[1]) + 22 + 62
    y = top + (ch - block) / 2
    base = y - tb[1]
    parts = (('Спогади', ORANGE, f), (' та ', (180, 157, 118), fa), ('мрії', BLUE, f))
    x = W / 2 - sum(d.textlength(w_, font=fw) for w_, _, fw in parts) / 2
    for word, col, fw in parts:
        text(d, (x, base), word, fw, col, a, 'ls')
        x += d.textlength(word, font=fw)
    y += tb[3] - tb[1] + 16
    text(d, (W // 2, y - sb[1]), 'вже світяться на мапі громади', fs, SOFT, a, 'ms')
    cy = y + (sb[3] - sb[1]) + 22
    for i, (n, one, few, many, col, at) in enumerate([(MEMORIES, 'спогад', 'спогади', 'спогадів', ORANGE, SWITCH + 2.2),
                                                       (DREAMS, 'мрія', 'мрії', 'мрій', BLUE, SWITCH + 3.0)]):
        b = prog(t, at, at + .5)
        v = round(n * prog(t, at, at + 1.2))
        label = f'{v} {plural(v, one, few, many)}'
        x0 = W // 2 - 285 + i * 300  # the two chips as a centred pair
        if b > 0:
            rrect(lay, (x0, cy, x0 + 270, cy + 62), 31, col + (int(255 * b),))
            text(d, (x0 + 135, cy + 31), label, font(34), (255, 255, 255), b, 'mm')
    # the records, one after the other, in a postcard at the bottom
    for i, (q, who, kind) in enumerate(QUOTES):
        st, en = SWITCH + 4.6 + i * 4.4, SWITCH + 4.6 + i * 4.4 + 4.2
        b = prog(t, st, st + .7) * (1 - prog(t, en - .1, en + .5)) if i < len(QUOTES) - 1 else prog(t, st, st + .7) * (1 - prog(t, DUR - 4.6, DUR - 4.0))
        if b <= 0:
            continue
        top = H - M - 330 + 24 * (1 - prog(t, st, st + .7))
        rrect(lay, (M, top, W - M, top + 300), 26, (255, 253, 247, int(245 * b)))
        text(d, (M + 40, top + 32), kind, MAK(46), ORANGE if kind == 'Спогад' else BLUE, b)
        words, lines, line = q.split(), [], ''
        for wd in words:  # wrap the record to the card
            if d.textlength(line + ' ' + wd, font=font(36, 500)) > W - 2 * M - 80 and line:
                lines.append(line); line = wd
            else:
                line = (line + ' ' + wd).strip()
        lines.append(line)
        for j, l in enumerate(lines[:3]):
            text(d, (M + 40, top + 100 + j * 48), l, font(36, 500), INK, b)
        text(d, (W - M - 40, top + 252), who, font(28, 700), SOFT, b, 'ra')
    # the ending: the call and the address
    a = prog(t, DUR - 4.0, DUR - 3.2)
    if a > 0:
        top = H - M - 230 + 20 * (1 - a)
        rrect(lay, (M, top, W - M, top + 200), 26, (23, 79, 62, int(245 * a)))
        text(d, (W // 2, top + 62), 'Додайте свій спогад чи мрію', font(40), CREAM, a, 'mm')
        rrect(lay, (W // 2 - 300, top + 104, W // 2 + 300, top + 170), 33, AMBER + (int(255 * a),))
        text(d, (W // 2, top + 137), 'prym.mydom.website/memories', font(32), GREEN, a, 'mm')
    bg.alpha_composite(lay)
    return bg


def frame(t):
    if t < SWITCH:
        return counter(t).convert('RGB')
    if t > SWITCH + 1.0:
        return memories(t).convert('RGB')
    return Image.blend(counter(t).convert('RGB'), memories(t).convert('RGB'), prog(t, SWITCH, SWITCH + 1.0))


def soundtrack():
    buf, rnd = sound.track(DUR), __import__('random').Random(7)
    walking_pad(buf, DUR)
    sound.ticks(buf, 1.45, 2.55, rnd)
    sound.chime(buf, 4.0)
    for i in range(len(ROWS)):
        sound.add(buf, 5.6 + i * .55, 2.5, sound.bell(sound.NOTES[i]), .22)
    sound.chime(buf, SWITCH + .8)
    sound.add(buf, SWITCH + 2.2, 2.5, sound.bell(sound.NOTES[1]), .2)
    sound.add(buf, SWITCH + 3.0, 2.5, sound.bell(sound.NOTES[3]), .2)
    for i in range(len(QUOTES)):
        sound.add(buf, SWITCH + 4.6 + i * 4.4, 2.5, sound.bell(sound.NOTES[2]), .16)
    sound.chord(buf, DUR - 4.0)
    sound.save(buf, 'update-10-25.wav')
    return os.path.join(HERE, 'sounds', 'update-10-25.wav')


if __name__ == '__main__':
    out = tempfile.mkdtemp()
    for i in range(int(DUR * FPS)):
        frame(i / FPS).save(os.path.join(out, f'{i:04d}.png'))
    frame(SWITCH + 8).save(os.path.join(HERE, 'update-10-25-still.png'))
    wav = soundtrack()
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(out, '%04d.png'), '-i', wav,
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                    '-movflags', '+faststart', os.path.join(HERE, OUT)], check=True)
    print('ok', OUT)
