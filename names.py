"""Shorten people's names to "Ім'я П." so the public portal can't be searched by full name.

Reversible: extract_articles.py applies it only when ABBREVIATE is on (env NAMES=full turns it off),
the archived source pages are never changed.

    Дробига Ірина Олександрівна  -> Ірина Д.
    Ірина Олександрівна Дробига  -> Ірина Д.
    О.А. Бондарова / Бондарова О.А.   -> О. А. Б.
    Оксана Зоріна / Зоріна Оксана -> Оксана З.
Streets, schools and parks named after people, and well-known historical figures, stay as they are.
"""
import os, re

ABBREVIATE = os.environ.get('NAMES', 'short') != 'full'

# common Ukrainian and Russian first names (nominative); inflected forms are matched by stem
FIRST = """Тоні Тони Аделіна Аделина Крістіна Кристина Аполлінарія Андріяна Рома Мілана Злата Вероніка Дарина Ангеліна Софія Емілія Віолета Карина Ельвіра Еміне Елеонора Арина Аріна Єва Ева Мирон Тимур Тимофій Давид Ілля Платон Генадій Геннадій Гліб Нікіта Ніка Діана Мілена Таїсія Влада Владислава Ксенія Есенія Устина Яна Олеся Леся Аліса Амелія Евеліна Ева Ілона Каміла Лілія Мирослав Ростислав Святослав Тарас Філіп Яків Ярина Ганна Ганна Зоряна Уляна Христина Стефанія Анжеліка Ангеліна Алла Жанна Інна Кіра Лада Майя Римма Тамара Фаїна Святослав Святослава Олександр Олександра Олексій Андрій Анатолій Антон Артем Богдан Борис Вадим Валентин Валентина Валерій Валерія Василь
Віктор Вікторія Віталій Віталіна Володимир Вячеслав В'ячеслав Геннадій Георгій Григорій Даниїл Данило Денис Дмитро Євген Євгенія Єгор
Іван Ігор Ілля Кирило Костянтин Леонід Максим Микола Михайло Назар Олег Павло Петро Роман Руслан Сергій Станіслав Степан Тарас
Тимофій Федір Юрій Ярослав Ярослава Аліна Алла Анастасія Ангеліна Анна Антоніна Валерія Галина Дарина Дар'я Діана Єлизавета Євгенія
Зінаїда Зоя Інна Ірина Катерина Кристина Лариса Людмила Любов Марина Марія Мирослава Надія Наталія Наталя Ніна Оксана Олена Ольга
Поліна Раїса Світлана Софія Тамара Тетяна Уляна Юлія Яна Людмила Лілія Лідія Віра Вероніка Жанна Карина Маргарита Милана Нонна
Александр Александра Алексей Анатолий Андрей Аркадий Валентин Валерий Василий Виктор Виталий Владимир Владислав Вячеслав Геннадий
Георгий Григорий Дмитрий Евгений Евгения Иван Игорь Илья Кирилл Константин Леонид Максим Михаил Николай Олег Павел Петр Пётр Роман
Сергей Станислав Степан Тимур Федор Фёдор Юрий Ярослав Алла Анастасия Анна Антонина Валентина Вера Галина Дарья Диана Екатерина Елена
Елизавета Жанна Зинаида Ирина Кристина Лариса Лидия Любовь Людмила Маргарита Марина Мария Надежда Наталья Нина Оксана Ольга Полина
Раиса Светлана София Тамара Татьяна Юлия Яна Лилия Вероника Анжела Инна Эдуард Эльвира Руслана Снежана Сніжана Олеся Леся Алёна Альона
Зураб Давид Марк Матвій Арсеній Остап Мирон Злата Соломія Єва Аріна Варвара Мілана Емілія Ілона Орест Владислав Владислава Гліб Семен Ганна""".split()
_STEMS = {}
for n in FIRST:
    stem = re.sub(r'(ій|ий|ей|ія|ья|ья|а|я|о|ь|й)$', '', n)
    if len(stem) >= 2:
        _STEMS.setdefault(stem, n)


# what a first name takes in its case forms: "Андрія", "Марку", "Олені"; never a surname ending like "Андрєєв", "Марков", "Юрків"
CASE_ENDINGS = {'', 'а', 'я', 'и', 'у', 'ю', 'і', 'ї', 'е', 'є', 'о', 'ом', 'ем', 'єм', 'ою', 'ею', 'єю', 'ові', 'еві', 'єві',
                'ій', 'ий', 'ей', 'ія', 'ії', 'ію', 'ією', 'ь', 'й', 'ко', 'ка', 'ку', 'ком', 'ці', 'ну', 'на', 'ни', 'ні', 'ною',
                'ия', 'ии', 'ию', 'ием', 'ией', 'ы', 'ой'}  # Russian: "Георгия", "Марии", "Галины", "Галиной"


def first_name(word):
    alt = re.sub(r'(з|ц|с)і$', lambda m: {'з': 'г', 'ц': 'к', 'с': 'х'}[m.group(1)] + 'і', word)  # Ользі = Ольга
    if alt != word and _first_name(alt):
        return word
    return _first_name(word)


def _first_name(word):
    """The nominative first name if `word` is one (in any case form), else None."""
    for cut in range(len(word), 1, -1):
        n = _STEMS.get(word[:cut])
        if n and word[cut:] in CASE_ENDINGS and (word == n or cut >= len(re.sub(r'(ій|ий|ей|ія|ья|а|я|о|ь|й)$', '', n))):
            return n if word == n else word  # keep the inflected form the text used
    return None


# "Кошелевич" is a surname that only looks like a patronymic
PATRONYMIC = re.compile(r"^(?!(?:Кошелевич)$)[А-ЯІЇЄҐ][а-яіїєґ'’]+(ович|евич|євич|йович|івна|ївна|овна|евна|ічна|ична|інічна|ович[аеуі]|овичем|івни|івною|івні|ївни|ївні|овны|овной|евны)$")
UP = r"[А-ЯІЇЄҐ]"
WORD = rf"{UP}(?:[а-яіїєґ'’]|&#x27;|&#039;)+(?:-{UP}[а-яіїєґ'’]+)?"  # the apostrophe may come HTML-encoded
# capitalised words that are not surnames
NOT_SURNAME = re.compile(r'^(Примор|Преслав|Маринів|Мариновк|Юр.ївк|Україн|Запоріз|Бердян|Мелітоп|Київ|Одес|Харків|Дніпр|Львів|Азов|Бог(?:а|у|ом|ові)?\b|Богород|Господ|Христ|Різдв|'
                         # months as whole words only: prefixes like "Мар", "Лип", "Серп" are also surnames (Марченко, Липенко)
                         r'(?:(?:Січ|Берез|Квіт|Трав|Черв|Лип|Серп|Верес|Жовт|Груд)(?:ень|ня|ні)|Лют(?:ий|ого|ому)|Листопад\w*|'
                         r'Январ\w*|Феврал\w*|Март\w?|Апрел\w*|Ма[яй]|Июн\w*|Июл\w*|Август\w*|Сентябр\w*|Октябр\w*|Ноябр\w*|Декабр\w*)$|'
                         r'Міськ|Сільськ|Районн|Обласн|Державн|Національн|Громад|Рад[аиіеу]|Верховн|Президент|Депутат|Голов(?:а|и|і|у|ою)\b|Центр|Будин|'
                         r'Школ|Ліце|Гімназ|Бібліотек|Музе|Парк|Сквер|Площ|Вулиц|Проспект|Свят|Дн[яі]|День|Фестивал|Олімпіад|Кубок|'
                         r'Приват|Ощад|Укр|Нафто|Газ|Енерго|Водо|Агро|Морськ|(?:Велик|Нов|Стар|Черн|Чорн|Бел|Біл|Червон|Зелен)(?:ий|ій|ый|ая|а|е|і|ого|ої|им|ім|ому|ою|их|ими|у|ю|ое|ой|ые)\b|Прикордон|Поліці|Армі|Збройн|Отец|Отц)', re.I)
# well-known people and street/institution names that must keep their full form
FAMOUS = re.compile(r'(Шевченк|Франк|Українк|Хмельницьк|Грушевськ|Сковород|Котляревськ|Мазеп|Бандер|Стус|Довженк|Сухомлинськ|'
                    r'Пушкін|Пушкин|Гагарін|Гагарин|Ломоносов|Толст|Чехов|Гоголь|Гогол|Ботев|Кирил[ао]?\s+(?:[іиy]|та)\s+Мефод|Купал|Мефоді|Глєбов|Глебов|Фомін|Ногай|Янукович|Ющенк|Кучм|Порошенк|Зеленськ|Тимошенк|Кравчук)')
# "Президент Віктор Федорович": the word before a name + patronymic may be a title, never a place (surnames like Старчук, Чернова are real)
# colour / "new" / "old" adjectives: not a surname on their own, but "Чорна Ганна Василівна" is one
ADJ = re.compile(r'^(?:Велик|Нов|Стар|Черн|Чорн|Бел|Біл|Червон|Зелен)(?:ий|ій|ый|ая|а|е|і|ого|ої|им|ім|ому|ою|их|ими|у|ю|ое|ой|ые)$')
ROLE = re.compile(r'^(?:Голов(?:а|и|і|у|ою)|(?:Президент|Депутат|Директор|Начальник|Заступник|Секретар|Керівник|Міністр|Губернатор|Мер|Пан|Отець|Отця|Протоієре|Священик|Вчител|Учител|Лікар|Доповідач|Тренер|Вихователь|Методист|Завідувач|Учень|Учениц|Студент|Випускни|Ведуч|Автор|Фото|Текст|Переможець|Переможниц|Учасни|Організатор|Спікер|Модератор|Гість|Гостя|Кандидат|Нардеп|Отаман)[а-яіїєґ]{0,3})(?![а-яіїєґ])')
PLACE_BEFORE = re.compile(r'(вул\.|вулиц[яіюе]|пров\.|провулок|пл\.|площ[аіу]|просп\.|проспект|бульв\.|парк|сквер|\bім\.|імені|имени|'
                          r'школ[аиі]|ліце[йю]|гімназі[яї]|пам.ятник|меморіал|премі[яї])\s*$', re.I)


def _abbr_surname(s):
    return s[0] + '.'


def _shorten(text):
    def keep(m):
        return PLACE_BEFORE.search(text[max(0, m.start() - 25):m.start()]) or FAMOUS.search(m.group(0))

    # Surname Name Patronymic  /  Name Patronymic Surname
    def trio(m):
        a, b, c = m.group(1), m.group(2), m.group(3)
        # "школи Нестеров Роман Васильович": a place word before a name + patronymic is just context, not "school named after"
        if FAMOUS.search(m.group(0)) or (keep(m) and not (PATRONYMIC.match(c) or PATRONYMIC.match(b))):
            return None
        # a patronymic proves the word before it is a first name, listed or not
        # the joiner keeps the later passes from reading "Генадій А." as surname + initial; it becomes a space at the end
        if PATRONYMIC.match(c) and not PATRONYMIC.match(b) and not (ROLE.match(a) or NOT_SURNAME.match(a) and not ADJ.match(a)):
            if re.match(rf'\s+{WORD}\b', text[m.end():]):  # "Доповідач Іван Петрович Сидоренко": the surname is the word after
                return None
            return f'{b}\u2060{_abbr_surname(a)}'
        if PATRONYMIC.match(b) and not PATRONYMIC.match(a) and not (ROLE.match(c) or NOT_SURNAME.match(c) and not ADJ.match(c)):
            return f'{a}\u2060{_abbr_surname(c)}'
        return None
    text = _scan(text, re.compile(rf'\b({WORD})\s+({WORD})\s+({WORD})\b'), trio)

    # "Наталія Ф. Гриценко": what an earlier pass left of "Наталія Федорівна Гриценко"
    def name_init_sur(m):
        a, c = m.group(1), m.group(3)
        if first_name(a) and not first_name(c) and not (NOT_SURNAME.match(c) or ROLE.match(c) or FAMOUS.search(c)):
            return f'{a} {_abbr_surname(c)}'
        return None
    text = _scan(text, re.compile(rf'\b({WORD})\s+({UP})\.\s?({WORD})\b'), name_init_sur)
    # initials + surname, surname + initials
    def init_sur(m):
        return m.group(0) if keep(m) or NOT_SURNAME.match(m.group(3)) else f'{m.group(1)}. {m.group(2) + ". " if m.group(2) else ""}{_abbr_surname(m.group(3))}'
    text = re.sub(rf'\b({UP})\.\s?(?:({UP})\.\s?)?({WORD})\b', init_sur, text)

    def sur_init(m):
        if first_name(m.group(1)):  # "Ірина Д." is already short: a first name, not a surname
            return m.group(0)
        return m.group(0) if keep(m) or NOT_SURNAME.match(m.group(1)) else f'{m.group(2)}. {m.group(3) + ". " if m.group(3) else ""}{_abbr_surname(m.group(1))}'
    text = re.sub(rf'\b({WORD})\s+({UP})\.\s?(?:({UP})\.)?(?![а-яіїєґ])', sur_init, text)

    # Name Surname  /  Surname Name
    def duo(m):
        a, b = m.group(1), m.group(2)
        if keep(m) or PATRONYMIC.match(a) or PATRONYMIC.match(b):
            return m.group(0)
        if first_name(a) and not first_name(b) and not (NOT_SURNAME.match(b) or ROLE.match(b)) and len(b) > 2:
            return f'{a} {_abbr_surname(b)}'
        if first_name(b) and not first_name(a) and not (NOT_SURNAME.match(a) or ROLE.match(a)) and len(a) > 2:
            return f'{b} {_abbr_surname(a)}'
        return None
    text = _scan(text, re.compile(rf'\b({WORD})\s+({WORD})\b'), duo)
    return re.sub(r'\b([А-ЯІЇЄҐ])\.\.(?!\.)', r'\1.', text).replace('\u2060', ' ')  # "Т." + the sentence's own full stop


def _scan(text, pattern, fn):
    """Like pattern.sub(fn), but a match fn leaves alone (None) advances by one word, not the whole match:
    in "Приморська Сергій Тарасов" or "Верховній Раді Артем Вікторович" the name starts at the 2nd word."""
    out, pos = [], 0
    while (m := pattern.search(text, pos)):
        new = fn(m)
        if new is None:
            out.append(text[pos:m.end(1)])
            pos = m.end(1)
            continue
        out.append(text[pos:m.start()] + new)
        pos = m.end()
    return ''.join(out) + text[pos:]


def shorten(s):
    """Works on plain text or simple HTML (tags and attributes are left alone)."""
    if not ABBREVIATE or not s:
        return s
    if '<' in s:
        s = _across_tags(s)
    return ''.join(part if part.startswith('<') else _shorten(part) for part in re.split(r'(<[^>]+>)', s))


_SEP = r'((?:\s|<[^>]+>|&nbsp;)+)'
_TRIO_TAGS = re.compile(rf'\b({WORD}){_SEP}({WORD}){_SEP}({WORD})\b')


def _across_tags(h):
    """Name + patronymic split by markup (table cells "Прізвище | Ім'я | По батькові", bold halves):
    the surname becomes its initial and the patronymic goes, every tag stays where it was."""
    def fix(m):
        a, s1, b, s2, c = m.groups()
        if '<' not in s1 + s2 or FAMOUS.search(m.group(0)):
            return None
        if PATRONYMIC.match(c) and not PATRONYMIC.match(b) and not (ROLE.match(a) or NOT_SURNAME.match(a) and not ADJ.match(a)):
            return f'{_abbr_surname(a)}{s1}{b}{s2}'
        if PATRONYMIC.match(b) and not PATRONYMIC.match(a) and not (ROLE.match(c) or NOT_SURNAME.match(c) and not ADJ.match(c)):
            return f'{a}{s1}{s2}{_abbr_surname(c)}'
        return None
    return _scan(h, _TRIO_TAGS, fix)


if __name__ == '__main__':
    t = lambda a, b: (shorten(a) == b) or print('FAIL', repr(a), '->', repr(shorten(a)), 'expected', repr(b))
    t('Дробига Ірина Олександрівна, начальник відділу', 'Ірина Д., начальник відділу')
    t('Ірина Олександрівна Дробига', 'Ірина Д.')
    t('Міський голова О.А. Бондарова', 'Міський голова О. А. Б.')
    t('Підготувала Ігнатова В.В.', 'Підготувала В. В. І.')
    t('автор: Оксана Зоріна / камера: Олександр Савчин', 'автор: Оксана З. / камера: Олександр С.')
    t('Зорина Оксана', 'Оксана З.')
    t('вітає Мелікідзе Зураба, учня', 'вітає Зураба М., учня')
    t('Мороз Олена', 'Олена М.')
    t('з 5 березня Олена', 'з 5 березня Олена')
    t('на вул. Тараса Шевченка біля школи', 'на вул. Тараса Шевченка біля школи')
    t('Приморська міська рада', 'Приморська міська рада')
    t('Сергій Ведмеденко привітав', 'Сергій В. привітав')
    t('жителя Преслава Георгия Гордеева, семьей Тони Валчева', 'жителя Преслава Георгия Г., семьей Тони В.')  # Russian cases; village is no surname
    t('представитель Приморска Сергей Тарасов.', 'представитель Приморска Сергей Т.')
    t('<p>Павло Іванович Гончаров</p>', '<p>Павло Г.</p>')
    t('Василь Миколайович Фомін', 'Василь Миколайович Фомін')  # historical figure (prym.in.ua)
    print('ok')
