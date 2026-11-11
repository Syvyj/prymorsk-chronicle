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
Зураб Давид Марк Матвій Арсеній Остап Мирон Злата Соломія Єва Аріна Варвара Мілана Емілія Ілона Орест Владислав Владислава Гліб Семен Ганна
Эрнест Ернест Василиса Василіса Клавдия Клавдія Алина Алена Артур Никита Микита Даша Саша Оля Ира Женя Катя Лена Настя Вова Ліна Ліза
Элеонора Егор Илона Нинель Кристиан Виолетта Вита Віта Елла Едуард Лев Даниил Евдокия Пантелей Всеволод Опанас Джон Джона
Росица Донка Лалка Красимир Красімір Дімітр Димитр Давід Дафіна Мишо Сократ Анвер В’ячеслав Красимір Афанасія
Ія Ії Ію Ією Кузьма Генрих Генріх Мішо Петар Мар'яна Мар'ян Неля Нелля Неллі Нелли Пилип Ринат Рінат Ельміра Эльмира Йордан Йосип Иосиф
Венера Нона Рефат Анфіса Анфиса Марфа Яніна Янина Віолетта Ада Атанас Димитар Страшемир Севіль Ленур Ельдар Эльдар Зарема Рустем
Костя Стас Дима Ксюша Стася Софійка Марійка""".split()
# only as written: their stems are everyday words («Вас», «Вік», «Ан», «Ніколи», «Львові», «Вітаю»)
EXACT = set("""Аня Ані Аню Анею Таня Тані Таню Танею Соня Соні Соню Соней Вася Васі Васю Васею Віка Віки Віку Вікою Вика Вики Вику Викой
Діма Діми Діму Дімою Ніколь Льва Льву Львом Миколая Миколаю Миколаєм""".split())
FIRST_SET = set(FIRST) | EXACT
NAME_END = re.compile(r'(ій|ий|ей|ія|ья|а|я|о|ь|й)$')  # what a first name drops before its case endings
_STEMS = {}
for n in FIRST:
    stem = NAME_END.sub('', n)
    if len(stem) >= 2:
        _STEMS.setdefault(stem, n)


# what a first name takes in its case forms: "Андрія", "Марку", "Олені"; never a surname ending like "Андрєєв", "Марков", "Юрків"
CASE_ENDINGS = {'', 'а', 'я', 'и', 'у', 'ю', 'і', 'ї', 'е', 'є', 'о', 'ом', 'ем', 'єм', 'ою', 'ею', 'єю', 'ові', 'еві', 'єві',
                'ій', 'ий', 'ей', 'ія', 'ії', 'ію', 'ією', 'ь', 'й', 'ко', 'ка', 'ку', 'ком', 'ці', 'ну', 'на', 'ни', 'ні', 'ною',
                'ия', 'ии', 'ию', 'ием', 'ией', 'ы', 'ой',
                'ья', 'ьи', 'ье', 'ью', 'ьей', 'ея', 'ее', 'еем',
                'ієм', 'ієві'}  # «Юрієм», «Юрієві»  # Russian: "Георгия", "Марии", "Галины", "Галиной"


def first_name(word):
    word_ = word.replace('’', "'").replace('ʼ', "'").replace('&#x27;', "'").replace('&#039;', "'")  # «Дар’я» = «Дар'я»
    if '-' in word_:  # «Анна-Марія»: a double first name, every part a name
        return word if all(_first_name(p) for p in word_.split('-')) else None
    if word_ in FIRST_SET:
        return word
    alt = re.sub(r'(з|ц|с)і$', lambda m: {'з': 'г', 'ц': 'к', 'с': 'х'}[m.group(1)] + 'і', word)  # Ользі = Ольга
    if alt != word and _first_name(alt):
        return word
    return word if _first_name(word_) else None


def _first_name(word):
    """The nominative first name if `word` is one (in any case form), else None."""
    for cut in range(len(word), 1, -1):
        n = _STEMS.get(word[:cut])
        if n and word[cut:] in CASE_ENDINGS and (word == n or cut >= len(NAME_END.sub('', n))):
            return n if word == n else word  # keep the inflected form the text used
    return None


# "Кошелевич", "Захаревич" are surnames that only look like patronymics
PATRONYMIC = re.compile(r"^(?!(?:Кошелевич|Захаревич)$)[А-ЯІЇЄҐ][а-яіїєґ'’]+(ович|евич|євич|йович|івна|ївна|овна|евна|ічна|ична|інічна|ович[аеуі]|овичем|івни|івною|івні|ївни|ївні|овны|овной|евны|івну|ївну|овну|евну|овне|евне|овною|евною|ичну|ичні)$")
UP = r"[А-ЯІЇЄҐ]"
WORD = rf"{UP}(?:[а-яіїєґ'’]|&#x27;|&#039;)+(?:-{UP}[а-яіїєґ'’]+)?"  # the apostrophe may come HTML-encoded
# capitalised words that are not surnames
NOT_SURNAME = re.compile(r'^(Ногайськ|Ногайск|'
                         # the community's villages: «с. Набережне» is a place, not «С. Набережне» a person
                         r'Набережн|Подспор|Підспір|Банівк|Бановк|Борисівк|Борисовк|Інзівк|Инзовк|Орлівк|Орловк|Лозуватк|Лозоватк|Райнівк|Райновк|'
                         r'Радолівк|Радоловк|Нельгівк|Нельговк|Зеленівк|Зеленовк|Єлизаветівк|Елизаветовк|Єлисеївк|Елисеевк|Софіївк|Софиевк|'
                         r'Новопавлівк|Новопавловк|Новоолексіївк|Новоалексеевк|Мануйлівк|Мануйловк|Лозанівк|Лозановк|Гюнівк|Гюновк|Петрівк|Петровк|'
                         r'Калинівк|Калиновк|Підгірн|Подгорн|Комишуватк|Камышеватк|В.ячеславк|Вячеславк|'
                         r'Геро(?:й|я|ю|єм|ям|ї|ев)\b|Бюст|Барельєф|Барельеф|Пам.ятник|Памятник|Примор|Преслав|Маринів|Мариновк|Юр.ївк|Україн|Запоріз|Бердян|Мелітоп|Київ|Одес|Харків|Дніпр|Львів|Азов|Бог(?:а|у|ом|ові)?\b|Богород|Господ|Христ|Різдв|'
                         # months as whole words only: prefixes like "Мар", "Лип", "Серп" are also surnames (Марченко, Липенко)
                         r'(?:(?:Січ|Берез|Квіт|Трав|Черв|Лип|Серп|Верес|Жовт|Груд)(?:ень|ня|ні)|Лют(?:ий|ого|ому)|Листопад\w*|'
                         r'Январ\w*|Феврал\w*|Март\w?|Апрел\w*|Ма[яй]|Июн\w*|Июл\w*|Август\w*|Сентябр\w*|Октябр\w*|Ноябр\w*|Декабр\w*)$|'
                         r'Міськ|Сільськ|Районн|Обласн|Державн|Національн|Громад|Рад[аиіеу]|Верховн|Президент|Депутат|Голов(?:а|и|і|у|ою)\b|Центр|Будин|'
                         r'Школ|Ліце|Гімназ|Бібліотек|Музе|Парк|Сквер|Площ|Вулиц|Проспект|Свят|Дн[яі]|День|Фестивал|Олімпіад|Кубок|'
                         r'Приват|Ощад|Укр|Нафто|Газ|Енерго|Водо|Агро|Морськ|(?:Велик|Нов|Стар|Черн|Чорн|Бел|Біл|Червон|Зелен)(?:ий|ій|ый|ая|а|е|і|ого|ої|им|ім|ому|ою|их|ими|у|ю|ое|ой|ые)\b|Прикордон|Поліці|Армі|Збройн|Отец|Отц)', re.I)
# well-known people and street/institution names that must keep their full form
# the sculptor Володимир Давидович Микитенко (press: Нікітенко / Никитенко), only in forms that can't be another Нікітенко
SCULPTOR = r'(?:Володимир[а-я]{0,2}\s+(?:Давидович[а-я]{0,2}\s+)?|Владимир[а-я]{0,2}\s+(?:Давыдович[а-я]{0,2}\s+)?|В\.\s?(?:Д\.\s?)?)[НМ][иі]к[иі]т[еє]нк|(?:Володимир[а-я]{0,2}|Владимир[а-я]{0,2})\s+(?:Давидович|Давыдович)[а-я]{0,2}\s+[НМ][иі]к[иі]т[еє]нк|[НМ][иі]к[иі]т[еє]нк[а-я]{0,2}\s+(?:Володимир|Владимир)[а-я]{0,2}\s+(?:Давидович|Давыдович)|Володимир[а-я]{0,2}\s+Микит[еє]нк|Владимир[а-я]{0,2}\s+Никит[еє]нк|В\.\s?Никит[еє]нк|В\.\s?Нікіт[еє]нк|Нікіт[еє]нк[а-я]{0,2}\s+Володимир|Никит[еє]нк[а-я]{0,2}\s+Владимир'
# well-known people keep their full name only as the pair they are known by («Тарас Шевченко», «Т. Г. Шевченка»): a private
# Шевченко, Кравчук or Тимошенко next to another first name is shortened like anyone else
FAMOUS_PEOPLE = {  # surname stem: first-name stems (Ukrainian and Russian), their initials are taken from them
    'Шевченк': 'Тарас', 'Франк': 'Іван Иван', 'Теліг': 'Олен', 'Телиг': 'Елен Олен', 'Куліш': 'Пантелеймон Микол', 'Кулиш': 'Пантелеймон Никола',
    'Котляревськ': 'Іван', 'Котляревск': 'Иван Іван', 'Хмельницьк': 'Богдан', 'Хмельницк': 'Богдан', 'Грушевськ': 'Михайл', 'Грушевск': 'Михаил',
    'Сковород': 'Григор', 'Мазеп': 'Іван Иван', 'Бандер': 'Степан', 'Стус': 'Васил', 'Довженк': 'Олександр Александр', 'Сухомлинськ': 'Васил',
    'Сухомлинск': 'Васил', 'Костенк': 'Лін', 'Нестайк': 'Всеволод', 'Пушкін': 'Олександр', 'Пушкин': 'Александр Олександр', 'Гагарін': 'Юр',
    'Гагарин': 'Юр', 'Ломоносов': 'Михайл Михаил', 'Толст': 'Лев Льв Олекс Алексе', 'Чехов': 'Антон', 'Гогол': 'Микол Никола', 'Купал': 'Іван Иван',
    'Чорновол': "В'ячеслав В’ячеслав Вячеслав", 'Чорновіл': "В'ячеслав В’ячеслав Вячеслав", 'Фомін': 'Васил', 'Янукович': 'Віктор Виктор',
    'Ющенк': 'Віктор Виктор', 'Кучм': 'Леонід Леонид', 'Порошенк': 'Петр Марин', 'Зеленськ': 'Володимир Олен', 'Тимошенк': 'Юлі Юли',
    'Кравчук': 'Леонід Леонид', 'Ахметов': 'Рінат Ринат',
}
# names that are known without a first name or are never a private person's (pseudonyms, saints, the sculptor's alley)
FAMOUS_ALONE = r"Українк|Украинк|Ольжич|Гулак|Артемовськ|Артемовск|Олександр[а-я]{0,2}\s+Олес|Александр[а-я]{0,2}\s+Олес|Ботев|Глєбов|Глебов|Кирил[ао]?\s+(?:[іиy]|та)\s+Мефод|Мефоді"
_L = "[а-яіїєґ'’]"


def _famous_rx():
    out = []
    for sur, firsts in FAMOUS_PEOPLE.items():
        f = '|'.join(firsts.split()).replace("'", "(?:'|’|&#x27;|&#039;)").replace('’', "(?:'|’|&#x27;|&#039;)")
        ini = ''.join(sorted({x[0] for x in firsts.split()}))
        out += [rf"(?:{f}){_L}{{0,4}}\s+(?:{UP}{_L}+\s+)?{sur}", rf"{sur}{_L}{{0,4}}\s+(?:{f})",
                rf"[{ini}]\.\s?(?:{UP}\.\s?)?{sur}", rf"{sur}{_L}{{0,4}}\s+[{ini}]\."]
    return '|'.join(out)


FAMOUS = re.compile('(' + SCULPTOR + '|' + FAMOUS_ALONE + '|' + _famous_rx() + ')')
# "Президент Віктор Федорович": the word before a name + patronymic may be a title, never a place (surnames like Старчук, Чернова are real)
# colour / "new" / "old" adjectives: not a surname on their own, but "Чорна Ганна Василівна" is one
ADJ = re.compile(r'^(?:Велик|Нов|Стар|Черн|Чорн|Бел|Біл|Червон|Зелен)(?:ий|ій|ый|ая|а|е|і|ого|ої|им|ім|ому|ою|их|ими|у|ю|ое|ой|ые)$')
ROLE = re.compile(r'^(?:Голов(?:а|и|і|у|ою)|(?:Президент|Депутат|Директор|Начальник|Заступник|Секретар|Керівник|Міністр|Губернатор|Мер|Пан|Отець|Отця|Протоієре|Священик|Вчител|Учител|Лікар|Доповідач|Тренер|Вихователь|Методист|Завідувач|Учень|Учениц|Студент|Випускни|Ведуч|Автор|Фото|Текст|Переможець|Переможниц|Учасни|Організатор|Спікер|Модератор|Гість|Гостя|Кандидат|Нардеп|Отаман)[а-яіїєґ]{0,3})(?![а-яіїєґ])')
CAPS = r"[А-ЯІЇЄҐ][А-ЯІЇЄҐ'’]{2,}(?:-[А-ЯІЇЄҐ]{2,})?"
CAPS_SURNAME_END = re.compile(r'(?:[ЕЄ]НК[ОАУ]|[ЧЩ]?УК|ЮК|[ОЕЄ]В[АУ]?|[ІИ]Н[АУ]?|[СЦ]ЬК(?:ИЙ|А|ОГО|ОЇ)|ИЧ|ЕЦЬ|ЯН|[АЯИО]К|ОВОЇ|ЕНКА)$')
CAPS_NOT_SURNAME = {'ЗОДА', 'ОДА', 'РДА', 'УООР', 'ОТГ', 'ПРООН', 'ЮНІСЕФ', 'ЮНЕСКО', 'ООН', 'ОБСЄ', 'УЄФА', 'ФІФА', 'НАТО', 'ЄВРО', 'УКРАЇНА', 'УКРАИНА',
                    'ПРИМОРСЬК', 'ПРИМОРСК', 'АТО', 'ООС', 'ЗСУ', 'ВЛК', 'ФОП', 'ТОВ', 'ПАТ', 'ДТЕК', 'ДТЭК', 'АЗОВ', 'ІНФО', 'ВІДЕО', 'ФОТО', 'УВАГА'}
PLACE_BEFORE = re.compile(r'(вул\.|вулиц[яіюе]|пров\.|провулок|пл\.|площ[аіу]|просп\.|проспект|бульв\.|парк|сквер|\bім\.|імені|имени|'
                          r'пам.ятник|меморіал)\s*$', re.I)


def _abbr_surname(s):
    return s[0] + '.'


def _shorten(text):
    def keep(m):
        return PLACE_BEFORE.search(text[max(0, m.start() - 25):m.start()]) or FAMOUS.search(m.group(0))

    # «Олена БОЖКОВА», «ПЕТРЕНКО Ірина»: a surname in capitals beside a first name (bylines, lists of winners);
    # a capitalised abbreviation (ЗОДА, ДТЕК) is not one: it needs two vowels, before a name also a surname ending
    def caps(m):
        if m.group(1):
            name, cap = m.group(1), m.group(2)
            ok = first_name(name) and len(cap) >= 4
        else:
            cap, name = m.group(3), m.group(4)
            ok = first_name(name) and CAPS_SURNAME_END.search(cap)
        word = cap.capitalize()
        if not ok or cap in CAPS_NOT_SURNAME or sum(c in 'АЕЄИІЇОУЮЯ' for c in cap) < 2 or keep(m) or NOT_SURNAME.match(word) \
                or FAMOUS.search(f'{name} {word}') or FAMOUS.search(f'{word} {name}'):
            return m.group(0)
        return f'{name} {cap[0]}.'
    text = re.sub(rf'\b({WORD})\s+({CAPS})\b(?![а-яіїєґ])|\b({CAPS})\s+({WORD})\b', caps, text)

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

    # "Наталія Ф. Гриценка": what an earlier pass left of "Наталія Федорівна Гриценка"
    def name_init_sur(m):
        a, c = m.group(1), m.group(3)
        if first_name(a) and not first_name(c) and not (NOT_SURNAME.match(c) or ROLE.match(c) or FAMOUS.search(c) or PATRONYMIC.match(c)):
            return f'{a} {_abbr_surname(c)}'
        return None
    text = _scan(text, re.compile(rf'\b({WORD})\s+({UP})\.\s?({WORD})\b'), name_init_sur)
    # initials + surname, surname + initials
    def init_sur(m):
        # «Т. Я. О. Реформування»: the last of a row of initials stands before the next sentence, not before a surname
        if re.search(rf'{UP}\.\s?$', text[max(0, m.start() - 3):m.start()]):
            return m.group(0)
        # «Руденко Т.М. Під час заходу»: a surname stands before the initials (the next pass shortens it), the word after them
        # starts the next sentence
        prev = re.search(rf'({WORD})\s+$', text[max(0, m.start() - 40):m.start()])
        if prev and not (ROLE.match(prev.group(1)) or NOT_SURNAME.match(prev.group(1)) or first_name(prev.group(1)) or PATRONYMIC.match(prev.group(1))):
            return m.group(0)
        return m.group(0) if keep(m) or NOT_SURNAME.match(m.group(3)) or PATRONYMIC.match(m.group(3)) or first_name(m.group(3)) else f'{m.group(1)}. {m.group(2) + ". " if m.group(2) else ""}{_abbr_surname(m.group(3))}'
    text = re.sub(rf'\b({UP})\.\s?(?:({UP})\.\s?)?({WORD})\b', init_sur, text)

    def sur_init(m):
        if first_name(m.group(1)):  # "Ірина Д." is already short: a first name, not a surname
            return m.group(0)
        return m.group(0) if keep(m) or NOT_SURNAME.match(m.group(1)) or ROLE.match(m.group(1)) else f'{m.group(2)}. {m.group(3) + ". " if m.group(3) else ""}{_abbr_surname(m.group(1))}'
    text = re.sub(rf'\b({WORD})\s+({UP})\.\s?(?:({UP})\.)?(?![а-яіїєґ])', sur_init, text)

    # Name Surname  /  Surname Name
    def duo(m):
        a, b = m.group(1), m.group(2)
        if keep(m) or PATRONYMIC.match(a) or PATRONYMIC.match(b):
            return m.group(0)
        if first_name(a) and not first_name(b) and not (NOT_SURNAME.match(b) or ROLE.match(b)) and len(b) > 2:
            return f'{a} {_abbr_surname(b)}'
        if first_name(b) and not first_name(a) and not (NOT_SURNAME.match(a) or ROLE.match(a)) and len(a) > 2:
            # «Фонд Ріната Ахметова», «компанії Сергія Петренка»: the name goes on to the right, the word before it is not a surname
            if re.match(rf'\s+{UP}\.', text[m.end():]):  # «Республіки Сергій Б.»: already short, the word before is not a surname
                return None
            nxt = re.match(rf'\s+({WORD})\b', text[m.end():])
            if nxt and (FAMOUS.search(f'{b} {nxt.group(1)}') or not (first_name(nxt.group(1)) or PATRONYMIC.match(nxt.group(1))
                                                                    or NOT_SURNAME.match(nxt.group(1)) or ROLE.match(nxt.group(1)))):
                return None
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
    # «Андрея<br>Федорова»: a line break inside a name is a space to the passes (\u2028 is whitespace to re), a <br> again after
    s = re.sub(r'<br\s*/?>', '\u2028', s)
    s = ''.join(part if part.startswith('<') else _shorten(part) for part in re.split(r'(<[^>]+>)', s))
    return s.replace('\u2028', '<br>')


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
    t('Марченко Олена', 'Олена М.')
    t('з 5 березня Олена', 'з 5 березня Олена')
    t('на вул. Тараса Шевченка біля школи', 'на вул. Тараса Шевченка біля школи')
    t('Приморська міська рада', 'Приморська міська рада')
    t('Сергій Ведмеденко привітав', 'Сергій В. привітав')
    t('жителя Преслава Георгия Гордеева, семьей Тони Валчева', 'жителя Преслава Георгия Г., семьей Тони В.')  # Russian cases; village is no surname
    t('представитель Приморска Сергей Тарасов.', 'представитель Приморска Сергей Т.')
    t('<p>Павло Іванович Гончаров</p>', '<p>Павло Г.</p>')
    t('Василь Миколайович Фомін', 'Василь Миколайович Фомін')  # historical figure (prym.in.ua)
    t('Бюсты Тараса Шевченко, Леси Украинки, Ивана Франко, Василия Стуса, Елены Телигы, Олеся Ольжича, Гулака Артемовского, Ивана Котляревского. Это все',
      'Бюсты Тараса Шевченко, Леси Украинки, Ивана Франко, Василия Стуса, Елены Телигы, Олеся Ольжича, Гулака Артемовского, Ивана Котляревского. Это все')  # writers on a sculptor's alley
    t('Івана Котляревського, Петра Гулака-Артемовського, Пантелеймона Куліша, Василя Стуса, Олени Теліги та Олександра Олеся',
      'Івана Котляревського, Петра Гулака-Артемовського, Пантелеймона Куліша, Василя Стуса, Олени Теліги та Олександра Олеся')
    t('Олесь Петренко прийшов', 'Олесь П. прийшов')  # Олесь stays a first name
    t('скульптора Володимира Давидовича Нікітенка, який навесні', 'скульптора Володимира Давидовича Нікітенка, який навесні')
    t('«Алею авторських бюстів» Володимира Нікітенко', '«Алею авторських бюстів» Володимира Нікітенко')
    t('Два сборника Владимира Давыдовича Никитенко вышли', 'Два сборника Владимира Давыдовича Никитенко вышли')
    t('мало кто знает, что В.Никитенко, который', 'мало кто знает, что В.Никитенко, который')
    t('Відділ освіти вітає Никитенко Анну, ученицю', 'Відділ освіти вітає Анну Н., ученицю')  # another Никитенко stays private
    t('Приморський парк прикрасять скульптури Володимира Нікітєнка', 'Приморський парк прикрасять скульптури Володимира Нікітєнка')
    t('первые места завоевали Эрнест Ефремян из Веселого', 'первые места завоевали Эрнест Е. из Веселого')  # names.py missed rare first names
    t('участница Василиса Гладковская (руководитель Татьяна К.)', 'участница Василиса Г. (руководитель Татьяна К.)')
    t('вручил Сергея Тарасова и Натальи Левчук', 'вручил Сергея Т. и Натальи Л.')  # Russian -ея / -ьи cases
    t('Ліна Костенко', 'Ліна Костенко')
    # review 2026-11-10: a private namesake of a famous person, a school word before a name, capitals, cases, apostrophes
    t('Ірина Шевченко, учениця 5 класу', 'Ірина Ш., учениця 5 класу')
    t('Тимошенко Дарина, 3 клас', 'Дарина Т., 3 клас')
    t('переміг Максим Кравчук, а Сергій Чехов', 'переміг Максим К., а Сергій Ч.')
    t('Тарас Шевченко, Т. Г. Шевченка, Шевченко Тарас Григорович, Юлія Тимошенко', 'Тарас Шевченко, Т. Г. Шевченка, Шевченко Тарас Григорович, Юлія Тимошенко')
    t('учениця школи Ірина Петренко, директор ліцею Олена Бондаренко', 'учениця школи Ірина П., директор ліцею Олена Б.')
    t('школа імені Івана Петренка', 'школа імені Івана Петренка')
    t('Ірина ПЕТРЕНКО і ПЕТРЕНКО Олег', 'Ірина П. і Олег П.')
    t('ДТЕК Максим, ЗОДА Артур, Віталія ЗОДА, Петро ПОРОШЕНКО', 'ДТЕК Максим, ЗОДА Артур, Віталія ЗОДА, Петро ПОРОШЕНКО')
    t('з Юрієм Петренком і Миколая Бойка', 'з Юрієм П. і Миколая Б.')
    t('Дар’я Бойко, Ія Бойко, Аня Бойко, Анна-Марія Петренко', 'Дар’я Б., Ія Б., Аня Б., Анна-Марія П.')
    t('Олександра Носова з Ногайська', 'Олександра Н. з Ногайська')
    t('пам’яті Героя Федора Р.', 'пам’яті Героя Федора Р.')
    t('Компанії Сергія Петренка', 'Компанії Сергія П.')
    t('почесний консул Республіки Сергій Б. та Вітаємо Анастасію К.', 'почесний консул Республіки Сергій Б. та Вітаємо Анастасію К.')
    t('заседание для Андрея<br>Федорова, который<br>был', 'заседание для Андрея Ф., который<br>был')
    t('хімії Ткачову Світлану Вікторівну!', 'хімії Світлану Т.!')  # accusative patronymic
    t('вчитель Руденко Т.М. Під час заходу, Директор Т.М. Петренко', 'вчитель Т. М. Р. Під час заходу, Директор Т. М. П.')
    t('с. Набережне, С. Подспор’є, В&#x27;ячеслава Чорновола, Фонд Ріната Ахметова', 'с. Набережне, С. Подспор’є, В&#x27;ячеслава Чорновола, Фонд Ріната Ахметова')
    for once in ('Анна С. К. Анны Алексеевны делегаты', 'облдержадміністрації Т. Я. О. Реформування галузі', 'Олександр О. Вікторович побажав', 'Ірина Д., О. А. Б.'):
        t(once, once)  # already short: a second pass changes nothing
    print('ok')
