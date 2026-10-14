// Voice engine — dual mode, both free today:
//   Mock Mode : browser SpeechRecognition + speechSynthesis (Chrome/Edge)
//   Gnani Mode: backend /ws/voice streams to Prisma; /api/tts returns Timbre audio
// The rest of the app only uses speak() and startListening() — mode is invisible.

export const speechSupported = () =>
  typeof window !== "undefined" &&
  ("webkitSpeechRecognition" in window || "SpeechRecognition" in window);

let rec = null;
let active = false;

export function startListening(onPartial, onFinal, lang = "hi-IN") {
  if (!speechSupported()) {
    onFinal && onFinal("", new Error("Is browser me speech recognition nahi hai — Chrome use karo"));
    return () => {};
  }
  const SR = window.webkitSpeechRecognition || window.SpeechRecognition;
  rec = new SR();
  rec.lang = lang;
  rec.continuous = false;
  rec.interimResults = true;
  active = true;

  rec.onresult = (e) => {
    let interim = "", final = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) final += t;
      else interim += t;
    }
    if (interim && onPartial) onPartial(interim);
    if (final && onFinal) onFinal(final.trim());
  };
  rec.onerror = (e) => {
    active = false;
    onFinal && onFinal("", new Error(e.error === "not-allowed" ? "Mic permission chahiye" : e.error));
  };
  rec.onend = () => { active = false; };
  try { rec.start(); } catch { /* already started */ }

  return () => { try { rec && rec.stop(); } catch {} };
}

export function stopListening() {
  try { rec && rec.stop(); } catch {}
  active = false;
}

export const isListening = () => active;

// ---------- TTS ----------
let cachedVoice = null;

function pickVoice() {
  if (cachedVoice) return cachedVoice;
  const vs = window.speechSynthesis?.getVoices?.() || [];
  cachedVoice =
    vs.find((v) => /hi-IN/i.test(v.lang)) ||
    vs.find((v) => /en-IN/i.test(v.lang)) ||
    vs.find((v) => /hi|in/i.test(v.lang)) ||
    vs[0] ||
    null;
  return cachedVoice;
}

export function speak(text, { pitch = 1, rate = 1, onEnd } = {}) {
  if (!("speechSynthesis" in window)) {
    onEnd && onEnd();
    return;
  }
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const v = pickVoice();
  if (v) u.voice = v;
  u.lang = v?.lang || "hi-IN";
  u.pitch = pitch;
  u.rate = rate;
  u.onend = () => onEnd && onEnd();
  u.onerror = () => onEnd && onEnd();
  window.speechSynthesis.speak(u);
}

export function stopSpeaking() {
  try { window.speechSynthesis.cancel(); } catch {}
}

// Warm the voice list (Chrome loads async)
if (typeof window !== "undefined" && "speechSynthesis" in window) {
  window.speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => { cachedVoice = null; pickVoice(); };
}

// ---------- recording helper (voice enroll) ----------
export async function recordClip(ms = 5000) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mr = new MediaRecorder(stream);
  const chunks = [];
  mr.ondataavailable = (e) => chunks.push(e.data);
  const done = new Promise((res) => (mr.onstop = res));
  mr.start();
  setTimeout(() => mr.stop(), ms);
  await done;
  stream.getTracks().forEach((t) => t.stop());
  return new Blob(chunks, { type: mr.mimeType || "audio/webm" });
}
