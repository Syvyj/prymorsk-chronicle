"""Full-text search for the chronicle: every word of every article -> the records it is in (timeline/search/).

Shards by the word's first letter, or its first two letters for the big letters (keys.json lists the two-letter ones),
so a query loads a few hundred kilobytes, not the 58 MB of texts. A shard's file is named by its letters' code points
(«пр» -> 43f-440.json): Cyrillic file names could be stored decomposed on the drive and then never found. Ids are positions in chronicle.json (same build),
delta-encoded. Called by extract_articles.py; the page matches a query word as the start of a word, like a stem.
"""
import json, os, re, shutil
import clean_article

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'timeline', 'search')
WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*")
BIG = 120_000  # bytes of JSON: a first letter with more is split by the second letter


def name(key):
    return '-'.join(f'{ord(c):x}' for c in key)


def words(text):
    return {w for w in WORD.findall(text.lower().replace('’', "'").replace('ʼ', "'")) if len(w) >= 3}


def write(records, text_of):
    """records: the chronicle.json rows in order; text_of(n): the article's plain text."""
    index = {}
    for i, a in enumerate(records):
        for w in words(text_of(a['n'])):
            index.setdefault(w, []).append(i)
    by_letter = {}
    for w in index:
        by_letter.setdefault(w[0], []).append(w)
    shards, two = {}, []
    for letter, ws in by_letter.items():
        if sum(len(w) + 6 * len(index[w]) for w in ws) > BIG:
            two.append(letter)
            for w in ws:
                shards.setdefault(w[:2], []).append(w)
        else:
            shards[letter] = ws
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    for key, ws in shards.items():
        data = {w: [ids[0]] + [b - a for a, b in zip(ids, ids[1:])] for w in sorted(ws) for ids in [index[w]]}
        json.dump(data, open(os.path.join(OUT, f'{name(key)}.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump(sorted(two), open(os.path.join(OUT, 'keys.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    return len(index), len(shards)


def plain(n):
    return clean_article.to_text(open(os.path.join(ROOT, 'timeline', 'a', n + '.html'), encoding='utf-8').read())


if __name__ == '__main__':
    assert words('Приморськ, п’ять і 2018 сім’я ДТЕК') == {'приморськ', "п'ять", "сім'я", 'дтек'}
    assert name('пр') == '43f-440' and name('a') == '61'
    print('ok')
