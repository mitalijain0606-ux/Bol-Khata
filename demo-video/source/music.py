"""Generate an original, royalty-free ambient bed (no samples, no third-party music).
Soft electric-piano chords + a warm pad, I-vi-IV-V in C, 72 bpm, quiet."""
import sys
import wave

import numpy as np

SR = 48000
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 143.0
OUT = sys.argv[1] if len(sys.argv) > 1 else "music.wav"
t = np.arange(int(SR * DUR)) / SR

def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

CHORDS = [[48, 55, 60, 64, 67], [45, 52, 57, 60, 64], [41, 48, 53, 57, 60], [43, 50, 55, 59, 62]]   # C Am F G
BAR = 60 / 72 * 4                       # 3.33 s per chord
mix = np.zeros_like(t)

# pad: slow-breathing sines with detune, crossfaded between chords
for i in range(int(DUR / BAR) + 2):
    start = i * BAR
    notes = CHORDS[i % 4]
    env = np.clip((t - start + 0.9) / 0.9, 0, 1) * np.clip((start + BAR + 0.9 - t) / 0.9, 0, 1)
    env = np.sin(env * np.pi / 2) ** 2
    if not env.any():
        continue
    for m in notes:
        for det in (-0.06, 0.06):
            mix += 0.030 * env * np.sin(2 * np.pi * hz(m + det) * t)

# soft piano-like plucks: arpeggio, 8th notes, decaying
step = BAR / 8
rng = np.random.default_rng(7)
for k in range(int(DUR / step)):
    st = k * step
    notes = CHORDS[int(st // BAR) % 4]
    m = notes[[2, 3, 4, 3, 2, 3, 4, 1][k % 8]] + 12
    n0 = int(st * SR); n1 = min(len(t), n0 + int(SR * 1.6))
    tt = t[n0:n1] - st
    vel = 0.022 * (0.85 + 0.3 * rng.random())
    tone = np.sin(2 * np.pi * hz(m) * tt) + 0.25 * np.sin(2 * np.pi * hz(m) * 2 * tt) * np.exp(-tt * 6)
    mix[n0:n1] += vel * tone * np.exp(-tt * 2.6) * np.clip(tt / 0.006, 0, 1)

# gentle low end
mix += 0.035 * np.sin(2 * np.pi * hz(36) * t) * (0.6 + 0.4 * np.sin(2 * np.pi * t / BAR))

# simple stereo room: two short delays
L = mix.copy(); R = mix.copy()
for d, g in ((0.087, .35), (0.141, .25), (0.233, .18)):
    n = int(d * SR)
    L[n:] += g * mix[:-n]; R[n + 97:] += g * mix[:-(n + 97)]

fade = np.clip(t / 2.5, 0, 1) * np.clip((DUR - t) / 4.0, 0, 1)
st = np.stack([L * fade, R * fade], 1)
st *= 10 ** (-20 / 20) / np.abs(st).max()          # peak -20 dBFS: a bed, not a song
with wave.open(OUT, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype("<i2").tobytes())
print("wrote", OUT, DUR, "s")
