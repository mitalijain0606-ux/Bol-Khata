"""Add a Gnani Timbre voiceover to the demo video — run this on your own machine,
where backend/.env holds your speech key. The key is read by the backend's own
settings and is never printed.

    cd backend
    .venv/bin/pip install imageio-ffmpeg        # once; skip if ffmpeg is installed
    .venv/bin/python ../demo-video/add_narration.py

Reads  demo-video/final-bol-khata-demo.mp4 (video + music) and narration.json
Writes demo-video/final-bol-khata-demo-narrated.mp4
       demo-video/narration/NN.wav   (one Timbre clip per line, for re-use)

Options: --voice Poorvi   --lang hi-IN   --music 1.0 (music level; ducked under the voice)
"""
import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parent / "backend"
sys.path.insert(0, str(BACKEND))


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg not found. Run:  .venv/bin/pip install imageio-ffmpeg   (or: brew install ffmpeg)")


def wav_seconds(p: Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


async def synth_all(lines, voice, lang, outdir):
    from app.config import settings
    from app.speech.tts import synthesize
    if not settings.tts_configured:
        sys.exit("backend/.env has no SPEECH_API_KEY — add it first (python -m scripts.health_check should say TTS OK).")
    outdir.mkdir(exist_ok=True)
    raws = []
    for i, line in enumerate(lines):
        text = line[3] if len(line) > 3 else line[2]      # spoken text, if it differs from the caption
        raw = outdir / f"{i:02d}.raw.wav"
        if not raw.exists():
            raw.write_bytes(await synthesize(text, voice=voice, lang=lang))
            print(f"  voiced line {i + 1}/{len(lines)}")
        raws.append(raw)
    return raws


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="")          # empty = TTS_VOICE_AGENT from .env (Poorvi)
    ap.add_argument("--lang", default="hi-IN")
    ap.add_argument("--music", type=float, default=1.0)
    a = ap.parse_args()

    ff = ffmpeg_exe()
    src = HERE / "final-bol-khata-demo.mp4"
    if not src.exists():
        sys.exit(f"missing {src}")
    lines = json.loads((HERE / "narration.json").read_text())["narration"]
    outdir = HERE / "narration"
    raws = asyncio.run(synth_all(lines, a.voice, a.lang, outdir))

    clips = []
    for i, (line, raw) in enumerate(zip(lines, raws)):
        start, end = line[0], line[1]
        norm = outdir / f"{i:02d}.wav"
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(raw), "-ar", "48000", "-ac", "2", str(norm)], check=True)
        dur, slot = wav_seconds(norm), end - start
        tempo = 1.0
        if dur > slot:                                   # speed up a little to fit its scene
            tempo = min(dur / slot, 1.25)
        elif dur < slot * 0.85:                          # or slow down a touch to fill it
            tempo = max(dur / (slot * 0.95), 0.9)
        if tempo != 1.0:
            fitted = outdir / f"{i:02d}.fit.wav"
            subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(norm), "-filter:a", f"atempo={tempo:.3f}",
                            str(fitted)], check=True)
            print(f"  line {i + 1}: {dur:.1f}s in a {slot:.1f}s slot -> tempo x{tempo:.2f}"
                  + ("" if dur / tempo <= slot + 0.3 else "  (still a little long; it runs into the pause after it)"))
            norm = fitted
        clips.append((start, norm))

    cmd = [ff, "-y", "-loglevel", "error", "-i", str(src)]
    for _, c in clips:
        cmd += ["-i", str(c)]
    parts = [f"[{k + 1}:a]adelay={int(s * 1000)}|{int(s * 1000)}[v{k}]" for k, (s, _) in enumerate(clips)]
    n = len(clips)
    flt = ";".join(parts) + ";" + "".join(f"[v{k}]" for k in range(n)) + \
        f"amix=inputs={n}:normalize=0,alimiter=limit=0.89,apad[voice];[voice]asplit[vo][sc];" \
        f"[0:a]volume={a.music}[mu];[mu][sc]sidechaincompress=threshold=0.03:ratio=6:attack=25:release=450[duck];" \
        "[duck][vo]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89[aout]"
    out = HERE / "final-bol-khata-demo-narrated.mp4"
    tmp = HERE / "final-bol-khata-demo-narrated.part.mp4"
    cmd += ["-filter_complex", flt, "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart", str(tmp)]
    subprocess.run(cmd, check=True)
    tmp.rename(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
