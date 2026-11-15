"""Film the real Bol-Khata app (real backend, real data) as JPEG stills at 2x.
Only the microphone is stubbed: a fake SpeechRecognition returns a fixed
transcript, because a headless browser has no microphone."""
import json, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path("/home/claude/work/video/shots"); OUT.mkdir(parents=True, exist_ok=True)
F = Path("/home/claude/work/scratch/fonts")
FONT_FILES = {
    "dev400": F / "fontsource-noto-sans-devanagari-5.2.10/files/noto-sans-devanagari-devanagari-400-normal.woff2",
    "dev600": F / "fontsource-noto-sans-devanagari-5.2.10/files/noto-sans-devanagari-devanagari-600-normal.woff2",
    "ta400": F / "fontsource-noto-sans-tamil-5.3.0/files/noto-sans-tamil-tamil-400-normal.woff2",
    "ta600": F / "fontsource-noto-sans-tamil-5.3.0/files/noto-sans-tamil-tamil-600-normal.woff2",
}
INIT = r"""
(() => {
  // Noto for Devanagari/Tamil glyphs only (the Linux recorder lacks them)
  const css = `
  @font-face{font-family:"Avenir Next";src:url(/__vf/dev400) format("woff2");font-weight:100 500;unicode-range:U+0900-097F,U+1CD0-1CF9,U+200C-200D,U+20A8,U+A830-A839,U+A8E0-A8FF;}
  @font-face{font-family:"Avenir Next";src:url(/__vf/dev600) format("woff2");font-weight:501 900;unicode-range:U+0900-097F,U+1CD0-1CF9,U+200C-200D,U+20A8,U+A830-A839,U+A8E0-A8FF;}
  @font-face{font-family:"Avenir Next";src:url(/__vf/ta400) format("woff2");font-weight:100 500;unicode-range:U+0B80-0BFF;}
  @font-face{font-family:"Avenir Next";src:url(/__vf/ta600) format("woff2");font-weight:501 900;unicode-range:U+0B80-0BFF;}
  @font-face{font-family:"Avenir Next";src:local("Inter");font-weight:100 500;unicode-range:U+0000-024F,U+20B9,U+2014,U+2018-201D,U+2022,U+2192,U+2212;}
  @font-face{font-family:"Avenir Next";src:local("Inter SemiBold");font-weight:501 650;unicode-range:U+0000-024F,U+20B9,U+2014,U+2018-201D,U+2022,U+2192,U+2212;}
  @font-face{font-family:"Avenir Next";src:local("Inter Bold"),local("Inter ExtraBold");font-weight:651 900;unicode-range:U+0000-024F,U+20B9,U+2014,U+2018-201D,U+2022,U+2192,U+2212;}`;
  const add = () => { const s = document.createElement("style"); s.textContent = css; document.head.appendChild(s); };
  if (document.head) add(); else document.addEventListener("DOMContentLoaded", add);

  // speech output: no audio device here; resolve like a short utterance
  class U { constructor(t){ this.text=t; } }
  window.SpeechSynthesisUtterance = U;
  Object.defineProperty(window, "speechSynthesis", { value: {
    getVoices: () => [{lang:"hi-IN", name:"hi"}],
    cancel(){}, speak(u){ setTimeout(() => u.onend && u.onend(), 250); },
    set onvoiceschanged(v){} } });

  // microphone stub: plays back a queued transcript word by word
  window.__srQueue = [];
  window.webkitSpeechRecognition = class {
    start() {
      const text = window.__srQueue.shift() || "";
      const words = text.split(" ");
      let i = 0;
      const tick = () => {
        i++;
        const partial = words.slice(0, i).join(" ");
        const done = i >= words.length;
        this.onresult && this.onresult({ resultIndex: 0,
          results: [Object.assign([{ transcript: partial }], { isFinal: done })] });
        if (!done) setTimeout(tick, 420); else setTimeout(() => this.onend && this.onend(), 500);
      };
      setTimeout(tick, 900);
    }
    stop() {} abort() {}
  };
})();
"""

shots = []
def shot(pg, name, note=""):
    p = OUT / f"{len(shots):03d}-{name}.jpg"
    pg.screenshot(path=str(p), type="jpeg", quality=92)
    shots.append({"file": p.name, "name": name, "note": note})

with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = b.new_context(viewport={"width": 430, "height": 932}, device_scale_factor=2,
                        service_workers="block", locale="en-IN")
    ctx.add_init_script(INIT)
    ctx.route("**/__vf/*", lambda r: r.fulfill(path=str(FONT_FILES[r.request.url.rsplit("/", 1)[1]]),
                                               content_type="font/woff2"))
    pg = ctx.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto("http://localhost:8000/"); pg.wait_for_selector(".auth-card"); pg.wait_for_timeout(800)
    shot(pg, "login-empty")
    pg.fill("input[inputmode=numeric]", "9876543210"); pg.fill("input[type=password]", "demo1234")
    shot(pg, "login-filled")
    pg.click("form button"); pg.wait_for_selector(".mic-orb"); pg.wait_for_timeout(900)
    shot(pg, "home")

    def scroll_log():
        pg.evaluate("""() => { const b=[...document.querySelectorAll('.bubble')].pop();
            if (b) b.scrollIntoView({block:'center'}); }""")
        pg.wait_for_timeout(250)

    def typed(cmd, tag):
        pg.evaluate("window.scrollTo(0,0)")
        box = pg.locator(".say-row input")
        box.click()
        step = max(1, len(cmd) // 9)
        for i in range(step, len(cmd) + step, step):
            box.fill(cmd[:i]); pg.wait_for_timeout(40); shot(pg, f"{tag}-type")
        pg.click(".say-row button"); pg.wait_for_timeout(900)
        scroll_log(); shot(pg, f"{tag}-reply")

    # 1) credit entry, typed
    typed("Ramesh ne 500 rupaye udhaar liye", "credit")
    # 2) customer khata
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.wait_for_timeout(300)
    shot(pg, "feed")
    pg.locator(".entry.tap", has_text="Ramesh").first.click()
    pg.wait_for_selector(".sheet .entry"); pg.wait_for_timeout(500)
    shot(pg, "sheet-ramesh")
    pg.locator(".sheet").evaluate("e => e.scrollTo(0, 260)"); pg.wait_for_timeout(250)
    shot(pg, "sheet-ramesh-entries")
    pg.click(".sheet-close"); pg.wait_for_timeout(300)
    # 3) payment + new customer
    typed("Ramesh ji ne 300 rupaye wapas kar diye", "payment")
    typed("Kavita ji ko 250 ka udhaar likh do", "newcust")

    # 4) HERO: voice
    pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(300)
    pg.evaluate("window.__srQueue.push('Suresh Gupta ne do hazaar paanch sau rupaye diye')")
    pg.click(".mic-orb")
    t0 = time.time()
    for i in range(14):
        shot(pg, "voice-listen"); pg.wait_for_timeout(330)
        if not pg.locator(".mic-orb.listening").count() and i > 3:
            break
    pg.wait_for_timeout(700); scroll_log(); shot(pg, "voice-reply")

    # 5) "udhaar du?" verdict
    typed("Chauhan ji ko 2000 udhaar du kya?", "lend")
    typed("Sharma ji ko 1000 udhaar du kya?", "lend2")

    # 6) dashboard
    pg.click("nav button:has-text('Hisaab')"); pg.wait_for_selector(".score-row"); pg.wait_for_timeout(700)
    pg.evaluate("window.scrollTo(0,0)"); shot(pg, "dash-top")
    pg.locator(".score-row").first.scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0,-120)")
    pg.wait_for_timeout(300); shot(pg, "dash-scores")
    pg.locator(".score-row", has_text="Chauhan").click(); pg.wait_for_timeout(400)
    pg.locator(".breakdown").first.scroll_into_view_if_needed(); pg.evaluate("window.scrollBy(0,-160)")
    pg.wait_for_timeout(250); shot(pg, "dash-breakdown")

    # 7) collections call (simulated customer)
    pg.click("nav button:has-text('Calls')"); pg.wait_for_selector(".score-row"); pg.wait_for_timeout(500)
    pg.evaluate("window.scrollTo(0,0)"); shot(pg, "calls-list")
    pg.locator(".score-row", has_text="Naresh Mehta").click()
    for i in range(40):
        pg.wait_for_timeout(450)
        if pg.locator(".result-card").count():
            break
        pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        shot(pg, "call-live")
    pg.wait_for_selector(".result-card"); pg.wait_for_timeout(400)
    pg.evaluate("window.scrollTo(0,0)"); shot(pg, "call-result")
    json.dump(shots, open(OUT / "shots.json", "w"), indent=1)
    print(len(shots), "shots; page errors:", errors)
    b.close()
