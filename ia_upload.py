"""Upload our video copies to the Internet Archive: one item per video, the YouTube original credited as source.

    .venv/bin/python ia_upload.py --one <youtube id>   # a single test item
    .venv/bin/python ia_upload.py --all                # everything allowed (resumable, log: ia_uploads.jsonl)

Needs `.venv/bin/ia configure` done by the account owner (the script never sees the password).
Only channels whose owners agreed; council session recordings are never uploaded (see video_download.verdict).
"""
import glob, html, json, os, sys, time
from internetarchive import get_item, upload
import video_download

ROOT = os.path.dirname(os.path.abspath(__file__))
DEST = video_download.DEST
LOG = os.path.join(ROOT, 'ia_uploads.jsonl')
# consent: the council (the author ran its site), the NGO's own studio, TRK "Yug" Prymorsk and Berdiansk (on condition: link to their YouTube)
ALLOWED = {'Приморська Міська Рада', 'Студія Прим24', 'ТРК "ЮГ" - Приморск', 'ТРК Юг Бердянск'}
PAUSE = 300  # seconds between new items: a new account creating items quickly is flagged as spam
SUBJECTS = ['Приморськ', 'Prymorsk', 'Primorsk', 'Запорізька область', 'Zaporizhzhia oblast', 'Ukraine', 'community archive', 'Хроніка громади']


def identifier(yid):
    return f'prymorsk-chronicle-{yid}'


def candidates():
    """(info, mp4, jpg) of every local copy that may go public."""
    ok = {r['id'] for r in video_download.rows() if video_download.verdict(r) == 'download'}
    for info_path in sorted(glob.glob(os.path.join(DEST, '*', '*.info.json'))):
        info = json.load(open(info_path, encoding='utf-8'))
        mp4 = info_path[:-len('.info.json')] + '.mp4'
        # long council session recordings are excluded by verdict(); short parts of a sitting are fine (author's call)
        if info.get('channel') in ALLOWED and info['id'] in ok and os.path.exists(mp4):
            jpg = mp4[:-4] + '.jpg'
            yield info, mp4, jpg if os.path.exists(jpg) else None


def metadata(info):
    d = info.get('upload_date') or ''
    date = f'{d[:4]}-{d[4:6]}-{d[6:8]}' if len(d) == 8 else ''
    yt, ch = info['webpage_url'], info['channel']
    desc = html.escape((info.get('description') or '').strip())[:3000].replace('\n', '<br>')
    return {
        'mediatype': 'movies', 'collection': 'opensource_movies',
        'title': info['title'], 'creator': ch, 'date': date, 'subject': SUBJECTS,
        'source': yt,  # the owners' condition: their YouTube stays the credited source
        'description': (f'<p><b>Джерело / Source:</b> {html.escape(ch)}, YouTube — <a href="{yt}">{yt}</a>'
                        + (f' (канал: <a href="{info["channel_url"]}">{info["channel_url"]}</a>)' if info.get('channel_url') else '') + '</p>'
                        + (f'<p>{desc}</p>' if desc else '')
                        + '<p>Копія збережена для архіву «Приморськ. Хроніка громади» — пам\'ять громади окупованого '
                          'Приморська (Запорізька область, Україна), 2004–2022.</p>'),
    }


def done():
    # only the items that went through: timeouts and refusals are tried again on the next run
    return {r['id'] for l in open(LOG) if (r := json.loads(l)).get('ok')} if os.path.exists(LOG) else set()


def push(info, mp4, jpg):
    files = {os.path.basename(mp4): mp4, **({os.path.basename(jpg): jpg} if jpg else {})}
    r = upload(identifier(info['id']), files=files, metadata=metadata(info), retries=10, retries_sleep=60,
               checksum=True, verbose=False)
    # the item itself is the proof: an earlier timed-out run may already have put the file there
    ok = all(x.status_code == 200 for x in r) or os.path.basename(mp4) in {f['name'] for f in get_item(identifier(info['id'])).files}
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'id': info['id'], 'identifier': identifier(info['id']), 'file': os.path.basename(mp4), 'ok': ok}) + '\n')
    return ok


if __name__ == '__main__':
    assert identifier('FRfdN_hyKTU') == 'prymorsk-chronicle-FRfdN_hyKTU'
    items = list(candidates())
    if sys.argv[1:2] == ['--one']:
        items = [c for c in items if c[0]['id'] == sys.argv[2]]
        assert items, 'not an allowed local video'
    elif sys.argv[1:] != ['--all']:
        sys.exit(__doc__)
    have = done()
    todo = [c for c in items if c[0]['id'] not in have]
    print(f'{len(items)} allowed, {len(todo)} to upload', flush=True)
    refused = 0
    for i, c in enumerate(todo, 1):
        try:
            ok = push(*c)
            refused = 0
        except Exception as e:
            # one item refused by the spam check (e.g. the 6th near-identical title): log it, go on;
            # several in a row means the account is throttled: stop, never hammer the archive
            refused += 1
            with open(LOG, 'a', encoding='utf-8') as f:
                f.write(json.dumps({'id': c[0]['id'], 'identifier': identifier(c[0]['id']), 'ok': False, 'error': str(e)[:200]}) + '\n')
            print(f'{i}/{len(todo)} REFUSED {c[0]["id"]} {c[0]["title"][:60]}', flush=True)
            if refused >= 3:
                sys.exit('stopped: three refusals in a row')
            time.sleep(PAUSE)
            continue
        print(f'{i}/{len(todo)} {"ok" if ok else "FAILED"} {c[0]["id"]} {c[0]["title"][:60]}', flush=True)
        time.sleep(PAUSE)
