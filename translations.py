"""Ukrainian titles/excerpts for Russian-language chronicle items (translations.json, keyed by article id).

    python3 translations.py todo > todo.json    # items not translated yet: [{"n", "t", "x"}]
    python3 translations.py merge done.json     # add {id: {"t", "x"}} to translations.json, then rebuild

Translate todo.json by any means (it was done with Claude in batches of ~250, rules: literary Ukrainian,
official place names, keep "Ірина Д." / "[ПІБ приховано]" tokens as they are). extract_articles.py shows the
translation and keeps the Russian title as "Оригінал: …" (searchable).
"""
import html, json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(ROOT, 'translations.json')


def russian(s):
    return len(re.findall(r'[ыэъё]', s, re.I)) > len(re.findall(r'[іїєґ]', s, re.I))


def todo():
    done = json.load(open(PATH, encoding='utf-8'))
    items = []
    for t in json.load(open(os.path.join(ROOT, 'timeline', 'data.json'), encoding='utf-8')):
        if t['n'] in done or t.get('to'):
            continue
        body = html.unescape(re.sub(r'<[^>]+>', ' ', open(os.path.join(ROOT, 'timeline', 'a', t['n'] + '.html'), encoding='utf-8').read()))
        if russian(t['t'] + ' ' + t.get('x', '')) or russian(body):
            items.append({'n': t['n'], 't': t['t'], 'x': t.get('x', '')})
    json.dump(items, sys.stdout, ensure_ascii=False, indent=0)


def merge(path):
    done = json.load(open(PATH, encoding='utf-8'))
    new = json.load(open(path, encoding='utf-8'))
    assert all(v.get('t') for v in new.values()), 'every item needs a title'
    done.update(new)
    json.dump(done, open(PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f'{len(new)} added, {len(done)} total')


if __name__ == '__main__':
    assert russian('Чтобы больше знать') and not russian('Щоб знати більше')
    todo() if sys.argv[1:] == ['todo'] else merge(sys.argv[2])
