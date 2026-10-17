"""Pull title / date / body text of every real article into articles.json (input for filtering, portal, bot).

    python3 extract_articles.py
"""
import json, os, re, html, collections, glob
from urllib.parse import unquote, quote
import clean_article
import names

ROOT = os.path.dirname(os.path.abspath(__file__))
# class token of the article body container per site
BODY = {'archive_mrprim': 'entry-content', 'archive_prim24': 'entry-content', 'archive_pro_prim': 'content'}
# sites rescued later with wayback_mirror.py: site key -> (mirror dir, body class, URLs that are content, kind)
MIRRORS = {
    'primorsk_in': ('primorsk_in', 'art-article', r'primorsk\.in\.ua(:80)?/(?!category/|page/|tag/|author/|\d{4}/\d{2}/?(page/\d+/?)?$)[^?]+$', 'news'),
    'primorsk_zp': ('primorsk_zp', 'full-article', r'/(news/\d+|component/content/article)/\d+-', 'news'),
    'imsu': ('imsu_history', 'newsitem_text', r'primorskij-rajon/.+\.html$', 'history'),
    'primorsk_forum': ('primorsk_zp', 'msgtext', r'/forum/\d+-[^/]+/\d+-', 'news'),
    'prym': ('prym', 'entry-content', r'prym\.in\.ua/\?(p|page_id)=\d+$', 'history'),
    # school / education sites on uCoz: news entries carry their date in the URL (.../2017-03-03-131)
    'rcdt': ('rcdt', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'school3': ('school3', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'licey': ('licey', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'school2': ('school2', 'eMessage', r'ucoz\.ua(:80)?/(publ/[^?]+|photo/[a-z_]+[^?]*)$', 'news'),  # no dated news here: articles + photo albums
    'primrda': ('primrda', 'articles', r'primrda\.gov\.ua(:80)?/(news|kulturni_zakhodi|gordist_primorskogo_raionu)/\d+-', 'news'),
    'tavriya': ('tavriya', 'itemFullText', r'/index\.php/primorsk/item/\d+-', 'news'),
    'primroo': ('primroo', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'travel': ('travel_mrprim', 'entry-content', r'travel\.mrprim\.zp\.ua(:80)?/\?(p|page_id)=\d+$', 'history'),
    'prim24_blog': ('prim24_sub', 'entry-content', r'[?&]p=\d+', 'news'),
    # village schools and education sites saved in 2026 (Wayback for the dead ones, live_mirror.py for the living)
    'yelyzavetivka': ('yelyzavetivka', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'radolivka': ('radolivka', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'zelenivka': ('zelenivka', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'partyzany': ('partyzany', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'rmc': ('rmc', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'fisra': ('fisra', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'nelgivka': ('nelgivka', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'inzivka': ('inzivka', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'yeliseivka': ('yeliseivka', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'borysivka': ('borysivka', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'orlivka': ('orlivka', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'primorskstep': ('primorskstep', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'cdut': ('cdut', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'marynivka': ('marynivka', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    'yurivka': ('yurivka', 'eMessage', r'/(news|blog|publ)/[^?]*(\d{4}-\d{2}-\d{2}-\d+|\d+-\d+-\d+)$', 'news'),
    'school1': ('school1', 'eMessage', r'/(news|blog|publ)/[^?]*(\d{4}-\d{2}-\d{2}-\d+|\d+-\d+-\d+)$', 'news'),
    'preslav_bzosh': ('preslav_bzosh', 'eMessage', r'/(news|blog|publ)/[^?]*(\d{4}-\d{2}-\d{2}-\d+|\d+-\d+-\d+)$', 'news'),
    'osvita_otg': ('osvita_otg', 'eMessage', r'/(news|blog|publ)/[^?]*\d{4}-\d{2}-\d{2}-\d+$', 'news'),
    # Blogspot: a school library, a school health blog, abandoned teachers' blogs (live_mirror.py --blogs)
    'gymn2_library': ('gymn2_library', 'post-body', r'\.blogspot\.com/', 'news'),
    'school3_health': ('school3_health', 'post-body', r'\.blogspot\.com/', 'news'),
    'blog_math_prim': ('blog_math_prim', 'post-body', r'\.blogspot\.com/', 'news'),
    'blog_pe_gymn2': ('blog_pe_gymn2', 'post-body', r'\.blogspot\.com/', 'news'),
    'blog_labour': ('blog_labour', 'post-body', r'\.blogspot\.com/', 'news'),
    'blog_primary': ('blog_primary', 'post-body', r'\.blogspot\.com/', 'news'),
    'blog_art': ('blog_art', 'post-body', r'\.blogspot\.com/', 'news'),
    'blog_bulgarian': ('blog_bulgarian', 'post-body', r'\.blogspot\.com/', 'news'),
    'blog_english': ('blog_english', 'post-body', r'\.blogspot\.com/', 'news'),
    'blog_ukrainian': ('blog_ukrainian', 'post-body', r'\.blogspot\.com/', 'news'),
    # pages only Common Crawl kept (cc_fetch.py): read exactly like the original site
    'cc_mrprim': ('cc_mrprim', 'entry-content', r'/\?p=\d+$', 'news'),
    'cc_pro_prim': ('cc_pro_prim', 'content', r'content\.php\?id=\d+$', 'news'),
    'cc_primrda': ('cc_primrda', 'articles', r'/(news|kulturni_zakhodi|gordist_primorskogo_raionu)/\d+-', 'news'),
}
CC_AS = {'cc_mrprim': 'archive_mrprim', 'cc_pro_prim': 'archive_pro_prim', 'cc_primrda': 'primrda'}
BLOGS = {'gymn2_library', 'school3_health', 'blog_math_prim', 'blog_pe_gymn2', 'blog_labour', 'blog_primary', 'blog_art', 'blog_bulgarian', 'blog_english', 'blog_ukrainian'}
# a school site speaks of its own village even when the text never names it
SITE_VILLAGE = {'yelyzavetivka': 'Єлизаветівка', 'radolivka': 'Радолівка', 'zelenivka': 'Зеленівка',
                'partyzany': 'Новопавлівка (Партизани)', 'nelgivka': 'Нельгівка', 'inzivka': 'Інзівка',
                'yeliseivka': 'Єлисеївка', 'borysivka': 'Борисівка', 'orlivka': 'Орлівка',
                'marynivka': 'Маринівка', 'yurivka': "Юр'ївка", 'preslav_bzosh': 'Преслав'}
for _k, _v in MIRRORS.items():
    BODY[_k] = _v[1]
MONTHS_RU_UK = {m: i for i, ms in enumerate([('январ', 'січ'), ('феврал', 'лют'), ('март', 'берез'), ('апрел', 'квіт'),
                                               ('ма[яй]', 'трав'), ('июн', 'черв'), ('июл', 'лип'), ('август', 'серп'),
                                               ('сентябр', 'верес'), ('октябр', 'жовт'), ('ноябр', 'листоп'), ('декабр', 'груд')], 1) for m in ms}
# Prymorsk + villages of the former Prymorsk district/community (collected from the archives themselves)
LOCAL = re.compile(r'приморськ|приморск|приморськ\w*|борисівк|борисовк|преслав|подспор|підспір|комишуватк|камышеватк'
                   r'|лозанівк|лозуватк|лозоватк|орлівк|набережн[еому]|новоолексіївк|в[’\']?ячеславк|інзівк|банівк'
                   r'|болгарк|райнівк|маринівк|мариновк|калинівк|калиновк|підгірн|подгорн|радолівк|радоловк|єлисеївк|елисеевк|єлизаветівк|мануйлівк|нельгівк|коларівк|зеленівк|ногайськ|ногайск', re.I)
REGION = re.compile(r'запоріз|запорож|бердянськ|бердянск|мелітопол|мелитопол|приазов', re.I)


PLACEHOLDER = re.compile(r'lorem ipsum|consectetur adipiscing|this is an example page|welcome to wordpress'
                         r'|hello world|this is your first post|just another wordpress site', re.I)


LISTING_URL = re.compile(r'[?&]m=\d{6}|^https?://[^/]+/20\d\d/(\d\d/(\d\d/)?)?$|cool_timeline|/(category|tag|author)/')
ABOUT_TITLE = re.compile(r'^(Депутатський корпус|Депутатські комісії|Графік прийому громадян.*|Публічна інформація|'
                         r'Запит на отримання публічної інформації|РЕГЛАМЕНТ роботи Приморської міської ради.*|'
                         r'[^,]{3,60},\s*(перший |провідний |головний )?(заступник|начальник|спеціаліст|керуюч|секретар|юрист|бухгалтер).*)$', re.I)  # staff cards


EXCERPT_ONLY = set()  # mirrored private media without the editors' consent: headline, excerpt, link
REGIONAL_UNTIL = '2023-01-01'  # hard cap; in practice regional news end with the last local record (see below)


def regional_body(url):
    """Clean full text of a regional article if regional_fulltext.py fetched it (allowed sources only)."""
    import regional_fulltext
    path = regional_fulltext.page_path(url)
    host = regional_fulltext.origin_host(url)
    if not regional_fulltext.ALLOWED.search(host) or not os.path.exists(path) or not os.path.getsize(path):
        return ''
    raw = read_html(path)
    best = ''
    for cls in ('article-content', 'field-name-body', 'article-details__text', 'entry-content', 'post-content', 'article-body', 'news-text', 'content'):
        h = clean_article.cut_tail(clean_article.clean(raw, cls, path, tries=3))  # no tag/related-posts tails
        if len(clean_article.to_text(h)) > len(clean_article.to_text(best)):
            best = h
    if len(clean_article.to_text(best)) < 150:
        return ''
    return names.shorten(clean_article.mask_private(best, 'regional'))


# navigation / service pages of the history and tourist sites: lists of links, phone numbers, "how to use the map"
# pages whose own title does not say what the text is (author's choice of a better one)
TITLE_FIX = {'http://www.prym.in.ua/?p=802': 'Довгий шлях до храму'}  # the School No.1 info board carries the story of the lost church
SERVICE_TITLE = re.compile(r'^(Інформаційні дошки|Відео про історію нашого міста|Екскурсійні маршрути|Про події та історії|'
                           r'Туристічні вказівники|Туристичні вказівники|Контактні телефони|Медичні заклади)$')


# typos of the sources themselves, by article id: {field: (wrong, right)}
TEXT_FIX = {
    'b95944cf95': {'t': ('01.02.3033', '01.03.2022')},              # zoda.gov.ua: the 1 March 2022 bulletin
    'ec39501b5d': {'x': ('3 0.08.2021', '30.08.2021')},
    '99d5cd55ab': {'t': ('детальніше...', 'Ми обираємо, нас обирають… (13 округ)')},  # the title was the "read more" link
}


def tidy_title(t):
    """Typing debris around a title, not the author's style ("!!!" and "…" stay)."""
    t = re.sub(r'^[\s*•\-–—|]+', '', t)                 # "* До уваги абітурієнтів!", "- тиждень географії…"
    t = re.sub(r'[\s,;:\-–—|/]+$', '', t)                # "…заробітної плати», -"
    t = re.sub(r'\s+([,;:!?)])', r'\1', t)               # "Сьогодні ,15.05" / "Новим Роком !"
    t = re.sub(r'([,;])(?=[А-ЯІЇЄҐа-яіїєґA-Za-z])|(?<!\d)([,;])(?=\d)', lambda m: (m.group(1) or m.group(2)) + ' ', t)  # "…15.05,на"; "1,5" stays
    t = re.sub(r'(?<=[а-яіїєґ])\.\.(?=\s)', '.', t)      # "ім.. Тараса"
    return t[:1].upper() + t[1:]


assert tidy_title('- тиждень, 1,5 грн') == 'Тиждень, 1,5 грн' and tidy_title('Сьогодні ,15.05,на вулицях') == 'Сьогодні, 15.05, на вулицях'


# the 2021 almanac of the local historians' union (almanac.py makes almanac/almanac.json from the PDF)
IN_ALMANAC = {'довгий шлях до храму', 'жизнь, оставившая добрую память'}  # the same articles on prym.in.ua: the book's text wins


def almanac():
    path = os.path.join(ROOT, 'almanac', 'almanac.json')
    if not os.path.exists(path):
        return []
    items = []
    for x in json.load(open(path, encoding='utf-8')):
        body = f'<p class="byline">{html.escape(x["author"])} · Альманах I Спілки краєзнавців Приморська, 2021, с. {x["pages"]}</p>\n' + x['html']
        imgs = re.findall(r'<img src="(/[^"]+)"', body)
        items.append({'site': 'almanac', 'path': f'almanac/{x["slug"]}', 'url': '', 'title': x['title'], 'to': x['original'],
                      'date': x['date'], 'date_est': 0, 'kind': 'history', 'scope': 'local', 'html': body,
                      'text': clean_article.to_text(x['html']), 'thumb': imgs[0] if imgs else '/media/almanac/cover.jpg'})
    return items


# orders (школа: lists of pupils by name; council: office paperwork) are documents, not chronicle (author's call)
ORDER_TITLE = re.compile(r'^\s*(?:\([^)]*\)\s*)?(?:наказ|приказ)\b', re.I)


def kind(a):
    """news | about (how the community was organised) | listing (archive index or service page, not content)"""
    if SERVICE_TITLE.match(a['title']) or ORDER_TITLE.match(a['title']):
        return 'listing'
    if ABOUT_TITLE.match(a['title']) and a['site'] == 'archive_mrprim':  # also the council pages only Common Crawl kept
        return 'about'
    if a.get('kind'):
        return a['kind']
    if LISTING_URL.search(a['url']):
        return 'listing'
    return 'news'


# on the council's own site the town is implied: its bodies, budget, districts and venues mark a post as local
COUNCIL_LOCAL = re.compile(r'міськ\w* рад|міськ\w* голов|виконком|виконавч\w* комітет|\bОТГ\b|громад[аиі]\b|депутат|сесі[яїю]|'
                           r'округ\s*№|паспорт\w* бюджетн|УСЗН|ЦНАП|парк\w* Ювілейн|будинк\w* культури|стадіон|староста', re.I)


# personal notices about named officials that must not be republished
HIDDEN = re.compile(r'про початок проходження перевірки', re.I)  # lustration check notices (2016), one per person


# topics: stems in Ukrainian and Russian (pro.primorsk.biz often wrote in Russian)
TOPICS = {
    'Влада': r'сесі[яїюі]|депутат|міськ\w* голов|мэр|виконком|виконавч\w* комітет|рішенн\w* ради|решени\w* совет|райрад|райсовет|громадськ\w* слухан|общественн\w* слушан|розпорядженн|регуляторн|бюджет\w* програм',
    'Культура': r'культур|концерт|фестивал|свят[оа]|праздник|будин\w* культури|дом\w* культуры|бібліотек|библиотек|виставк|выставк|вистав[аи]|театр|музе[йюя]|хор\b|ансамбл|пісн|песн|танц|поет|поэт|книг',
    'Спорт': r'спорт|турнір|турнир|змаган|соревнован|чемпіонат|чемпионат|футбол|волейбол|баскетбол|шахмат|борц|боротьб|борьб|бокс|легкоатлет|стадіон|стадион|забіг|забег|кубок|олімпіад\w* з фізкульт|спартакіад',
    'Туризм і море': r'турист|туризм|курорт|пляж|відпочин|отдых|база відпочинку|базы отдыха|курортн\\w* сезон|пляжн\\w* сезон|оздоровч\\w* сезон|набережн|азовськ\w* мор|азовск\w* мор|море\b|морі\b|коса|екскурс|экскурс|маршрут',
    'Освіта': r'школ|учн[іяь]|ученик|вчител|учител|педагог|садоч|дитяч\w* садк|детск\w* сад|освіт|образован|урок|випускн|выпускн|олімпіад|олимпиад|ЗНО\b|ліце|лице[йя]|коледж|колледж',
    'Молодь і діти': r'молод|дітей|діти|дитин|детей|дети|ребен|школяр|школьник|підліт|подрост|студент|табір|лагер|скаут|пласт',
    'Здоров\'я': r'лікар|больниц|врач|медицин|медичн|здоров|амбулатор|поліклін|поликлин|вакцин|щеплен|прививк|covid|коронавірус|коронавирус|донор|аптек|хвор|болезн',
    'Благоустрій і ЖКГ': r'благоустр|ремонт|дорог|асфальт|освітлен|освещен|водопост|водопровод|каналізац|канализац|вивіз сміття|вывоз мусора|смітт|мусор|сквер|парк\w*\b|тротуар|газопост|газифік|опален|отоплен|ЖКГ|ЖКХ|комунал|коммунал|ОСББ',
    'Безпека': r'поліці|полици|ДТП|аварі|авари|пожеж|пожар|ДСНС|ГСЧС|МНС|МЧС|рятувальн|спасател|злочин|преступ|крадіж|краж|шахра|мошенни|затриман|задержан|суд\b|прокурат|потонул|утонул',
    'Оборона і АТО': r'\bАТО\b|ООС|військов|военн|воїн|воин|прикордон|пограни|армі[яїю]|арми[яи]|мобілізац|мобилизац|ветеран|волонтер|захисник|защитник|ВПО|переселен',
    'Соціальна сфера': r'пенсі|пенси|субсиді|субсиди|соціальн|социальн|УСЗН|малозабезпеч|малообеспеч|інвалід|инвалид|допомог\w* сім|багатодітн|многодетн|пільг|льгот',
    'Економіка і бізнес': r'підприєм|предприним|бізнес|бизнес|ФОП|аграр|фермер|урожа|зернов|худоб|скот|сільськ\\w* господар|сельск\\w* хозяйств|посів|посев|податк|налог|інвестиц|инвестиц|ринок|рынок|торгівл|торговл|вакансі|вакансии|зайнятост|занятост|тариф',
    'Історія і пам\'ять': r'істор|истори|пам.ят|памят|річниц|годовщин|ювіле|юбиле|загибл|погибш|голодомор|ногайськ|ногайск|засновання|основания города|краєзнав|краевед|археолог|курган|архів|архив',
    'Екологія': r'еколог|эколог|природ|довкілл|сміттєзвалищ|свалк|дерев[ао]|озелен|субботник|суботник|толок|chistyj|браконьєр|браконьер|риб[аиоу]\b|рыб[аыу]\b',
    'Громадські ініціативи': r'громадськ\w* організац|общественн\w* организац|\bГО\b|ініціатив|инициатив|громадськ\w* бюджет|общественн\w* бюджет|грант|проект\w* громад|активіст|активист|петиці|петици|відкрите місто',
}
TOPIC_RE = {k: re.compile(v, re.I) for k, v in TOPICS.items()}
# villages of the former Prymorsk district/community: canonical name -> stems (uk + ru)
VILLAGES = {
    'Борисівка': r'борисівк|борисовк', 'Преслав': r'преслав', "Підспір'я": r'подспор|підспір|подспорь',
    'Комишуватка': r'комишуватк|камышеватк|комишеватк', 'Лозанівка': r'лозанівк|лозановк', 'Лозуватка': r'лозуватк|лозоватк',
    'Орлівка': r'орлівк|орловк', 'Набережне': r'\bнабережн(е|ого|ому|ое)\b', 'Новоолексіївка': r'новоолексіївк|новоалексеевк',
    'В\'ячеславка': r'в[’\']?ячеславк|вячеславк', 'Інзівка': r'інзівк|инзовк', 'Банівка': r'банівк|бановк',
    'Софіївка (Болгарка, Коларівка)': r'\bболгарк|\bсофіївк|\bсофиевк|коларівк|коларовк', 'Райнівка': r'райнівк|райновк', 'Єлизаветівка': r'єлизаветівк|елизаветовк',
    'Мануйлівка': r'мануйлівк|мануйловк', 'Нельгівка': r'нельгівк|нельговк',
    'Зеленівка': r'зеленівк|зеленовк', 'Новопавлівка (Партизани)': r'\bпартизан(и|ах|ів|ська|ській|ської)\b|\bпартизаны\b|новопавлівк|новопавловк',
    'Гюнівка': r'гюнівк|гюновк', "Юр'ївка": r"юр['’]?ївк|юрьевк",
    'Радолівка': r'радолівк|радоловк', 'Азов': r'\b(?:с\.|смт\.?|село|селі|села|селом|селе|поселк\w*|посел\w*|селищ\w*)\s*Азов(?:і|у|а|е)?\b',
    'Калинівка': r'калинівк|калиновк', 'Маринівка': r'маринівк|мариновк', 'Підгірне': r'підгірн|подгорн', 'Петрівка': r'петрівк|петровк', 'Єлисеївка': r'єлисеївк|елисеевк',
}
VILLAGE_RE = {k: re.compile(v, re.I) for k, v in VILLAGES.items()}


def topics(title, text):
    """Up to 3 topics: a hit in the title counts 3, each hit in the first part of the text counts 1; need >= 3."""
    body = text[:2500]
    score = {k: 3 * len(r.findall(title)) + len(r.findall(body)) for k, r in TOPIC_RE.items()}
    return [k for k, v in sorted(score.items(), key=lambda kv: -kv[1]) if v >= 3][:3]


def villages(title, text):
    """In the title, twice in the text, or as the one village of the lead (the first sentence names what the story is about;
    a lead that lists several villages — football rounds, power cuts — is a list, not a subject)."""
    lead = re.split(r'(?<=[.!?])\s', text.strip(), 1)[0][:300]
    in_lead = [k for k, r in VILLAGE_RE.items() if r.search(lead)]
    return [k for k, r in VILLAGE_RE.items() if r.search(title) or len(r.findall(text)) >= 2 or in_lead == [k]]


assert villages('У нас – газ. А у вас?', 'На прошлой неделе торжественно пущен газ в поселке Азов. Потом Камышеватка и Камышеватку.') == ['Комишуватка', 'Азов']
assert villages('Свято', 'Учні привітали ветеранів. Згодом поїхали до Азовського моря.') == []
assert villages('Результати туру', 'Зіграли Борисівка, Преслав і Нельгівка. Далі буде.') == []


def scope(title, text, site=''):
    """local: about Prymorsk area; region: Zaporizhzhia oblast / neighbours; general: national or world news."""
    if site == 'archive_mrprim' and not REGION.search(title) and COUNCIL_LOCAL.search(title + ' ' + text[:1500]):
        return 'local'
    if LOCAL.search(title) or len(LOCAL.findall(text)) >= 2:
        return 'local'
    if REGION.search(title) or LOCAL.search(text) or len(REGION.findall(text)) >= 2:
        return 'region'
    return 'general'


def clean(t):
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    return re.sub(r'\s*\n\s*', '\n', t).strip()


def featured(raw, path):
    """WordPress puts the post's main photo above the body: first local photo anywhere on the page."""
    for src in re.findall(r'<img\b[^>]*?\ssrc="([^"]+)"', raw):
        if src.startswith('/media/'):
            f = os.path.join(ROOT, unquote(src[1:]))
        elif not re.match(r'(https?:)?//|data:', src):
            f = os.path.join(os.path.dirname(path), unquote(src.split('?')[0]))
        else:
            continue
        if os.path.isfile(f) and os.path.getsize(f) > 8000 and not re.search(r'logo|icon|banner|button|avatar', f, re.I):
            return clean_article.published(f)
    return ''


def thumb(body, path):
    """First real photo of the cleaned body (its img srcs are already verified local files)."""
    for src in re.findall(r'<img src="(/[^"]+)"', body):
        f = os.path.join(ROOT, unquote(src[1:]))
        if os.path.getsize(f) > 8000 and not re.search(r'logo|icon|banner|button|avatar', f, re.I):
            return src
    return ''


MON = {m: i for i, ms in enumerate([('січ', 'янв'), ('лют', 'фев'), ('бер', 'мар'), ('кві', 'апр'), ('тра', 'май', 'мая'),
                                    ('чер', 'июн'), ('лип', 'июл'), ('сер', 'авг'), ('вер', 'сен'), ('жов', 'окт'),
                                    ('лис', 'ноя'), ('гру', 'дек')], 1) for m in ms}


def day_month(s):
    """'28Лют' / '21 Фев' / 'Чер22017' -> (day, month, year|None)"""
    s = s.lower()
    m = re.search(r'(\d{1,2})\s*([а-яіїє]{3})', s)
    if m and m.group(2) in MON:
        return int(m.group(1)), MON[m.group(2)], None
    m = re.search(r'([а-яіїє]{3})\s*(\d{1,2})\s*(20\d\d)', s)  # month-first variant: 'Чер' '2' '2017'
    if m and m.group(1) in MON:
        return int(m.group(2)), MON[m.group(1)], int(m.group(3))
    return None


def fill_dates(arts):
    """Undated WordPress posts: post ids grow over time, so interpolate between dated neighbours;
    then snap to the day/month printed under the title when we have it."""
    import bisect, datetime as dt
    pts = sorted((a['pid'], dt.date.fromisoformat(a['date'])) for a in arts if a['pid'] and a['date'])
    # ponytail: running max smooths the few out-of-order ids (drafts published late); fine for "which week"
    ids, days = [], []
    for pid, d in pts:
        ids.append(pid)
        days.append(max(d, days[-1]) if days else d)
    for a in arts:
        if a['date'] or not a['pid'] or not ids:
            continue
        i = bisect.bisect_left(ids, a['pid'])
        if i == 0 or i == len(ids):
            est, window = days[min(i, len(ids) - 1)], 9999
        else:
            (i0, d0), (i1, d1) = (ids[i - 1], days[i - 1]), (ids[i], days[i])
            est, window = d0 + (d1 - d0) * ((a['pid'] - i0) / (i1 - i0)), (d1 - d0).days
        if a['dm']:
            day, mon, year = a['dm']
            cands = []
            for y in ([year] if year else [est.year - 1, est.year, est.year + 1]):
                try:
                    cands.append(dt.date(y, mon, day))
                except ValueError:
                    pass
            if cands:
                a['date'] = min(cands, key=lambda c: abs((c - est).days)).isoformat()
                continue
        # date_est = how many days the true date may be off (0/1 = neighbours posted the same day)
        a['date'], a['date_est'] = est.isoformat(), window if window > 1 else False


def excerpt(text):
    # pro_prim bodies start with "title, author, views, dd.mm.yy | hh:mm [Поделиться ссылкой:]" — drop that header
    m = re.search(r'\d{1,2}\.\d{2}\.\d{2} \| \d{2}:\d{2}\s*(Поделиться ссылкой:)?', text[:400])
    return (text[m.end():] if m else text).strip()[:260]


def title_from_body(body):
    """uCoz news of the education department use the date as the entry title; the real one is the
    leading bold paragraph (short ones like "Увага!" get the first sentence after them) or the first sentence."""
    txt = lambda h: re.sub(r'\s+([,.;:!?])', r'\1', clean(html.unescape(re.sub(r'<[^>]+>', ' ', h))))
    lead = re.match(r'\s*<p>\s*<strong>(.*?)</strong>\s*</p>\s*', body, re.S)
    head, rest = (txt(lead.group(1)).strip(' .'), body[lead.end():]) if lead else ('', body)
    first = re.split(r'(?<=[.!?])(?<![\s(][А-ЯІЇЄҐ]\.)\s', txt(rest).replace('\n', ' '), maxsplit=1)[0]
    t = head if len(head) >= 15 else (head + ('' if head[-1] in '.!?:' else ':') + ' ' + first).strip() if head else first
    if len(t) > 120:
        t = t[:120].rsplit(' ', 1)[0] + '…'
    return t, (rest if lead and len(head) >= 15 else body)


def read_html(path):
    b = open(path, 'rb').read()
    enc = 'cp1251' if re.search(rb'charset=["\']?(windows-1251|cp1251)', b[:3000], re.I) else 'utf-8'
    return b.decode(enc, 'ignore')


def text_date(raw):
    """'17.09.2009' or '25 Февраля 2010' anywhere near the top of the page body."""
    top = raw[raw.find('<body'):][:20000]
    top = re.sub(r'<[^>]+>', ' ', top)
    m = re.search(r'\b(\d{1,2})\.(\d{2})\.((?:19|20)\d\d)\b', top)
    if m:
        return f'{m.group(3)}-{m.group(2)}-{int(m.group(1)):02d}'
    m = re.search(r'\b(\d{1,2})\s+([А-Яа-яІіЇїЄє]+)\s+((?:19|20)\d\d)', top)
    if m:
        mon = next((i for k, i in MONTHS_RU_UK.items() if re.match(k, m.group(2).lower())), None)
        if mon:
            return f'{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}'
    return ''


def extract(path, site):
    raw = read_html(path)
    title = re.search(r'class="article-title"[^>]*>\s*<h1[^>]*>(.*?)</h1>', raw, re.S) \
        or (re.search(r'<title>(.*?)</title>', raw, re.S | re.I) if site in MIRRORS else None)  # their plain <h1> is the site name
    et = re.search(r'class="eTitle"[^>]*>(.*?)(?=class="e(?:Message|Details|Text)")', raw, re.S)  # uCoz entry title
    if et:  # it also holds the time ("16:12") in a floated div
        et_text = re.sub(r'\b\d{1,2}:\d{2}\b', '', html.unescape(re.sub(r'<[^>]+>', ' ', et.group(1))))
        et_text = re.sub(r'\s+', ' ', et_text.split('<')[0])
        et_text = re.sub(r'^(\d{1,2}[.:]\d{2}([.:]\d{2})?\s+|[AP]M\s+)+|\s+\d{1,2}\.\d{0,2}\.?\d*$', '', et_text.strip()).strip(' "')
        title = re.match(r'(.*)', et_text) if et_text else title
    title = title or re.search(r'<h1[^>]*>(.*?)</h1>', raw, re.S) or re.search(r'<title>(.*?)</title>', raw, re.S)
    title = clean(html.unescape(re.sub(r'<[^>]+>', ' ', title.group(1)))) if title else ''
    title = re.sub(r'\s*[|–—»-]\s*(Приморськ|Приморск|ПРО Приморськ|Приморська міська рада|#goPrim24|Portal\b).*$', '', title, flags=re.I)
    title = re.sub(r'\s*[|–—»-]\s*ГО\s*"Приморськ 24/7".*$', '', title)
    title = re.sub(r'^Приморск\s*::\s*|\s+-\s+(primorsk\.zp\.ua|Інформаційно-познавальний портал).*$|\s+[–-]\s+(Перші сходинки.*|Школярик)$|\s+-\s+primorsk\.zp\.ua$|\s+[–-]\s+(Твоя історія починається тут|Знайомство з Приморськом)$', '', title)
    title = title.strip(' ~')
    date = (re.search(r'datetime="(\d{4}-\d{2}-\d{2})', raw)
            or re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', raw)
            or re.search(r'article:published_time" content="(\d{4}-\d{2}-\d{2})', raw))
    date = date.group(1) if date else ''
    if not date and site == 'archive_pro_prim':  # pro_prim: photo names like 2017_06_02_002316_01.jpg, or dd.mm.yyyy in text
        m = re.search(r'(20\d\d)_(\d\d)_(\d\d)_\d{6}', raw) or re.search(r'\b(\d\d)\.(\d\d)\.(20\d\d)\b', raw)
        if m:
            g = m.groups()
            date = f'{g[0]}-{g[1]}-{g[2]}' if len(g[0]) == 4 else f'{g[2]}-{g[1]}-{g[0]}'
    pid = re.search(r'postid-(\d+)', raw) or re.search(r'class="[^"]*\bpost-(\d+)\b', raw)
    dm = None
    if not date:
        m = re.search(r'class="[^"]*(?:entry-date|posted-on|post-date|published)[^"]*"[^>]*>(.{0,200})', raw, re.S)
        dm = day_month(re.sub(r'<[^>]+>', ' ', m.group(1))) if m else None
    if not date and site in MIRRORS:
        ad = re.search(r'class="(?:article-date|eDetails|news-date|itemDateCreated)[^"]*"[^>]*>(.{0,300})', raw, re.S)  # the page's own date line first
        date = (text_date('<body>' + ad.group(1)) if ad else '') or text_date(raw)
    if date and date < '1990':
        date = ''  # a year from the story, not a publication date
    orig = re.search(r'Оригінал:</b>\s*<a href="([^"]+)"', raw)
    if site == 'primorsk_in' and ': ' in title:  # <title> is "Рубрика: Заголовок"
        tail = title.split(': ', 1)[1]
        if tail[:25] in html.unescape(raw):
            title = tail
    forum = site == 'primorsk_forum'
    body = clean_article.clean(raw, BODY[site], path, title, tries=60 if forum else 4 if site in MIRRORS else 1, join=forum)
    if site in MIRRORS and not re.search(r'[а-яіїєґ]', title, re.I):  # a date or nothing as the title
        title, body = title_from_body(body)
    if '<img' not in body and (f := featured(raw, path)):
        body = f'<img src="{f}" alt="" loading="lazy">\n' + body
    if site == 'prym':  # tourist route pages open with "duration / extra materials / accessibility" boxes
        body = re.sub(r'(<p>\s*)?<h4>(Тривалість|Допоміжні матеріали|Доступність)</h4>\s*<p>.*?</p>(\s*</p>)*\s*', '', body, flags=re.S)
    body = clean_article.mask_private(body, site)
    title = clean_article.mask_private(title, site)
    body, title = names.shorten(body), names.shorten(title)  # reversible: NAMES=full python3 extract_articles.py
    # scope is judged on the page as it was (its tags and "see also" say where the story belongs),
    # the portal text drops those tails
    scope_ = scope(title, clean_article.to_text(body), site)
    body = clean_article.cut_tail(body)
    text = clean_article.to_text(body)
    return {'html': body, 'pid': int(pid.group(1)) if pid else None, 'dm': dm, 'date_est': False, 'thumb': thumb(body, path), 'site': site, 'path': os.path.relpath(path, ROOT), 'url': orig.group(1) if orig else '',
            'title': title, 'date': date, 'scope': scope_, 'text': text}


if __name__ == '__main__':
    assert title_from_body('<p><strong>З Україною в серці</strong></p><p>Текст.</p>')[0] == 'З Україною в серці'
    assert title_from_body('<p><strong>Наші вітання</strong></p><p>Відділ освіти вітає. Далі.</p>')[0] == 'Наші вітання: Відділ освіти вітає.'
    assert title_from_body('<p>Відділ освіти вітає <strong>Андрія Д.</strong>, учня 10 класу, який посів ІІІ місце. Інше.</p>')[0] \
        == 'Відділ освіти вітає Андрія Д., учня 10 класу, який посів ІІІ місце.'
    # article pages of the three original archives (frozen from the old preview_app classification; the archives no longer change)
    data = json.load(open(os.path.join(ROOT, 'archive_pages.json'), encoding='utf-8'))
    out = []
    import multiprocessing
    pool = multiprocessing.Pool()  # extract() is pure per page: all cores
    # moved to private storage (council documents, see tools/legacy/move_council_docs.py) = missing here
    jobs = [(os.path.join(ROOT, path), site) for site, paths in data.items() for path in paths if os.path.exists(os.path.join(ROOT, path))]
    for a in pool.starmap(extract, jobs, chunksize=64):
        # drop stubs that slipped into "articles" and WordPress default/theme demo content
        if len(a['text']) >= 200 and not PLACEHOLDER.search(a['text']) and not a['title'].startswith('Markup:') \
                and not HIDDEN.search(a['text']):
            out.append(a)
    # pages rescued later from the Wayback Machine (mirror/<dir>/<slug>.html + manifest.json)
    jobs = []
    for site, (d, _, content_url, page_kind) in MIRRORS.items():
        mpath = os.path.join(ROOT, 'mirror', d, 'manifest.json')
        if not os.path.exists(mpath):
            continue
        for slug_, meta_ in json.load(open(mpath)).items():
            if meta_.get('missing') or not re.search(content_url, meta_['url']):
                continue
            page = os.path.join(ROOT, 'mirror', d, slug_ + '.html')
            if BODY[site] == 'eMessage' and open(page, 'rb').read().count(b'class="eMessage"') != 1:
                continue  # uCoz list page (several entries): titles and texts would not match
            jobs.append((page, CC_AS.get(site, site), meta_, page_kind))
    results = pool.starmap(extract, [j[:2] for j in jobs], chunksize=64)
    pool.close()
    for (page, site, meta_, page_kind), a in zip(jobs, results):
        a['url'], a['kind'] = meta_['url'], page_kind
        # where a reader can see the original: Wayback (default), the still-live site, or nowhere public (Common Crawl only)
        a['arch'] = 'cc' if meta_.get('cc') else 'live' if meta_.get('live') else ''
        a['title'] = TITLE_FIX.get(meta_['url'], a['title'])
        if site in ('rcdt', 'school3', 'licey', 'school2', 'primroo', 'primrda', 'tavriya') or site in MIRRORS and \
                MIRRORS[site][1] in ('eMessage', 'post-body') and site != 'primorskstep':  # the steppe one also reposts national news
            a['scope'] = 'local'  # a Prymorsk school / education office site: everything is local life
        if site == 'travel' and '?p=' in meta_['url']:
            a['title'] = f"Туристичний маршрут «{a['title']}»"
        if site == 'primorsk_forum' and re.search(r'/forum/(7|14)-', meta_['url']):
            a['scope'] = 'local'  # sections "Все о Приморске" / "Политика в Приморске": the town is implied
        if site in BLOGS:  # Blogger's own publication date
            a['date'], a['date_est'] = f"{meta_['ts'][:4]}-{meta_['ts'][4:6]}-{meta_['ts'][6:8]}", False
        if site in SITE_VILLAGE:
            a['vl'] = [SITE_VILLAGE[site]]
        m_ = re.search(r'/(\d{4}-\d{2}-\d{2})-\d+$', meta_['url'])
        if m_:  # uCoz: the URL date is the publication date
            a['date'], a['date_est'] = m_.group(1), False
        if page_kind == 'history' and a['date'] < '2005':  # a year from the story itself, not a publication date
            a['date'] = ''
        if not a['date']:  # fall back to the capture date: the page existed by then
            a['date'], a['date_est'] = f"{meta_['ts'][:4]}-{meta_['ts'][4:6]}-{meta_['ts'][6:8]}", 9999
        if a['date'] > '2022-03-31' and page_kind == 'news':
            continue  # captured under occupation: the free local press ends in March 2022
        if len(a['text']) >= 200 and 'Сторінка в розробці' not in a['text'] and not PLACEHOLDER.search(a['text']):
            out.append(a)
    # council session recordings were hidden by the council on purpose: drop their embeds from the portal
    hidden, gone = set(), set()
    if os.path.exists(os.path.join(ROOT, 'videos_meta.jsonl')):
        import video_download
        for r in video_download.rows():
            v = video_download.verdict(r)
            if v.startswith('skip: council session'):
                hidden.add(r['id'])
            elif v == 'skip: unavailable':  # removed from YouTube before we could copy it: an empty player helps nobody
                gone.add(r['id'])
    GONE = '<p class="video-gone">Відео не збереглося: його видалили з YouTube раніше, ніж архів встиг зробити копію.</p>\n'
    for a in out:
        a['html'] = re.sub(r'<iframe src="[^"]*embed/([\w-]{11})"[^>]*></iframe>\n?',
                           lambda m: '' if m.group(1) in hidden else GONE if m.group(1) in gone else m.group(0), a['html'])
    # a picture reused by many posts is a header/stock image (council crest), not a photo of the event
    # pages keep their own copy of a shared banner, so compare file names without the size suffix
    img_key = lambda src: re.sub(r'-\d+x\d+(?=\.\w+$)', '', unquote(src).rsplit('/', 1)[-1].lower())
    # the council's own banners ("ОФІЦІЙНО", crest, section headers) are its official identity and stay;
    # on the other two sites a picture repeated across posts is an ad or a stock header
    uses = collections.Counter(img_key(a['thumb']) for a in out if a['thumb'] and a['site'] != 'archive_mrprim')
    banners = {k for k, n in uses.items() if n > 3}
    council_uses = collections.Counter(img_key(a['thumb']) for a in out if a['thumb'] and a['site'] == 'archive_mrprim')
    council_banners = {k for k, n in council_uses.items() if n > 3}  # kept, but flagged: not a photo of the event
    for a in out:
        if a['site'] == 'archive_mrprim':
            continue
        a['html'] = re.sub(r'<img src="([^"]+)"[^>]*>\n?', lambda m: '' if img_key(m.group(1)) in banners else m.group(0), a['html'])
        a['thumb'] = thumb(a['html'], a['path'])
    for site in ('archive_mrprim', 'archive_prim24'):
        fill_dates([a for a in out if a['site'] == site])
    json.dump(out, open(os.path.join(ROOT, 'articles.json'), 'w'), ensure_ascii=False, indent=0)
    out += almanac()
    # timeline: local articles with a date, deduplicated (pro_prim was crawled under two URL forms)
    seen, timeline, about = set(), [], {}
    for a in sorted(out, key=lambda a: a['date']):
        k = (a['site'], a['title'], a['date'])
        kd = kind(a)
        # no Cyrillic in the title = WordPress theme demo content ("Sample Page", "Hello world")
        if kd == 'listing' or not a['date'] or k in seen or not re.search(r'[а-яіїєґ]', a['title'], re.I):
            continue
        # the council's own posts stay whatever their scope: it published what it judged mattered to the community
        if kd == 'news' and a['scope'] != 'local' and a['site'] not in ('imsu', 'archive_mrprim'):
            continue
        seen.add(k)
        if a['site'] in EXCERPT_ONLY:
            a['ext_url'] = f"https://web.archive.org/web/2022/{a['url']}"
        entry = {'d': a['date'], 's': a['site'].removeprefix('archive_'), 't': a['title'],
                 'x': excerpt(a['text']), 'p': '/' + quote(a['path']), 'u': a['url'], 'i': a['thumb'],
                 **({'e': a['date_est']} if a['date_est'] else {}),
                 **({'w': 1} if len(a['text']) < 300 else {}),  # w = too thin for a bot post
                 **({'ph': n} if (n := a['html'].count('<img')) else {}),  # photos in the clean text
                 **({'bn': 1} if a['thumb'] and img_key(a['thumb']) in council_banners else {}),
                 **({'v': 1} if '<iframe' in a['html'] or re.search(r'href="[^"]*youtu', a['html']) else {}),
                 **({'c': c} if (c := topics(a['title'], a['text'])) else {}),
                 **({'vl': v} if (v := list(dict.fromkeys(a.get('vl', []) + villages(a['title'], a['text'])))) else {}),
                 **({'ar': a['arch']} if a.get('arch') else {})}
        if kd == 'about':
            continue  # council reference pages (deputies, reception hours, regulations): not part of the chronicle (author's call)
        if kd == 'history' and a['site'] == 'almanac':  # the history block: the union's almanac (author's call, 2026-10)
            about[(a['site'], a['title'].lower())] = {**entry, 'k': kd, **({'to': a['to']} if a.get('to') else {})}
        elif kd == 'history':  # the history sites' pages now live in the chronicle like any record (latest snapshot wins)
            if a['title'].lower() not in IN_ALMANAC:
                about[(a['site'], a['title'].lower())] = entry
        else:
            timeline.append(entry)
    # regional media: headline, date, excerpt and a link; full text where allowed (official sites, editors' consent)
    # they stop where the community's own sites fell silent: the chronicle ends with a local record (author's call)
    last_local = max(t['d'] for t in timeline)
    regional_html = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'regional_news*.jsonl'))):
        for line in open(f, encoding='utf-8'):
            r = json.loads(line)
            if not r.get('date') or r['date'] >= REGIONAL_UNTIL or r['date'] > last_local or 'tavriya' in r['source']:  # tavriya is mirrored in full
                continue
            text = f"{r['title']} {r.get('excerpt', '')}"
            if len(r['title']) < 20 or re.match(r'(Довідка|Загальна інформація|Географічне|Інформація щодо|Звіт|План)', r['title']):
                continue  # oblast site reference pages, not news
            if not LOCAL.search(text) or re.search(r'Приморське|Приморского края|Ленинградск|Ахтарск|Приморськ\w* Посад|Приморськ\w* площ', text):
                continue  # other places called Primorsk / Prymorske
            k = ('regional', r['title'], r['date'])
            if k in seen:
                continue
            seen.add(k)
            full = regional_body(r['url'])
            if full:
                regional_html[r['url']] = full
            timeline.append({'d': r['date'], 's': 'regional', 't': names.shorten(r['title']), 'x': names.shorten(r.get('excerpt', ''))[:260], 'p': r['url'],
                             **({'full': 1} if full else {}),
                             'u': r['url'], 'i': '', 'ext': r['source'].replace(' (Wayback)', ''),
                             **({'c': c} if (c := topics(r['title'], r.get('excerpt', ''))) else {}),
                             **({'vl': v} if (v := villages(r['title'], r.get('excerpt', ''))) else {})})
    timeline += [t for t in about.values() if not t.get('k')]
    timeline.sort(key=lambda t: t['d'])
    timeline += [t for t in about.values() if t.get('k')]  # almanac order: as in the book
    # a picture reused by many posts is a header/stock image (council crest), not a photo of the event
    uses = collections.Counter(t['i'] for t in timeline if t['i'] and t['s'] != 'mrprim')
    for t in timeline:
        if t['s'] != 'mrprim' and uses[t['i']] > 3:
            t['i'] = ''
    # clean article bodies for the reader, one fragment per timeline entry
    art_dir = os.path.join(ROOT, 'timeline', 'a')
    os.makedirs(art_dir, exist_ok=True)
    by_path = {a['path']: a for a in out}
    # stable id from the article's address: links (#id, bot posts) survive rebuilds and reordering
    import hashlib
    for t in timeline:
        t['n'] = hashlib.md5(t['p'].encode()).hexdigest()[:10]
    # Russian-language titles/excerpts in Ukrainian (translations.json, keyed by id); the original title stays in 'to'
    tr_path = os.path.join(ROOT, 'translations.json')
    tr = json.load(open(tr_path, encoding='utf-8')) if os.path.exists(tr_path) else {}
    for t in timeline:
        if (u := tr.get(t['n'])) and u.get('t'):
            # the translation goes through the same privacy pass as every original text
            safe = lambda v: names.shorten(clean_article.mask_private(v, t['s']))
            if u['t'] != t['t']:  # "Газ – не для нас?" reads the same in both: no "original title" line then
                t['to'] = t['t']
            t['t'], t['x'] = safe(u['t']), safe(u.get('x') or '') or t['x']
    # one story saved under two addresses (Russian and Ukrainian slug, "?shared=email"): keep the copy with the longer text
    best = {}
    for t in timeline:
        k = (t['s'], t['t'].strip(' «»"').lower(), t['d'])
        if k not in best or len(by_path.get(unquote(t['p'][1:]), {}).get('text', '')) > len(by_path.get(unquote(best[k]['p'][1:]), {}).get('text', '')):
            best[k] = t
    timeline[:] = [t for t in timeline if best[(t['s'], t['t'].strip(' «»"').lower(), t['d'])] is t]
    for t in timeline:
        for field, (wrong, right) in TEXT_FIX.get(t['n'], {}).items():
            t[field] = t[field].replace(wrong, right)
        t['t'] = tidy_title(t['t'])
    from translations import russian
    import proofread
    PROOF = json.load(open(proofread.PATH, encoding='utf-8')) if os.path.exists(proofread.PATH) else {}
    for t in timeline:  # mechanical slips of the sources: apostrophes only where the text is Ukrainian
        body = by_path.get(unquote(t['p'][1:]), {}).get('text', '') if not t.get('full') else ''
        t['ua'] = not russian(f"{t.get('to') or t['t']} {t['x']} {body[:2000]}")
        t['t'], t['x'] = (names.shorten(clean_article.fix_typos(t[k], t['ua'])) for k in ('t', 'x'))
        t.update(proofread.apply(t, PROOF.get(t['n'], {})))  # proofread headline / excerpt (proofread.json)
    live = {t['n'] + '.html' for t in timeline}
    for f in os.listdir(art_dir):  # fragments of articles that are gone (moved/filtered) must not stay reachable
        if f.endswith('.html') and f not in live:
            os.remove(os.path.join(art_dir, f))
    for t in timeline:
        n = t['n']
        # body only: every link to the original / Wayback is added by the reader and the article page, at the bottom
        # (the consented editors' "credit at the top" is the linked source name above the headline)
        if t.get('full'):
            body = regional_html[t['u']]
        elif t.get('ext') or by_path.get(unquote(t['p'][1:]), {}).get('ext_url'):
            body = f"<p>{html.escape(t['x'])}</p>"  # excerpt; the full text is at the source
        else:
            body = by_path[unquote(t['p'][1:])]['html']
            if 'x' in TEXT_FIX.get(n, {}):  # the typo is in the text itself too
                body = body.replace(*TEXT_FIX[n]['x'])
        with open(os.path.join(art_dir, f'{n}.html'), 'w', encoding='utf-8') as f:
            # names once more: a surname typed with a Latin look-alike letter is a word only after fix_typos
            f.write(names.shorten(clean_article.fix_typos(body, t.pop('ua'))))
    # the chronicle only shows 3 lines of the excerpt: 160 characters keep data.json (loaded on every visit) light
    short = [{**t, 'x': t['x'][:160]} for t in timeline]
    json.dump(short, open(os.path.join(ROOT, 'timeline', 'data.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
    import pages
    print('article pages:', pages.build(timeline))
    import export
    print('open data rows:', export.write(timeline))  # timeline/export/chronicle.csv  # timeline/p/<id>.html for search engines and link previews
    print('timeline:', len(timeline), 'with photo:', sum(1 for t in timeline if t['i']))
    meta = {a['path']: [a['scope'], a['date'], a['title']] for a in out}
    if os.path.isdir(os.path.join(ROOT, 'preview_app')):  # the old three-archive browser, if still kept
        with open(os.path.join(ROOT, 'preview_app', 'scopes.js'), 'w', encoding='utf-8') as f:
            f.write('const articleMeta = ' + json.dumps(meta, ensure_ascii=False) + ';\n')
    for site in data:
        arts = [a for a in out if a['site'] == site]
        by = {s: sum(1 for a in arts if a['scope'] == s) for s in ('local', 'region', 'general')}
        print(site, len(arts), 'with date:', sum(1 for a in arts if a['date']),
              'approx:', sum(1 for a in arts if a['date_est']), by)
