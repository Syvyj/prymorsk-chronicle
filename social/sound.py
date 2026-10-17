"""The chronicle's sound kit: everything synthesized here (no third-party samples, no licences to worry about).

    python3 social/sound.py            # writes social/sounds/*.wav (the kit) and social/sounds/update-12s.wav (the FB update track)

The kit (44.1 kHz, mono, 16-bit):
    pad-12s.wav       warm A-major pad, swells in over 2.5 s and fades out over 2 s — the background bed
    tick.wav          one soft click (noise + 1.8 kHz blip), for counters and lists
    ticks-2.6s.wav    a run of clicks that speeds up and slows down — the counter 9 558 -> 9 749
    chime.wav         two-note bell (A5 + E6) — "something new appeared" (the +191 pill)
    note-1..4.wav     single bells A4, B4, C#5, E5 — rising pentatonic steps, one per list item
    chord.wav         A-major bell chord (A4 C#5 E5 A5) — the closing / call to action
Pure stdlib (array, math, wave), so it runs anywhere.
"""
import array, math, os, random, wave

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sounds')


def track(seconds):
    return array.array('d', bytes(8 * int(SR * seconds)))


def add(buf, start, length, fn, gain):
    a = int(start * SR)
    for i in range(max(0, min(int(length * SR), len(buf) - a))):
        buf[a + i] += gain * fn(i / SR)


def bell(f):  # a soft marimba-like note: two partials, fast attack, exponential decay
    return lambda t: min(1, t * 200) * math.exp(-t * 3.2) * (math.sin(2 * math.pi * f * t) + .35 * math.sin(2 * math.pi * f * 3.01 * t) * math.exp(-t * 6))


def pad(buf, dur):  # A major (A2 E3 A3 C#4 E4), slight detune for warmth
    env = lambda t: min(1, t / 2.5) * min(1, (dur - t) / 2.0)
    add(buf, 0, dur, lambda t: env(t) * sum(math.sin(2 * math.pi * f * t) + math.sin(2 * math.pi * f * 1.003 * t)
                                            for f in (110.0, 164.81, 220.0, 277.18, 329.63)) / 10, .22)


def tick(buf, at, rnd):
    add(buf, at, .03, lambda x: math.exp(-x * 220) * (rnd.random() * 2 - 1), .18)
    add(buf, at, .05, lambda x: math.exp(-x * 90) * math.sin(2 * math.pi * 1800 * x), .06)


def ticks(buf, start, length, rnd):  # denser in the middle, like an eased count
    t = start
    while t < start + length:
        tick(buf, t, rnd)
        p = (t - start + .05) / (length + .05)  # the curve of the original FB track (ticks from 1.45 s, curve from 1.4 s)
        t += .05 + .16 * (2 * p - 1) ** 2


def chime(buf, at):
    add(buf, at, 3, bell(880.0), .30)
    add(buf, at, 3, bell(1318.5), .16)


NOTES = [440.0, 493.88, 554.37, 659.25]


def chord(buf, at):
    for f in (440.0, 554.37, 659.25, 880.0):
        add(buf, at, 3.8, bell(f), .14)


def save(buf, name, peak=None):
    peak = peak or max(abs(v) for v in buf) or 1
    with wave.open(os.path.join(OUT, name), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(array.array('h', (int(max(-1, min(1, v / peak * .85)) * 32767) for v in buf)).tobytes())


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    # the FB update track (2026-10): pad, ticks under the counter, chime on "+191", a note per village, chord with the address
    full = track(12.0)
    pad(full, 12.0)
    ticks(full, 1.45, 2.55, random.Random(7))
    chime(full, 4.0)
    for i, f in enumerate(NOTES):
        add(full, 5.0 + i * .55, 2.5, bell(f), .22)
    chord(full, 8.2)
    peak = max(abs(v) for v in full)
    save(full, 'update-12s.wav', peak)
    # the kit: each piece alone, at the same loudness as in the track (shared peak), so they mix the same way again
    b = track(12.0); pad(b, 12.0); save(b, 'pad-12s.wav', peak)
    b = track(.08); tick(b, 0, random.Random(7)); save(b, 'tick.wav', peak)
    b = track(2.7); ticks(b, 0, 2.55, random.Random(7)); save(b, 'ticks-2.6s.wav', peak)
    b = track(3.0); chime(b, 0); save(b, 'chime.wav', peak)
    for i, f in enumerate(NOTES, 1):
        b = track(2.5); add(b, 0, 2.5, bell(f), .22); save(b, f'note-{i}.wav', peak)
    b = track(3.8); chord(b, 0); save(b, 'chord.wav', peak)
    print('\n'.join(sorted(os.listdir(OUT))))
