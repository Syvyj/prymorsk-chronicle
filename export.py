"""Open data export of the chronicle for researchers: timeline/export/chronicle.csv + fields.md.

Called by extract_articles.py with the full timeline (excerpts not trimmed). Same privacy as the portal:
names are already shortened and phones/emails masked in titles and excerpts.
"""
import csv, os

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'timeline', 'export')
FIELDS = [  # column, source key, description
    ('id', 'n', 'стабільний ідентифікатор запису; сторінка: p/<id>.html'),
    ('date', 'd', 'дата публікації, РРРР-ММ-ДД'),
    ('date_error_days', 'e', 'якщо дата оцінена (за порядком записів WordPress) — на скільки днів вона може помилятися; порожньо = точна'),
    ('source', 's', 'ключ джерела (назви — timeline/meta.js, SOURCES)'),
    ('source_host', 'ext', 'для обласних ЗМІ: сайт видання'),
    ('title', 't', 'заголовок (українською; для російськомовних — переклад)'),
    ('title_original', 'to', 'оригінальний заголовок, якщо перекладено'),
    ('excerpt', 'x', 'початок тексту (до 260 символів)'),
    ('original_url', 'u', 'адреса оригіналу (шукати в Wayback Machine)'),
    ('villages', 'vl', 'згадані села громади, через «; »'),
    ('topics', 'c', 'теми (автоматично, за ключовими словами), через «; »'),
    ('photos', 'ph', 'скільки фото в тексті'),
    ('has_video', 'v', '1 = у тексті є відео'),
]


def write(timeline):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, 'chronicle.csv'), 'w', encoding='utf-8-sig', newline='') as f:  # BOM: Excel opens Cyrillic right
        w = csv.writer(f)
        w.writerow([c for c, _, _ in FIELDS])
        for t in timeline:
            w.writerow(['; '.join(v) if isinstance(v := t.get(k, ''), list) else v for _, k, _ in FIELDS])
    with open(os.path.join(OUT, 'fields.md'), 'w', encoding='utf-8') as f:
        f.write('# Хроніка Приморська: відкриті дані\n\n`chronicle.csv` (UTF-8, кома як роздільник), один рядок на запис.\n'
                'Імена скорочено, телефони й email приховано так само, як на порталі.\n\n| Поле | Опис |\n|---|---|\n')
        f.writelines(f'| `{c}` | {d} |\n' for c, _, d in FIELDS)
    return len(timeline)


if __name__ == '__main__':
    import json
    print('rows:', write(json.load(open(os.path.join(ROOT, 'timeline', 'data.json'), encoding='utf-8'))))
