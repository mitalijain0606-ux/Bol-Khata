"""Noise-Canceller test harness (free, offline).

cloud TTS se synthetic test sentences banao -> market/traffic noise mix karo ->
cloud STT aur ek baseline (browser/whisper) pe WER compare karo.
Output: demo/noise_report.json + console table.

Key-less machines pe ye sirf test-set generate karta hai; WER step needs keys.
"""
import asyncio
import json
import random
import struct
import wave
from pathlib import Path

from app.config import AUDIO_DIR, settings

SENTENCES = [
    "Sharma ji ko do hazaar paanch sau ka udhaar lagana",
    "Gupta ne paanch sau diye aaj",
    "kitna baki hai Verma ji ka",
    "Yadav ka hisaab clear kar do",
    "aaj ka total udhaar batao",
]
DEMO_DIR = Path(__file__).resolve().parent.parent.parent / "demo"
OUT = DEMO_DIR / "noise_testset"
OUT.mkdir(parents=True, exist_ok=True)

SAMPLE_RATE = 16000


def synth_tone_speech_placeholder(text: str, seconds: float = 2.0) -> bytes:
    """Offline placeholder 'speech' (tonal hum) — replaced by cloud TTS when
    keys are configured. Keeps the harness runnable at zero cost."""
    import math
    frames = bytearray()
    for i in range(int(SAMPLE_RATE * seconds)):
        v = int(6000 * math.sin(2 * math.pi * 180 * i / SAMPLE_RATE) *
                (0.6 + 0.4 * math.sin(2 * math.pi * 3 * i / SAMPLE_RATE)))
        frames += struct.pack("<h", v)
    return bytes(frames)


def make_noise(seconds: float, kind: str = "market") -> list[int]:
    random.seed(kind)
    amp = 9000 if kind == "market" else 6000
    samples = []
    prev = 0
    for _ in range(int(SAMPLE_RATE * seconds)):
        prev = int(0.97 * prev + random.uniform(-amp, amp))  # brown-ish noise
        samples.append(max(-32768, min(32767, prev)))
    return samples


def mix(speech: bytes, noise: list[int], snr_db: float) -> bytes:
    n = len(noise)
    sp = list(struct.unpack(f"<{len(speech)//2}h", speech))
    sp += [0] * (n - len(sp)) if len(sp) < n else sp[:n]
    import math
    sp_rms = math.sqrt(sum(s * s for s in sp) / n) or 1
    nz_rms = math.sqrt(sum(v * v for v in noise) / n) or 1
    scale = sp_rms / (nz_rms * (10 ** (snr_db / 20)))
    out = [max(-32768, min(32767, int(s + v * scale))) for s, v in zip(sp, noise)]
    return struct.pack(f"<{len(out)}h", *out)


def write_wav(path: Path, pcm: bytes):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)


async def main():
    snrs = [0, 5, 10]
    report = {"generated": [], "wer": {}}

    # 1) generate test set (cloud TTS when configured, placeholder otherwise)
    for s_i, sent in enumerate(SENTENCES):
        if settings.tts_configured:
            from app.speech.tts import synthesize
            speech = await synthesize(sent)
            path = OUT / f"utt_{s_i}_clean.wav"
            path.write_bytes(speech)
        else:
            speech = synth_tone_speech_placeholder(sent)
            write_wav(OUT / f"utt_{s_i}_clean.wav", speech)
        noise = make_noise(2.5, random.choice(["market", "traffic"]))
        for snr in snrs:
            write_wav(OUT / f"utt_{s_i}_{snr}db.wav", mix(speech, noise, snr))
        report["generated"].append(sent)

    # 2) WER eval (needs STT key; skip otherwise)
    if settings.stt_configured:
        from app.speech.stt import transcribe_clip
        def wer(ref: str, hyp: str):
            r, h = ref.lower().split(), hyp.lower().split()
            import difflib
            sm = difflib.SequenceMatcher(None, r, h)
            return 1 - sm.ratio()

        for snr in [None, *snrs]:
            scores = []
            for s_i, sent in enumerate(SENTENCES):
                f = OUT / (f"utt_{s_i}_clean.wav" if snr is None else f"utt_{s_i}_{snr}db.wav")
                hyp = await transcribe_clip(f.read_bytes())
                scores.append(wer(sent, hyp))
            label = "clean" if snr is None else f"{snr}dB"
            report["wer"][label] = round(sum(scores) / len(scores), 3)
        print(json.dumps(report["wer"], indent=2))

    (DEMO_DIR / "noise_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Test set ready at {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
