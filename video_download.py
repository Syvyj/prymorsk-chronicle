"""Back up the YouTube videos used in the articles to the external drive.

    python3 video_download.py --plan    # what would be downloaded / skipped, with hours and size estimate
    python3 video_download.py           # download (resumable: yt-dlp keeps a download archive)
    python3 video_download.py --index   # refresh timeline/videos.json from what is on the drive

Skipped on purpose:
  * long council session recordings: the council team hid them deliberately and they must not be republished;
  * videos that are no longer available.
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
DEST = os.environ.get('PRYM_ARCHIVE', '../prymorsk-archive') + '/video'
META = os.path.join(ROOT, 'videos_meta.jsonl')
SESSION = re.compile(r'сесі|засідан|сессия|заседани', re.I)
COUNCIL = 'Приморська Міська Рада'


_local = None


def local_ids():
    """Videos embedded in articles that are about the community (scope 'local'); world news clips are not ours to keep."""
    global _local
    if _local is None:
        scope = {a['path']: a['scope'] for a in json.load(open(os.path.join(ROOT, 'articles.json')))}
        vids = json.load(open(os.path.join(ROOT, 'videos.json')))
        _local = {v for v, paths in vids.items() if any(scope.get(p) == 'local' for p in paths)}
    return _local


def verdict(r):
    if r['id'] not in local_ids():
        return 'skip: not about the community'
    if r['ok'] and r.get('duration') is None and r.get('availability') == 'NA':
        return 'wait: YouTube bot check, re-check later'
    if not r['ok'] or not r.get('duration') or r.get('channel') in (None, '', 'NA'):
        return 'skip: unavailable'
    long_ = r['duration'] > 30 * 60
    if long_ and (SESSION.search(r.get('title', '')) or r.get('channel') == COUNCIL):
        return 'skip: council session (hidden on purpose)'
    return 'download'


def rows():
    last = {}  # the survey appends re-checks; the newest line per video wins
    for line in open(META):
        r = json.loads(line)
        last[r['id']] = r
    return list(last.values())


def build_index():
    """timeline/videos.json: YouTube id -> our copy (served via the timeline/video symlink to the drive)."""
    index = {}
    for dirpath, _, files in os.walk(DEST):
        for f in files:
            m = re.fullmatch(r'\d{8}_([\w-]{11})\.mp4', f)
            if m:
                rel = os.path.relpath(os.path.join(dirpath, m.group(0)), DEST)
                thumb = rel[:-4] + '.jpg'
                index[m.group(1)] = {'src': 'video/' + rel, 'poster': 'video/' + thumb if os.path.exists(os.path.join(DEST, thumb)) else ''}
    if os.environ.get('SITE_URL'):  # published build: play the Internet Archive copies (ia_upload.py), the drive stays home
        # only the copies that are on the archive: any other video falls back to its YouTube embed (the drive is not online)
        ia, online = os.path.join(ROOT, 'ia_uploads.jsonl'), {}
        for r in map(json.loads, open(ia) if os.path.exists(ia) else []):
            if r.get('ok') and r['id'] in index:
                base = f"https://archive.org/download/{r['identifier']}/"
                online[r['id']] = {'src': base + r['file'], 'poster': base + r['file'][:-4] + '.jpg' if index[r['id']]['poster'] else ''}
        index = online
    json.dump(index, open(os.path.join(ROOT, 'timeline', 'videos.json'), 'w'), ensure_ascii=False)
    link = os.path.join(ROOT, 'timeline', 'video')
    if not os.path.islink(link):
        os.symlink(DEST, link)
    print(f'video index: {len(index)} local copies')


def plan():
    groups = {}
    for r in rows():
        g = groups.setdefault(verdict(r), [0, 0])
        g[0] += 1
        g[1] += (r.get('duration') or 0) / 3600
    for k, (n, h) in sorted(groups.items()):
        extra = f', ≈ {h * 0.33:.0f} GB at 720p' if k == 'download' else ''
        print(f'{k:45} {n:5} videos {h:7.1f} h{extra}')


def download():
    todo = [r['id'] for r in rows() if verdict(r) == 'download']
    os.makedirs(DEST, exist_ok=True)
    listfile = os.path.join(DEST, '_todo.txt')
    with open(listfile, 'w') as f:
        f.write('\n'.join(f'https://www.youtube.com/watch?v={v}' for v in todo))
    print(f'{len(todo)} videos to {DEST}', flush=True)
    subprocess.run([
        'yt-dlp', '-a', listfile,
        '--download-archive', os.path.join(DEST, '_downloaded.txt'),  # resume: skips what is already done
        '-f', 'bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/bv*[height<=720]+ba/b',
        '--merge-output-format', 'mp4',
        '-o', os.path.join(DEST, '%(channel)s', '%(upload_date)s_%(id)s.%(ext)s'),
        '--write-info-json', '--write-thumbnail', '--convert-thumbnails', 'jpg',
        '--no-overwrites', '--ignore-errors', '--no-warnings',
        '--sleep-interval', '2', '--max-sleep-interval', '6',  # ponytail: polite pace; YouTube throttles bursts
        '--progress', '--newline',
    ])
    build_index()


if __name__ == '__main__':
    if '--plan' in sys.argv:
        plan()
    elif '--index' in sys.argv:
        build_index()
    else:
        download()
