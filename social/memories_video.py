"""The soundtrack and final mux of the «Спогади та мрії» video (2026-10-22).

    python3 social/memories_video.py <video.mp4> <events.json>    # writes social/prym-memories.mp4

The picture is a recording of the live page (/memories) driven by a small Puppeteer script: captions, a soft cursor
and the camera moves are played in the page, each step logged with its time in events.json. Here the chronicle's own
sound kit (sound.py) is laid on those times: a slow pad that walks A, F#m, D, E under the whole film, a bell when a
light is touched, a chime when a postcard opens, a few soft keys while a memory is typed, bells for the ending.
(Take 2 tried an arpeggio and a melody on top; the author preferred the plain pad, so they are gone.)
"""
import json, math, os, random, subprocess, sys
from sound import SR, track, add, bell, chime, chord, tick, save, NOTES

HERE = os.path.dirname(os.path.abspath(__file__))
CHORDS = [(110.0, 164.81, 220.0, 277.18, 329.63),   # A
          (92.50, 138.59, 185.0, 220.0, 277.18),    # F#m
          (73.42, 146.83, 185.0, 220.0, 293.66),    # D
          (82.41, 123.47, 164.81, 207.65, 246.94)]  # E


def walking_pad(buf, dur, bar=8.8, fade=2.2):
    """The pad chord changes every bar, each one swelling in over the last one's fade."""
    t, i = 0.0, 0
    while t < dur:
        fs, length = CHORDS[i % len(CHORDS)], min(bar + fade, dur - t)
        env = lambda x, L=length, first=(t == 0), last=(t + bar >= dur): min(1, x / (2.5 if first else fade)) * min(1, (L - x) / (2.0 if last else fade))
        add(buf, t, length, lambda x, e=env, fs=fs: e(x) * sum(math.sin(2 * math.pi * f * x) + math.sin(2 * math.pi * f * 1.003 * x) for f in fs) / 10, .22)
        t += bar
        i += 1


def soft_key(buf, at, rnd):  # a quiet key press: a short muffled click, much softer than the counter's tick
    add(buf, at, .025, lambda x: math.exp(-x * 260) * (rnd.random() * 2 - 1), .07)


def soundtrack(dur, events):
    buf, rnd, n = track(dur), random.Random(7), 0
    walking_pad(buf, dur)
    at = lambda name: [t for e, t in events if e == name]
    for t in at('reveal'): chord(buf, t)
    for t in at('hover'): add(buf, t, 2.5, bell(NOTES[0]), .2)
    for t in at('open'): chime(buf, t + .15)
    for t in at('turn'): add(buf, t, 2.5, bell(NOTES[1]), .2)
    for t in at('zoom'): add(buf, t, 2.5, bell(NOTES[2]), .2)
    for t in at('daily'): add(buf, t, 2.5, bell(NOTES[3 - n % 2]), .18); n += 1
    for t in at('form'): add(buf, t, 2.5, bell(NOTES[2]), .18)
    for f, e in zip(at('typing'), at('typed')):  # soft keys while the memory is typed
        x = f + .05  # unhurried, irregular keys: a press every 0.13–0.25 s, not one per letter
        while x < e:
            soft_key(buf, x, rnd)
            x += .13 + rnd.random() * .12
    for t in at('quote'): add(buf, t, 2.5, bell(NOTES[0]), .16)
    for t in at('title'): chord(buf, t)
    for t in at('url'): chime(buf, t)
    return buf


if __name__ == '__main__':
    video, events = sys.argv[1], json.load(open(sys.argv[2]))
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', video]))
    wav = os.path.join(HERE, 'sounds', 'memories-track.wav')
    save(soundtrack(dur, events), os.path.basename(wav))
    out = os.path.join(HERE, 'prym-memories.mp4')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', video, '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', out], check=True)
    print(out, os.path.getsize(out) // 1024, 'KB,', round(dur, 1), 's')
