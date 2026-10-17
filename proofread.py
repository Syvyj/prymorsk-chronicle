"""Proofread headlines and excerpts (spelling, apostrophes, punctuation, ALL-CAPS headlines -> sentence case).

    python3 proofread.py merge todo_*.json -- done_*.json   # add the corrections to proofread.json
Each entry keeps the text it was made for ({"t_from", "t", "x_from", "x"}): extract_articles.py applies a
correction only while the record still reads exactly like that, so a rebuilt or changed record is never mangled.
"""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(ROOT, 'proofread.json')


def apply(t, fix):
    """t: a timeline entry {'t', 'x', ...}; fix: one proofread.json entry. Returns the fields to change."""
    out = {}
    if fix.get('t') and t['t'] == fix.get('t_from'):
        out['t'] = fix['t']
    if fix.get('x') and fix.get('x_from') and t['x'].startswith(fix['x_from']):
        out['x'] = fix['x'] + t['x'][len(fix['x_from']):]  # the excerpt was proofread as shown (cut), the rest follows
    return out


def merge(todo_files, done_files):
    src = {i['n']: i for f in todo_files for i in json.load(open(f, encoding='utf-8'))}
    have = json.load(open(PATH, encoding='utf-8')) if os.path.exists(PATH) else {}
    added = 0
    for f in done_files:
        for n, fix in json.load(open(f, encoding='utf-8')).items():
            if n not in src:
                continue
            e = {}
            if fix.get('t') and fix['t'] != src[n]['t']:
                e.update(t_from=src[n]['t'], t=fix['t'])
            if fix.get('x') and fix['x'] != src[n]['x']:
                e.update(x_from=src[n]['x'], x=fix['x'])
            if e:
                have[n] = e
                added += 1
    json.dump(have, open(PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    print(f'{added} corrections merged, {len(have)} in proofread.json')


if __name__ == '__main__':
    assert apply({'t': 'НАШІ ДОРОГИ', 'x': 'обєднання громад тощо'}, {'t_from': 'НАШІ ДОРОГИ', 't': 'Наші дороги', 'x_from': 'обєднання', 'x': 'об’єднання'}) == \
        {'t': 'Наші дороги', 'x': 'об’єднання громад тощо'}
    assert apply({'t': 'інший', 'x': 'інше'}, {'t_from': 'НАШІ', 't': 'Наші'}) == {}
    if sys.argv[1:2] == ['merge']:
        i = sys.argv.index('--')
        merge(sys.argv[2:i], sys.argv[i + 1:])
    else:
        print('ok')
