#!/usr/bin/env python3
"""Collect headline/date/excerpt/link records about Prymorsk (Zaporizhzhia obl.) and its villages
from regional sources. Stdlib only. Resumable: URLs already in the output are skipped, and
per-URL fetch results are memoised in regional_cache/meta.jsonl.

Usage:  python3 regional_collect.py [zoda reporter 06137 zppravda mig]   (default: all, in order)
Sources can be run as separate processes in parallel: rate limits are per host, output is flock'ed.
Politeness: >=2.5 s per live host (10 s where robots says Crawl-delay: 10, 5 s for 06137),
>=5 s for web.archive.org; no robots-disallowed search endpoints; a source stops on repeated errors.
"""
import fcntl, hashlib, html, json, os, re, ssl, sys, time, urllib.error, urllib.parse as up, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "regional_news.jsonl")
CACHE_DIR = os.path.join(HERE, "regional_cache")
META = os.path.join(CACHE_DIR, "meta.jsonl")
UA = "Mozilla/5.0 (Macintosh) archival-research (Prymorsk memorial chronicle; low rate)"
os.makedirs(CACHE_DIR, exist_ok=True)

# ---------------------------------------------------------------- http
_ctx = ssl.create_default_context(); _ctx.check_hostname = False; _ctx.verify_mode = ssl.CERT_NONE
_last = {}

class Blocked(Exception):
    pass

class Source:
    """Tracks consecutive failures; raises Blocked to stop the source."""
    def __init__(self, name, max_err=5):
        self.name, self.err, self.max_err, self.blocks = name, 0, max_err, 0

    def get(self, url, delay, timeout=45):
        host = up.urlsplit(url).netloc
        wait = _last.get(host, 0) + delay - time.time()
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "uk,ru;q=0.8,en;q=0.5"})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_ctx) as r:
                code, body = r.status, r.read()
        except urllib.error.HTTPError as e:
            code, body = e.code, b""
        except Exception as e:
            _last[host] = time.time()
            self.err += 1
            log(self.name, "ERR", url[:100], e)
            if "refused" in str(e).lower() or self.err >= self.max_err:
                raise Blocked(f"{self.name}: {e}")
            return 0, ""
        _last[host] = time.time()
        if code in (403, 429, 503):
            self.blocks += 1
            log(self.name, code, url[:100])
            if self.blocks >= 2:
                raise Blocked(f"{self.name}: HTTP {code}")
            time.sleep(30)
            return code, ""
        self.err = 0
        return code, body.decode("utf-8", "replace")

def log(*a):
    print(time.strftime("%H:%M:%S"), *a, file=sys.stderr, flush=True)

# ---------------------------------------------------------------- persistence
def load_out():
    if not os.path.exists(OUT):
        return set()
    return {json.loads(l)["url"] for l in open(OUT, encoding="utf-8") if l.strip()}

DONE = load_out()

def write(rec):
    with open(OUT, "a", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fcntl.flock(fh, fcntl.LOCK_UN)
    DONE.add(rec["url"])

_meta = {}
if os.path.exists(META):
    for l in open(META, encoding="utf-8"):
        try:
            d = json.loads(l); _meta[d["url"]] = d["m"]
        except ValueError:
            pass

def meta_get(url):
    return _meta.get(url)

def meta_put(url, m):
    _meta[url] = m
    with open(META, "a", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        fh.write(json.dumps({"url": url, "m": m}, ensure_ascii=False) + "\n")
        fcntl.flock(fh, fcntl.LOCK_UN)

# ---------------------------------------------------------------- text + places
# unambiguous within the oblast: a mention alone counts
PLACES = [
    ("Приморськ", r"Приморськ(?!о-|е\b|их\b|ого\b(?! район)|ому\b(?! район))|Приморск(?!о-|ое\b|их\b|ий Посад|ом Посад|ого\b(?! район)|ому\b(?! район))|Ногайськ|Ногайск"),
    ("Преслав", r"Преслав"), ("Підспір'я", r"Підспір|Подспор"),
    ("В'ячеславка", r"В['’ʼ]?ячеславк|Вячеславк"), ("Інзівка", r"Інзівк|Инзовк"), ("Банівка", r"Банівк|Бановк"),
    ("Райнівка", r"Райнівк|Райновк"), ("Нельгівка", r"Нельгівк|Нельговк"), ("Лозанівка", r"Лозанівк|Лозановк"),
    ("Коларівка", r"Коларівк|Коларовк"), ("Гюнівка", r"Гюнівк|Гюновк"),
]
# common village names elsewhere too: count only together with Prymorsk/Berdiansk context
AMBIG = [
    ("Борисівка", r"Борисівк|Борисовк"), ("Комишуватка", r"Комишуватк|Камышеватк|Камышуватк"),
    ("Набережне", r"\bНабережн(е|ого|ому|ое)\b"), ("Орлівка", r"Орлівк|Орловк"), ("Болгарка", r"Болгарк"),
    ("Лозуватка", r"Лозуватк|Лозоватк"), ("Єлизаветівка", r"Єлизаветівк|Елизаветовк"),
    ("Новоолексіївка", r"Новоолексіївк|Новоалексеевк"), ("Мануйлівка", r"Мануйлівк|Мануйловк"),
    ("Зеленівка", r"Зеленівк|Зеленовк"), ("Юр'ївка", r"Юр['’ʼ]?ївк|Юрьевк"),
]
CONTEXT = re.compile(r"Приморськ|Приморск|Бердянськ|Бердянск|Бердянськ\w+ район|Приазов")
NOISE = re.compile(r"Усть-Луг|Ленінград|Ленинград|Тосно|Ахтарськ|Ахтарск|Балтій|Балтий|Посад|Приморськ\w* площ|Приморск\w* площ|"
                   r"Приморськ\w* бульвар|Приморск\w* бульвар|танкер|термінал|терминал|нафтоналив|нефтеналив|Приморськ\w* край|Приморск\w* край|Владивост")
GENERIC_TITLE = re.compile(r"^\s*(Загальна інформація|Довідка|До уваги|Географічне положення|План заходів|Перелік|Мережа|"
                           r"Звіт про виконання|Інформація (щодо|про)|Оголошення|Контакти|Графік|Діти\s*$|Увага|Анонс|"
                           r"Список|Реєстр|Порядок|Положення|Протокол|Розпорядження|Результати|Про\s|Оперативна інформація)", re.I)

def places(text):
    found = [lab for lab, rx in PLACES if re.search(rx, text)]
    if CONTEXT.search(text):
        found += [lab for lab, rx in AMBIG if re.search(rx, text)]
    return found

def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

def excerpt(s, n=300):
    s = clean(s)
    out = " ".join(re.split(r"(?<=[.!?…])\s+", s)[:2])
    if len(out) > n:
        out = out[: n - 1].rsplit(" ", 1)[0] + "…"
    out = re.sub(r"\+?\d[\d ()\-]{8,}\d", "[тел.]", out)
    if "[тел.]" in out or re.search(r"[А-ЯІЇЄҐ][а-яіїєґ'’]+ [А-ЯІЇЄҐ][а-яіїєґ'’]+ [А-ЯІЇЄҐ][а-яіїєґ'’]+(вич|вна)\b", out):
        return ""  # directory-like text with full names / phones: title + link only
    if re.search(r"\.(jpe?g|png|gif)\b", out, re.I) or sum(ch.isdigit() for ch in out) > 0.2 * max(len(out), 1):
        return ""  # page chrome / timetables, not prose
    return out

def window(body, rx=r"Приморськ|Приморск"):
    """Short text around the first place mention (for pages whose teaser does not name the place)."""
    m = re.search(rx, body)
    if not m:
        return ""
    pre = body[max(0, m.start() - 120): m.start()]
    pre = pre.rsplit(". ", 1)[-1] if ". " in pre else "…" + pre.split(" ", 1)[-1]
    return pre + body[m.start(): m.start() + 170].rsplit(" ", 1)[0] + "…"

OTHER_TOWNS = re.compile(r"Мелітопол|Мелитопол|Василівк|Дніпрорудн|Кам.янк|Енергодар|Токмак|Полог|Оріхів|Гуляйпол|Якимівк|"
                         r"Михайлівк|Приазовськ|Більмак|Розівк|Чернігівк|Вільнянськ|Новомиколаївк|Кирилівк|Молочанськ|Степногірськ")

def listy(text):
    """Mention that is just one item in a list (towns, hromadas, people) - incidental, not news about Prymorsk."""
    return (len(set(m.group(0)[:5] for m in OTHER_TOWNS.finditer(text))) >= 2
            or len(re.findall(r"\b(ОТГ|сільськ\w*|селищн\w*|міськ\w* рад\w*|громад\w*)\b", text)) >= 3
            or text.count(",") >= 4
            or re.search(r"[А-ЯІЇЄҐ][а-яіїєґ'’]+ [А-ЯІЇЄҐ][а-яіїєґ'’]+ (із|з) с\.", text))

def meta_tag(t, *names):
    for n in names:
        m = re.search(r'<meta[^>]+(?:name|property)="%s"[^>]+content="([^"]*)"' % re.escape(n), t) or \
            re.search(r'<meta[^>]+content="([^"]*)"[^>]+(?:name|property)="%s"' % re.escape(n), t)
        if m and m.group(1).strip():
            return html.unescape(m.group(1)).strip()
    return ""

def body_text(t):
    t = re.sub(r"<(script|style|nav|header|footer|aside)\b.*?</\1>", " ", t, flags=re.S | re.I)
    return clean(t)

def emit(source, date, title, url, exc, default_place=None, require_place=True):
    """Filter + write one record. Returns True if written."""
    if url in DONE or date[:4] >= "2023":  # rule: nothing dated 2023-01-01 or later
        return False
    title, exc = clean(title), excerpt(exc)
    if not title:
        return False
    pl = places(title + " " + exc)
    if NOISE.search(title) and not (set(pl) - {"Приморськ"}):
        return False
    if GENERIC_TITLE.search(title) and not places(title):
        return False
    if not places(title) and listy(exc):
        return False
    if not pl and default_place:
        pl = [default_place]
    if require_place and not pl:
        return False
    write({"source": source, "date": date, "title": title, "url": url, "excerpt": exc, "places": pl})
    return True

# ---------------------------------------------------------------- sources
UK_MONTHS = {m: i + 1 for i, m in enumerate("січня лютого березня квітня травня червня липня серпня вересня жовтня листопада грудня".split())}

def forms_uk(word):
    """Nominative + common oblique forms (zoda search matches whole words)."""
    if word.endswith("ка"):
        b = word[:-2]; return [word, b + "ці", b + "ки"]
    if word.endswith("не"):
        b = word[:-1]; return [word, b + "ого", b + "ому"]
    if word.endswith("я"):
        b = word[:-1]; return [word, b + "ї"]
    return [word, word + "і", word + "а"]

VILLAGES_UK = ["Преслав", "Борисівка", "Підспір'я", "Комишуватка", "Набережне", "Орлівка", "В'ячеславка", "Інзівка",
               "Банівка", "Болгарка", "Софіївка", "Лозуватка", "Райнівка", "Єлизаветівка", "Новоолексіївка", "Нельгівка",
               "Мануйлівка", "Лозанівка", "Коларівка", "Зеленівка", "Гюнівка"]

def src_zoda():
    s = Source("zoda")
    terms = ["Приморськ", "Приморська", "Приморську", "Приморського", "Приморському", "Приморській", "Приморської"]
    for v in VILLAGES_UK:
        terms += forms_uk(v)
    n = 0
    for term in terms:
        page, last = 1, 1
        while page <= last:
            url = f"https://www.zoda.gov.ua/search?q={up.quote(term)}&page={page}"
            code, t = s.get(url, 2.5)
            if code != 200:
                break
            last = max([last] + [int(x) for x in re.findall(r"[?&;]page=(\d+)", t)])
            items = t.split('class="news-item row')[1:]
            if not items:
                break
            for b in items:
                m = re.search(r'<h4 class="h5"><a href="([^"]+)">(.*?)</a>', b, re.S)
                if not m:
                    continue
                aurl = up.urljoin("https://www.zoda.gov.ua/", m[1])
                if aurl in DONE:
                    continue
                d = re.search(r'date-info-date">(\d+) (\S+) (\d{4})', b)
                date = f"{d[3]}-{UK_MONTHS.get(d[2], 0):02d}-{int(d[1]):02d}" if d else ""
                tx = re.search(r'news-text[^>]*><span>(.*?)</span>', b, re.S)
                if date[:4] >= "2023":
                    continue  # no requests for 2023+ items
                title, exc = clean(m[2]), clean(tx[1] if tx else "")
                if GENERIC_TITLE.search(title) and not places(title):
                    continue
                if not places(title + " " + exc):
                    mm = meta_get(aurl)
                    if mm is None:
                        c2, at = s.get(aurl, 2.5)
                        if c2 != 200:
                            continue
                        body = body_text(at)
                        desc = meta_tag(at, "description", "og:description")
                        rx = "|".join(r for _, r in PLACES + AMBIG)
                        mm = {"desc": desc, "win": window(body, rx) if not places(desc) else ""}
                        meta_put(aurl, mm)
                    exc = mm["desc"] if places(mm["desc"]) else mm["win"]
                    if not places(mm["desc"]) and listy(exc):
                        continue
                n += emit("zoda.gov.ua", date, title, aurl, exc)
            log("zoda", term, page, "/", last, "total", n)
            page += 1
    return n

REPORTER_TAGS = ["primorsk", "primorskiy-rayon", "primorskiy-rayonnyy-sud", "primorskaya-rga", "primorskiy-gorsovet",
                 "preslav", "borisovka", "podspore", "nogai", "kamyshevatka", "naberezhnoe", "orlovka", "vyacheslavka",
                 "inzovka", "banovka", "bolgarka", "lozovatka", "raynovka", "elizavetovka", "novoalekseevka", "nelgovka",
                 "manuylovka", "lozanovka", "kolarovka", "zelenovka", "gyunovka"]
TAG_PLACE = {"preslav": "Преслав", "borisovka": "Борисівка", "podspore": "Підспір'я", "nogai": "Підспір'я",
             "kamyshevatka": "Комишуватка", "naberezhnoe": "Набережне", "orlovka": "Орлівка", "vyacheslavka": "В'ячеславка",
             "inzovka": "Інзівка", "banovka": "Банівка", "bolgarka": "Болгарка", "lozovatka": "Лозуватка",
             "raynovka": "Райнівка", "elizavetovka": "Єлизаветівка", "novoalekseevka": "Новоолексіївка",
             "nelgovka": "Нельгівка", "manuylovka": "Мануйлівка", "lozanovka": "Лозанівка", "kolarovka": "Коларівка",
             "zelenovka": "Зеленівка", "gyunovka": "Гюнівка"}

def src_reporter():
    s = Source("reporter")  # robots: Crawl-delay 10, /search/ disallowed -> tag pages only
    n = 0
    for tag in REPORTER_TAGS:
        ambiguous_tag = TAG_PLACE.get(tag) in [a for a, _ in AMBIG]
        page = 0
        while True:
            code, t = s.get(f"https://reporter-ua.com/tags/{tag}" + (f"?page={page}" if page else ""), 10)
            if code != 200:
                break
            items = t.split('class="e-news-item"')[1:]
            if not items:
                break
            for b in items:
                m = re.search(r'e-news-item-title"><a href="([^"]+)">(.*?)</a>', b, re.S)
                if not m:
                    continue
                d = re.search(r'post-date">(\d\d)\.(\d\d)\.(\d{4})', b)
                tx = re.search(r'e-news-item-text">(.*?)</div>', b, re.S)
                # ambiguous village tag (e.g. Орловка) must still show Prymorsk context
                n += emit("reporter-ua.com", f"{d[3]}-{d[2]}-{d[1]}" if d else "", m[2], up.urljoin("https://reporter-ua.com/", m[1]),
                          tx[1] if tx else "", default_place=None if ambiguous_tag else TAG_PLACE.get(tag, "Приморськ"))
            log("reporter", tag, page, "total", n)
            if f"?page={page + 1}" not in t:
                break
            page += 1
    return n

VILLAGE_SLUG = (r"prim|prym|preslav|borisiv|borysiv|borisov|inziv|inzov|baniv|banov|nelgiv|nelgov|kolariv|kolarov|lozaniv|lozanov|"
                r"guniv|gyuniv|gunov|rajniv|rayniv|rajnov|vaceslav|vyaceslav|vjaceslav|podspor|pidspir|komisuvat|kamysev|naberezn|"
                r"orlivk|orlovk|bolgark|lozuvat|lozovat|elizavet|jelizavet|novooleks|novoaleks|manujl|manuyl|zeleniv|zelenov|nogajsk")

def cdx(source, query, cache_name):
    path = os.path.join(CACHE_DIR, cache_name)
    if os.path.exists(path):
        return json.load(open(path))
    url = "https://web.archive.org/cdx/search/cdx?" + query
    for attempt in range(3):
        code, t = source.get(url, 5, timeout=240)
        if code == 200 and t.strip().startswith("["):
            rows = json.loads(t)[1:]
            json.dump(rows, open(path, "w"))
            return rows
        time.sleep(20)
    raise Blocked(f"{source.name}: CDX failed")

def src_06137():
    s, wb = Source("06137"), Source("06137-cdx")
    rows = cdx(wb, "url=06137.com.ua/news/&matchType=prefix&output=json&fl=timestamp,original&filter=statuscode:200"
                   "&collapse=urlkey&from=2020&to=2023&limit=50000", "cdx_06137_news_2020_2023.json")
    urls = {}
    for ts, orig in rows:
        m = re.search(r"/news/(\d+)/([a-z0-9-]+)", orig)
        # ids < ~2.622M are 2019 (checked: 2617xxx = 2019-12-25), > ~3.5M are 2023+; the date is re-checked per page.
        # Slug must name the town or a village (network-wide news is dropped)
        if m and 2622000 <= int(m[1]) <= 3500000 and re.search(VILLAGE_SLUG, m[2]):
            urls.setdefault(m[1], f"https://www.06137.com.ua/news/{m[1]}/{m[2]}")
    log("06137 candidates", len(urls))
    n = 0
    for i, (nid, url) in enumerate(sorted(urls.items(), key=lambda x: int(x[0]))):
        if url in DONE:
            continue
        mm = meta_get(url)
        if mm is None:
            code, t = s.get(url, 5)  # robots: Crawl-delay 5
            if code == 404:
                meta_put(url, {"gone": True}); continue
            if code != 200:
                continue
            d = re.search(r'"datePublished":"(\d{4}-\d\d-\d\d)', t)
            mm = {"title": meta_tag(t, "og:title"), "desc": meta_tag(t, "og:description", "description"), "date": d[1] if d else ""}
            meta_put(url, mm)
        if mm.get("gone") or not ("2020" <= mm["date"][:4] <= "2022"):
            continue
        slug_town = re.search(r"primorsk|prymorsk|primorc|prymorc|primorcan|nogajsk", url)  # town, its residents, Ногайськ
        n += emit("06137.com.ua", mm["date"], mm["title"], url, mm["desc"], default_place="Приморськ" if slug_town else None)
        if i % 50 == 0:
            log("06137", i, "/", len(urls), "total", n)
    return n

def src_zppravda():
    s = Source("zppravda-wayback")
    flt = up.quote(f"original:.*({VILLAGE_SLUG}).*")
    rows = cdx(s, f"url=zp-pravda.info&matchType=domain&output=json&fl=timestamp,original&filter=statuscode:200"
                  f"&filter=mimetype:text/html&collapse=urlkey&filter={flt}", "cdx_zppravda_prim.json")
    arts = {}
    for ts, orig in rows:
        m = re.search(r"zp-pravda\.info(?::80)?/(\d{4})/(\d\d)/(\d\d)/([^/?#]+)/?$", orig)
        if m and not re.search(r"primorsk\w*-(plosh|bulv)|/feed", orig):
            arts.setdefault(m[4], (ts, orig, f"{m[1]}-{m[2]}-{m[3]}"))
    log("zppravda candidates", len(arts))
    n = 0
    for slug, (ts, orig, date) in sorted(arts.items(), key=lambda x: x[1][2]):
        wurl = f"https://web.archive.org/web/{ts}/{orig}"
        if wurl in DONE:
            continue
        mm = meta_get(wurl)
        if mm is None:
            code, t = s.get(f"https://web.archive.org/web/{ts}id_/{orig}", 5, timeout=90)
            if code != 200:
                meta_put(wurl, {"gone": True}); continue
            title = meta_tag(t, "og:title") or clean((re.search(r"<h1[^>]*>(.*?)</h1>", t, re.S) or [None, ""])[1])
            title = re.sub(r"\s*[|–-]\s*Запорізька правда.*$", "", title)
            desc = meta_tag(t, "og:description", "description")
            rx = "|".join(r for _, r in PLACES + AMBIG)
            mm = {"title": title, "desc": desc, "win": "" if places(desc) else window(body_text(t), rx)}
            meta_put(wurl, mm)
        if mm.get("gone"):
            continue
        exc = mm["desc"] if places(mm["desc"]) else (mm["win"] or mm["desc"])
        if not places(mm["title"] + " " + mm["desc"]) and listy(exc):
            continue
        n += emit("zp-pravda.info (Wayback)", date, mm["title"], wurl, exc)
    return n

MIG_TAG_QUERIES = ["Приморськ", "Приморск", "primorsk", "prymorsk", "Преслав", "Борисівк", "Борисовк", "Подспор", "Підспір",
                   "Інзівк", "Инзовк", "Банівк", "Бановк", "Орлівк", "Орловк", "Вячеславк", "Нельгівк", "Коларівк", "Гюнівк",
                   "Райнівк", "Лозанівк", "Мануйлівк", "Комишуватк", "Камышеватк", "Болгарк", "Єлизаветівк", "Новоолексіївк"]

def src_mig():
    s = Source("mig")  # robots forbids ?s= and /search/; WP REST tag listing is not disallowed
    tags = {}
    for q in MIG_TAG_QUERIES:
        code, t = s.get(f"https://mig.com.ua/wp-json/wp/v2/tags?search={up.quote(q)}&per_page=100&_fields=id,name,slug,count", 3)
        if code != 200:
            continue
        for tg in json.loads(t or "[]"):
            name = tg["name"]
            pl = places(name) or [lab for lab, rx in AMBIG if re.search(rx, name) and CONTEXT.search(name)]
            if pl and not NOISE.search(name) and tg["count"]:
                tags[tg["id"]] = (name, pl[0])
    log("mig tags", len(tags), [v[0] for v in tags.values()][:40])
    n = 0
    for tid, (name, place) in tags.items():
        page = 1
        while True:
            code, t = s.get(f"https://mig.com.ua/wp-json/wp/v2/posts?tags={tid}&per_page=100&page={page}"
                            f"&_fields=link,date,title,excerpt", 3)
            if code != 200:
                break
            posts = json.loads(t or "[]")
            for p in posts:
                n += emit("mig.com.ua", p["date"][:10], p["title"]["rendered"], p["link"], p["excerpt"]["rendered"],
                          default_place=place)
            if len(posts) < 100:
                break
            page += 1
        log("mig", name, "total", n)
    return n

def refilter():
    """Re-apply current filters to the existing output (after filter changes)."""
    rs = [json.loads(l) for l in open(OUT, encoding="utf-8") if l.strip()]
    keep = []
    for r in rs:
        t, e = r["title"], r["excerpt"]
        if (NOISE.search(t) and not (set(places(t + " " + e)) - {"Приморськ"})) or \
           (GENERIC_TITLE.search(t) and not places(t)) or (not places(t) and listy(e)):
            continue
        r["excerpt"] = excerpt(e) if e else ""
        keep.append(r)
    with open(OUT + ".tmp", "w", encoding="utf-8") as fh:
        for r in keep:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(OUT + ".tmp", OUT)
    log("refilter: kept", len(keep), "of", len(rs))

SOURCES = {"zoda": src_zoda, "reporter": src_reporter, "06137": src_06137, "zppravda": src_zppravda, "mig": src_mig}

def selftest():
    assert places("В Приморске пожар") == ["Приморськ"]
    assert places("ворог атакував Приморське") == []
    assert places("школярі Приморського району") == ["Приморськ"]
    assert places("у приморських районах області") == []
    assert places("село Орлівка Василівського району") == []
    assert "Орлівка" in places("с. Орлівка Приморського району")
    assert "Преслав" in places("У селі Преслав") and places("вулиця Набережна") == []
    assert listy("Берестівська, Веселівська, Воскресенська, Гірсівська, Приморська ОТГ")
    assert GENERIC_TITLE.search("Про продовження договору") and GENERIC_TITLE.search("ОПЕРАТИВНА ІНФОРМАЦІЯ ЩОДО ВОДИ")
    assert listy("міста Бердянськ та Приморськ Бердянського району, Василівка, Дніпрорудне")
    assert excerpt("Тел. 0613391617. Текст.") == ""
    assert GENERIC_TITLE.search("До уваги журналістів!") and not GENERIC_TITLE.search("У Приморську відкрили сквер")

if __name__ == "__main__":
    selftest()
    if sys.argv[1:] == ["refilter"]:
        refilter(); sys.exit()
    names = sys.argv[1:] or list(SOURCES)
    for name in names:
        try:
            log("==", name, "start")
            log("==", name, "done, new records:", SOURCES[name]())
        except Blocked as e:
            log("== STOPPED", e)
