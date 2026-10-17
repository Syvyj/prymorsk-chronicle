"""Golden check of extract() on one page per engine (WordPress, custom PHP, phpBB-like forum, Joomla K2, uCoz).

    python3 test_extract.py

Needs the local archives (not in git). A failure after a cleaner/extractor change means a regression
on that engine: look at the page before updating the expected values.
"""
import os, sys
from extract_articles import extract, ROOT

CASES = [  # site, path, title, date (None: mirrors get it from the address later, in the main loop), start of text
    ('archive_mrprim', 'archive_mrprim/80_info-tsentr_novini_331-40-rokiv-z-momentu-stvorennya-ukrajinskoji-gelsinskoji-grupi/index.html',
     '40 років з моменту створення Української Гельсінської групи', '2016-11-09', 'Сьогодні ми відначаємо 40-річчя'),
    ('archive_pro_prim', 'archive_pro_prim/80_content_php_id_5531/index.html',
     'У школах Приморська урочисто відзначили День Соборності України', '2020-01-22', 'Саме 22 січня у 1919 році'),
    ('primorsk_forum', 'mirror/primorsk_zp/primorsk.zp.ua_80_forum_13-fludilka_v_primorske__978-ostav_svoi_sled__0cb59e.html',
     'Оставь свой след!!!!!', None, 'Здесь посетители оставляют'),
    ('tavriya', 'mirror/tavriya/tavriya.co.ua_index.php_primorsk_item_102-прошел-чемпионат-по-мини-футболу-в-приморском-районе_fb6379.html',
     'Прошел чемпионат по мини-футболу в Приморском районе', '2012-03-16', 'Нововасильевские футболисты'),
    ('primroo', 'mirror/primroo/primroo.ucoz.ua_news_01_02_2016_2016-02-02-637_4cdd8b.html',  # title is a date on the page
     'Увага! 1 лютого о 12:00 розпочалася реєстрація осіб для участі в зовнішньому незалежному оцінюванні 2016 року, яка…',
     None, 'Увага!\n1 лютого'),
]

if __name__ == '__main__':
    bad = 0
    for site, path, title, date, start in CASES:
        a = extract(os.path.join(ROOT, path), site)
        got = (a['title'], a['date'] if date else None, a['text'][:len(start)])
        if got != (title, date, start):
            bad += 1
            print(f'FAIL {site}: {got!r}\n   expected {(title, date, start)!r}')
    print('ok' if not bad else f'{bad} failed')
    sys.exit(1 if bad else 0)  # stops build.sh
