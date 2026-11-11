"""«Цей день в історії»: a 30 s square video for one date — four years of the chronicle, one card each.

    .venv/bin/python social/day_video.py            # today
    .venv/bin/python social/day_video.py 10-16      # any MM-DD -> social/day-MM-DD.mp4 + .png + .txt (the FB post)
Cards come from CURATED when the date is there (texts written by hand), otherwise from timeline/data.json:
four records of different years, villages and photos preferred. Same look and sounds as update_video.py.
"""
import datetime, json, os, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw
import update_video as u
import sound as snd

ROOT = os.path.dirname(u.HERE)
W = H = u.W
FPS, DUR = 30, 30.0
M = 84
SLOTS = [3.2, 8.6, 14.0, 19.4]   # each card's entrance; a card lives 5.4 s
CARD = 5.4
FINAL = 25.0
FSTEP = .85        # the finale's four steps, one note each
FINAL_NOTES = [880.0, 987.77, 1108.73]  # A5 B5 C#6: the card notes carried one octave up
MONTHS = 'січня лютого березня квітня травня червня липня серпня вересня жовтня листопада грудня'.split()

# hand-written cards: (record id, place, title, line under it)
CURATED = {
    '10-23': [
        ('a85fbbe90c', 'Зеленівка', 'Зеленівка відсвяткувала День села', 'Покровський хоровод у дворі будинку культури: ігри, конкурси, концерт і вироби місцевих майстрів.'),
        ('0c2c8d9ff2', 'Інзівка', 'Покрова і козацтво в школі', 'Третьо- і четвертокласники провели свято «Ми роду козацького діти» про Покрову й козацькі звичаї.'),
        ('6eee34843c', 'Єлизаветівка', 'Наша зірка на «Зорепаді»', 'Катерина К. представляла школу на обласному фестивалі в Бердянську: сучасна пісня і вірш.'),
        ('b16b76508a', 'Приморськ', 'Квадрокоптер для рятувальників', 'ГО «Приморськ 24/7» разом з мелітопольськими активістами подарувала техніку приморським пожежникам.'),
    ],
    '10-22': [
        ('3167e47689', 'Приморськ', 'Довідка, що я не верблюд', 'Щоб приватизувати 10 соток, треба було вистояти чергу по довідку в управлінні культури. Фейлетон з 2009-го.'),
        ('5f5f6a5841', 'Приморський район', 'У районі буде шаховий клуб', 'Шахісти й шашкісти міста і сіл зібралися, щоб об’єднатися і проводити турніри не лише в Приморську.'),
        ('895ea5bd2c', 'Приморськ', 'Ветерани футболу четверті в Україні', 'Команда 55+ зіграла фінал кубка Колоса в Берегові, а її тренер став найкращим воротарем турніру.'),
        ('7845272c5f', 'Приморськ', 'Школа №1 отримала нові карти й глобуси', 'Кабінет географії став одинадцятим мультимедійним класом школи. Сюрприз чекав дітей після канікул.'),
    ],
    '10-21': [
        ('c42282cb16', 'Приморськ', 'Сільські голови з’їхалися до Приморська', 'Голови сіл чотирьох районів області радилися з керівництвом ОДА, як розвивати свої території.'),
        ('be2450a5b1', 'Борисівка', 'Соколята привезли бронзу', 'Команда борисівської школи виграла стрільбу й конкурс рятівника на грі Джура і стала третьою.'),
        ('566814bf33', 'Приморськ', 'Європа починається з тебе', 'Двоє вихованців ЦДЮТ стали переможцями обласного конкурсу есе серед сотні робіт.'),
        ('bc2a687b2d', 'Єлисеївка', 'Як хлопців у козаки приймали', 'Соколята і Патріоти змагалися у знанні козацької історії й танцювали гопак. Гомін стояв довго.'),
    ],
    '10-16': [
        ('095a184107', 'Азов', 'У нас — газ. А у вас?', 'У селищі урочисто пустили газ: ще один населений пункт району отримав блага цивілізації.'),
        ('34750adc81', 'Єлисеївка', 'Змагання до Дня захисника', 'Старшокласники показали стройову підготовку й змагалися за програмою спартакіади.'),
        ('0a3135cecb', 'Юр’ївка', 'На Покрову приймали гостей з усього району', 'Покрова, День козацтва і День захисника — свято, що збирало громаду разом.'),
        ('f09cb234b5', 'Приморськ', 'Над морем — «біла» веселка', 'Туманного дня мешканка зняла рідкісне природне явище над морем.'),
    ],
    '10-18': [
        ('b03fc7397d', 'Приморськ', 'Гості з Польщі', 'Польські школярі побачили Обиточну косу й наше море і не могли намилуватися містом.'),
        ('e26f84c300', 'Борисівка', 'Десять років храму на Покрову', 'Свято готували всім селом, і відновлений храм зустрів людей у новому вбранні.'),
        ('90173d27a4', 'Єлизаветівка', 'Покровський хоровод', 'На свято Покрови й козацтва до села з’їхалися понад двісті учасників.'),
        ('6d163adaf2', 'Приморськ', 'Відкрився шаховий гурток', 'У центральній бібліотеці двічі на тиждень учать грати в шахи. Запрошують усіх охочих.'),
    ],
    '10-17': [
        ('ae41a33044', 'Приморськ', 'Хризантеми хрестиком', 'На виставці умільців люди ахали біля вишивок: до двадцяти відтінків ниток в одній квітці.'),
        ('043b0cc228', 'Приморський район', 'Фурор на Покровському ярмарку', 'Павільйон району на головному ярмарку області підкорив гостей піснями й гостинністю.'),
        ('6fca13915b', 'Борисівка', 'Першачків посвятили в козачата', 'Напередодні Дня козацтва малечу вітали батьки й юні «Соколята».'),
        ('0067e90bb6', 'Єлисеївка', 'Акція «Старенький вчитель»', 'Десятикласники прибрали подвір’я вчительки на пенсії, а вона щиро подякувала дітям.'),
    ],
}


def first_sentence(x, limit=120):
    s = re.split(r'(?<=[.!?…])\s', re.sub(r'\s+', ' ', x).strip())[0]
    return s if len(s) <= limit else s[:limit].rsplit(' ', 1)[0] + '…'


def cards_for(md):
    data = json.load(open(os.path.join(ROOT, 'timeline', 'data.json')))
    by_id = {a['n']: a for a in data}
    if md in CURATED:
        return [dict(n=n, year=by_id[n]['d'][:4], place=p, title=t, line=l, photo=by_id[n].get('i', '')) for n, p, t, l in CURATED[md]]
    day = [a for a in data if a['d'][5:] == md and a.get('k') != 'history']
    best = {}
    for a in day:  # one per year: a photo first, then a village, then a longer text
        score = (bool(a.get('i')), bool(a.get('vl')), len(a.get('x', '')))
        if a['d'][:4] not in best or score > best[a['d'][:4]][0]:
            best[a['d'][:4]] = (score, a)
    picks = [a for _, a in sorted(best.values(), key=lambda r: r[0], reverse=True)[:4]]
    return [dict(n=a['n'], year=a['d'][:4], place=(a.get('vl') or ['Приморськ'])[0].split(' (')[0], title=a['t'],
                 line=first_sentence(a.get('x', '')), photo=a.get('i', '')) for a in sorted(picks, key=lambda a: a['d'])]


def plain(s):
    """Post text the way people type it: no «» quotes, no long dashes (the author's wish for FB posts)."""
    s = re.sub(r'\s+[—–-]\s+', ' ', s.replace('«', '').replace('»', '').replace('„', '').replace('“', '').replace('”', ''))
    return re.sub(r'\s+', ' ', s).strip()


def sentence(s):
    s = plain(s).rstrip('.…').rstrip()
    return s if s.endswith(('?', '!')) else s + '.'


def post(cards, date_label, md=''):
    """The FB post; the links sit in the text itself, one tap away (the author's call, 4.11.2026: no more first-comment links)."""
    lead = next((c for c in reversed(cards) if c.get('photo')), cards[-1])  # the linked story: the last one with a photo (the preview shows it)
    lines = [f'📅 Цей день в історії, {date_label}', '', 'Що відбувалося в нашій громаді цього дня в різні роки:', '']
    for c in cards:
        lines.append(f"📍 {c['year']}, {c['place']}. {sentence(c['title'])} {sentence(c['line'])}")
    lines += ['', 'Кожен день громади є в хроніці. Відкрий розділ Цей день в історії і знайди свою історію: '
                  'свого села, своєї школи, свого року.', '',
              # the link goes to one story's own page (its title and photo in the preview), the day feed is one more link:
              # a day with a direct article link brought several times more readers than a day with the home page (20.10.2026)
              f"{sentence(lead['title'])} https://prym.mydom.website/p/{lead['n']}",
              f"Усі історії цього дня: https://prym.mydom.website/{'?day=' + md if md else ''}", '',
              "Громада, яку ми пам'ятаємо 💛💙", '', '#Приморськ #ЦейДеньВІсторії #ХронікаГромади #Приморськ247']
    return '\n'.join(lines) + '\n'


def wrap(d, s, f, width):
    words, lines, cur = s.split(), [], ''
    for w in words:
        trial = f'{cur} {w}'.strip()
        if d.textlength(trial, font=f) <= width:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


def photo_panel(path, w, h):
    im = Image.open(os.path.join(ROOT, path.lstrip('/'))).convert('RGB')
    s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1))
    x, y = (im.width - w) // 2, (im.height - h) // 2
    im = im.crop((x, y, x + w, y + h)).convert('RGBA')
    mask = Image.new('L', (w * 4, h * 4), 0)  # 4x and down: smooth corners (PIL shapes have no antialiasing)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w * 4 - 1, h * 4 - 1), 28 * 4, fill=255)
    im.putalpha(mask.resize((w, h), Image.LANCZOS))
    return im


preview_dir = tempfile.gettempdir()


def make(md, preview=None):
    cards = cards_for(md)
    mm, dd = (int(v) for v in md.split('-'))
    date_label = f'{dd} {MONTHS[mm - 1]}'
    panels = {i: photo_panel(c['photo'], W - 2 * M, 400) for i, c in enumerate(cards) if c['photo']}

    def frame(t):
        im = u.BG.copy().convert('RGBA')
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        # top: the brand on the intro and the finale; on a news card only the place (left) and the year (right)
        # one at a time, never on top of each other: what leaves is gone before the next arrives
        cards_o = []
        for i, c in enumerate(cards):
            end = SLOTS[i + 1] if i + 1 < len(cards) else FINAL
            cards_o.append(u.prog(t, SLOTS[i], SLOTS[i] + .4) * (1 - u.prog(t, end - .4, end)))
        brand = (1 - u.prog(t, SLOTS[0] - .4, SLOTS[0])) + u.prog(t, FINAL, FINAL + .4)
        u.header(lay, d, t, fade=brand)
        for c, o in zip(cards, cards_o):
            if o > 0:
                u.text(d, (M, M + 14), 'ЦЕЙ ДЕНЬ В ІСТОРІЇ', u.MONO(20), u.AMBER, o, track=4)
                u.text(d, (M, M + 44), c['place'], u.font(52), u.CREAM, o)
                u.text(d, (W - M, M + 14), date_label.upper(), u.MONO(20), u.AMBER, o, 'ra', track=4)
                u.text(d, (W - M, M + 44), c['year'], u.font(52), u.CREAM, o, 'ra')
        # the date: large at first, then a small label that stays
        a_big = u.prog(t, .4, 1.2) * (1 - u.prog(t, 2.6, 3.1))
        if a_big > 0:
            y = 330 - 30 * (1 - u.prog(t, .4, 1.2))
            u.text(d, (M - 6, y), date_label, u.font(150), u.AMBER, a_big)
            u.text(d, (M, y + 190), 'Що було цього дня в громаді', u.font(48, 700), u.CREAM, a_big)
            u.text(d, (M, y + 260), 'у різні роки — з архіву хроніки', u.font(34, 600), u.MINT, a_big)
        # the cards
        for i, c in enumerate(cards):
            st = SLOTS[i]
            a = u.prog(t, st, st + .7) * (1 - u.prog(t, st + CARD - .5, st + CARD))
            if a <= 0:
                continue
            dx = int(70 * (1 - u.prog(t, st, st + .9)) - 50 * u.prog(t, st + CARD - .5, st + CARD))
            if i in panels:  # a large photo, the story under it
                p = panels[i].copy()
                p.putalpha(p.getchannel('A').point(lambda v: int(v * a)))
                lay.alpha_composite(p, (M + dx, 250))
                ty, f, g = 690, u.font(56), u.font(34, 600)
            else:  # the story alone, large, in the middle of the frame
                f, g = u.font(76), u.font(40, 600)
                n1 = len(wrap(d, c['title'], f, W - 2 * M)[:3])
                n2 = len(wrap(d, c['line'], g, W - 2 * M)[:3])
                block = n1 * int(f.size * 1.18) + 28 + n2 * int(g.size * 1.32)
                ty = 250 + (690 - block) // 2
            lines = wrap(d, c['title'], f, W - 2 * M)[:3]
            lh = int(f.size * 1.18)
            for k, line in enumerate(lines):
                u.text(d, (M + dx, ty + k * lh), line, f, u.CREAM, a)
            for k, line in enumerate(wrap(d, c['line'], g, W - 2 * M)[:3]):
                u.text(d, (M + dx, ty + len(lines) * lh + 28 + k * int(g.size * 1.32)), line, g, u.MINT, a)
        # progress: four dots, the current one amber
        a = u.prog(t, 3.0, 3.5) * (1 - u.prog(t, FINAL - .4, FINAL))
        cur = max([i for i, st in enumerate(SLOTS) if t >= st] or [0])
        x = M
        for i in range(len(cards)):
            if i == cur:
                fill = max(0, min(1, (t - SLOTS[i]) / CARD))  # linear: a timer, not an animation
                u.rrect(lay, (x, H - M - 14, x + 64, H - M), 7, u.CREAM + (int(70 * a),))
                if fill > 0:
                    u.rrect(lay, (x, H - M - 14, x + max(14, int(64 * fill)), H - M), 7, u.AMBER + (int(255 * a),))
                x += 64 + 12
            else:
                u.rrect(lay, (x, H - M - 14, x + 14, H - M), 7, (u.AMBER + (int(255 * a),)) if i < cur else (u.CREAM + (int(90 * a),)))
                x += 14 + 12
        # finale: invitation + address
        steps = [FINAL + k * FSTEP for k in range(4)]  # headline, the invitation, the address, the slogan
        a = u.prog(t, steps[0], steps[0] + .8)
        if a > 0:
            y = 330 - 30 * (1 - a)
            u.text(d, (W // 2, y), 'Кожен день громади —', u.font(66), u.CREAM, a, 'ma')
            u.text(d, (W // 2, y + 80), 'у хроніці на сайті', u.font(66), u.AMBER, a, 'ma')
            a1 = u.prog(t, steps[1], steps[1] + .7)
            y1 = 526 + 20 * (1 - a1)
            u.text(d, (W // 2, y1), 'Відкрий «Цей день в історії»', u.font(36, 600), u.MINT, a1, 'ma')
            u.text(d, (W // 2, y1 + 48), 'і знайди свою історію', u.font(36, 600), u.MINT, a1, 'ma')
            a2 = u.prog(t, steps[2], steps[2] + .7)
            bw, bh = 520, 84
            yy = 700 + 20 * (1 - a2)
            u.rrect(lay, (W // 2 - bw // 2, yy, W // 2 + bw // 2, yy + bh), 22, u.CREAM + (int(255 * a2),))
            u.text(d, (W // 2, yy + bh // 2), 'prym.mydom.website', u.font(38), u.GREEN, a2, 'mm')
            a3 = u.prog(t, steps[3], steps[3] + .9)
            u.text(d, (W // 2, 840 + 14 * (1 - a3)), "Громада, яку ми пам’ятаємо", u.font(34, 600), u.MINT, a3, 'ma')
        im.alpha_composite(lay)
        return im.convert('RGB')

    if preview:  # stills at the given seconds, no video
        for t in preview:
            frame(t).save(os.path.join(preview_dir, f'preview-{t:04.1f}.png'))
        return preview_dir

    # the soundtrack from the kit: pad, a chime for the date, a rising note per card, the chord with the address
    track = snd.track(DUR)
    snd.pad(track, DUR)
    snd.chime(track, 1.0)
    for i, st in enumerate(SLOTS[:len(cards)]):
        snd.add(track, st + .1, 2.5, snd.bell(snd.NOTES[i]), .22)
    for k, f in enumerate(FINAL_NOTES):
        snd.add(track, FINAL + k * FSTEP + .05, 2.5, snd.bell(f), .16)
    snd.chord(track, FINAL + 3 * FSTEP + .05)
    tmp = tempfile.mkdtemp()
    wav = os.path.join(tmp, 'track.wav')
    snd.OUT = tmp
    snd.save(track, 'track.wav')
    for i in range(int(DUR * FPS)):
        frame(i / FPS).save(os.path.join(tmp, f'{i:04d}.png'))
    frame(SLOTS[-1] + 2).save(os.path.join(u.HERE, f'day-{md}.png'))
    open(os.path.join(u.HERE, f'day-{md}.txt'), 'w').write(post(cards, date_label, md))
    out = os.path.join(u.HERE, f'day-{md}.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(tmp, '%04d.png'), '-i', wav,
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-c:a', 'aac', '-b:a', '192k', '-shortest',
                    '-movflags', '+faststart', out], check=True)
    return out


if __name__ == '__main__':
    assert plain('Над морем — «біла» веселка') == 'Над морем біла веселка'
    assert sentence('У нас – газ. А у вас?') == 'У нас газ. А у вас?' and sentence('шляхом повного…') == 'шляхом повного.'
    md = sys.argv[1] if sys.argv[1:] else datetime.date.today().strftime('%m-%d')
    print(make(md))
