"""Check every YouTube video referenced by the articles without downloading it.

    python3 video_survey.py      # writes videos_meta.jsonl (resumable), prints a summary

Each line: {"id", "ok", "availability", "duration", "channel", "upload_date", "title", "error"}
"""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'videos_meta.jsonl')
FIELDS = ['id', 'availability', 'duration', 'channel', 'upload_date', 'title']


def probe(vid):
    r = subprocess.run(['yt-dlp', '--skip-download', '--no-warnings', '--ignore-no-formats-error',
                        '-O', '%(' + ')s\t%('.join(FIELDS) + ')s', f'https://www.youtube.com/watch?v={vid}'],
                       capture_output=True, text=True, timeout=120)
    line = r.stdout.strip().split('\n')[-1] if r.stdout.strip() else ''
    if r.returncode == 0 and line.count('\t') == len(FIELDS) - 1:
        d = dict(zip(FIELDS, line.split('\t')))
        d['duration'] = int(d['duration']) if d['duration'].isdigit() else None
        if d['title'] == f'youtube video #{vid}' and d['availability'] == 'NA':  # placeholder of a removed / private video
            return {'id': vid, 'ok': False, 'error': 'Video unavailable'}
        return {**d, 'id': vid, 'ok': True, 'error': ''}
    err = (r.stderr.strip().split('\n') or [''])[-1]
    if 'not a bot' in err:
        raise SystemExit('YouTube asks to confirm we are not a bot: stop now, re-run in a few hours (progress is kept)')
    return {'id': vid, 'ok': False, 'error': err.replace('ERROR: ', '')[:300]}


def summary(rows):
    ok = [r for r in rows if r['ok']]
    hours = sum(r['duration'] or 0 for r in ok) / 3600
    chans = {}
    for r in ok:
        c = chans.setdefault(r['channel'], [0, 0])
        c[0] += 1
        c[1] += (r['duration'] or 0) / 3600
    print(f'checked {len(rows)}: available {len(ok)}, gone {len(rows) - len(ok)}, total {hours:.0f} h')
    # rough sizes: 360p ≈ 0.14 GB/h, 720p ≈ 0.33 GB/h (measured on a council session video)
    print(f'estimated size: 360p ≈ {hours * 0.14:.0f} GB, 720p ≈ {hours * 0.33:.0f} GB')
    for name, (n, h) in sorted(chans.items(), key=lambda kv: -kv[1][0])[:10]:
        print(f'  {n:5} videos {h:7.1f} h  {name}')


if __name__ == '__main__':
    ids = list(json.load(open(os.path.join(ROOT, 'videos.json'))))
    done = {}
    if os.path.exists(OUT):
        for line in open(OUT):
            r = json.loads(line)
            # "Sign in to confirm you're not a bot" leaves empty metadata: not gone, just blocked; check again later
            if r['ok'] and r.get('duration') is None and r.get('availability') == 'NA':
                continue
            done[r['id']] = r
    todo = [v for v in ids if v not in done]
    print(f'{len(todo)} to check, {len(done)} already done', flush=True)
    # ponytail: 2 parallel probes; at 4 YouTube started asking to sign in after ~1200 videos
    with ThreadPoolExecutor(2) as pool, open(OUT, 'a') as f:
        for i, r in enumerate(pool.map(probe, todo), 1):
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
            f.flush()
            done[r['id']] = r
            if i % 100 == 0:
                print(f'{i}/{len(todo)}', flush=True)
    summary(list(done.values()))
