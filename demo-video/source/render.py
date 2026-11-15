"""Render stage.html into the demo video: one MP4 per scene, joined with -c copy.

    python3 render.py --stills 5,30,60,75,100,125,138   # check frames first
    python3 render.py                                     # full render
"""
import json
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"; OUT.mkdir(exist_ok=True)
FPS = 30
TL = json.loads((ROOT / "timeline.json").read_text())
SCENES, NARR = TL["scenes"], TL["narration"]

shots = {}
for s in json.loads((ROOT / "shots" / "shots.json").read_text()):
    shots.setdefault(s["name"], []).append(s["file"])

INIT = f"window.SHOTS={json.dumps(shots)};window.SCENES={json.dumps(SCENES)};window.NARR={json.dumps(NARR)};"
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS),
       "-g", str(FPS * 2), "-movflags", "+faststart"]


def open_page(p):
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox", "--force-color-profile=srgb"])
    pg = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    pg.add_init_script(INIT)
    pg.goto((ROOT / "stage.html").as_uri())
    n = pg.evaluate("window.preload()")
    pg.evaluate("document.fonts.ready")
    print("preloaded", n, "images")
    return b, pg


def stills(times):
    with sync_playwright() as p:
        b, pg = open_page(p)
        for t in times:
            pg.evaluate(f"window.render({t})")
            pg.screenshot(path=str(OUT / f"still-{t:06.2f}.jpg"), type="jpeg", quality=92)
        b.close()


def render_all(only=None):
    with sync_playwright() as p:
        b, pg = open_page(p)
        for i, (name, s, e) in enumerate(SCENES):
            if only and name not in only:
                continue
            final, tmp = OUT / f"{i:02d}-{name}.mp4", OUT / f"{i:02d}-{name}.part.mp4"
            n = round((e - s) * FPS)
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS),
                                   "-c:v", "mjpeg", "-i", "-", *ENC, str(tmp)], stdin=subprocess.PIPE)
            for f in range(n):
                pg.evaluate(f"window.render({s + f / FPS})")
                ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
            ff.stdin.close()
            if ff.wait() == 0:
                tmp.rename(final)
                print("scene", name, n, "frames")
            else:
                sys.exit(f"ffmpeg failed on {name}")
        b.close()
    parts = sorted(OUT.glob("[0-9][0-9]-*.mp4"))
    parts = [x for x in parts if ".part" not in x.name]
    (OUT / "concat.txt").write_text("".join(f"file '{x.name}'\n" for x in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(OUT / "concat.txt"),
                    "-c", "copy", str(OUT / "video-silent.mp4")], check=True)
    print("joined", len(parts), "scenes")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--stills":
        stills([float(x) for x in sys.argv[2].split(",")])
    elif len(sys.argv) > 2 and sys.argv[1] == "--only":
        render_all(set(sys.argv[2].split(",")))
    else:
        render_all()
