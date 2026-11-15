// Voice engine — dual mode, automatic:
//   cloud mode : mic audio -> backend /api/stt -> cloud STT transcript
//                replies  -> backend /api/tts -> cloud TTS audio
//   Mock Mode  : browser SpeechRecognition + speechSynthesis (free fallback)
// The app only calls startListening()/recordUtterance() and speak().

import { authHeaders } from "./api.js";

export const micSupported = () =>
  typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia &&
  typeof MediaRecorder !== "undefined";

export const speechSupported = () =>
  typeof window !== "undefined" &&
  ("webkitSpeechRecognition" in window || "SpeechRecognition" in window);

// ---------------- STT (browser path — mock mode) ----------------

let rec = null;
let active = false;

export function startListening(onPartial, onFinal, lang = "hi-IN") {
  if (!speechSupported()) {
    onFinal && onFinal("", new Error("Is browser me speech recognition nahi hai — Chrome use karo"));
    return () => {};
  }
  const SR = window.webkitSpeechRecognition || window.SpeechRecognition;
  try { rec && rec.abort(); } catch {}
  const r = new SR();
  rec = r;
  r.lang = lang;
  r.continuous = false;
  r.interimResults = true;
  active = true;

  // onFinal fires exactly once per listen — with the text, or "" when the
  // recogniser stops on silence / an error (the mic button used to stay stuck
  // on "listening" forever in that case).
  let finalText = "", lastInterim = "", delivered = false;
  const deliver = (text, err) => {
    if (delivered) return;
    delivered = true;
    active = false;
    onFinal && onFinal(text, err);
  };

  r.onresult = (e) => {
    let interim = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) finalText += t;
      else interim += t;
    }
    if (interim) { lastInterim = interim; onPartial && onPartial(interim); }
  };
  r.onerror = (e) => {
    if (e.error === "no-speech" || e.error === "aborted") return; // onend follows
    const msg = e.error === "not-allowed" || e.error === "service-not-allowed"
      ? "Mic ki permission chahiye — browser me mic allow kijiye"
      : e.error === "network" ? "Speech service tak nahi pahunch paye — internet check kijiye"
      : e.error === "audio-capture" ? "Mic nahi mila — mic jod kar dobara koshish kijiye"
      : "Mic error: " + e.error;
    deliver("", new Error(msg));
  };
  r.onend = () => deliver((finalText || lastInterim).trim());
  try { r.start(); } catch (e) { deliver("", e); }

  return () => { try { r.stop(); } catch {} };
}

export function stopListening() {
  try { rec && rec.stop(); } catch {}
  active = false;
}

export const isListening = () => active;

// ---------------- STT (cloud STT path) ----------------

// Tap-to-talk: startRecording() -> stopper.stop() -> 16 kHz mono WAV blob
export async function startRecording(onLevel) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mr = new MediaRecorder(stream);
  const chunks = [];
  mr.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  mr.start(250);

  // optional live level for UI pulse
  let ctx, raf;
  try {
    ctx = new AudioContext();
    const src = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    src.connect(analyser);
    const buf = new Uint8Array(analyser.frequencyBinCount);
    const tick = () => {
      analyser.getByteTimeDomainData(buf);
      let peak = 0;
      for (const v of buf) peak = Math.max(peak, Math.abs(v - 128));
      onLevel && onLevel(peak / 128);
      raf = requestAnimationFrame(tick);
    };
    tick();
  } catch { /* level meter optional */ }

  let stopResolve;
  const stopped = new Promise((res) => { stopResolve = res; });
  mr.onstop = () => stopResolve();

  return {
    stop: async () => {
      if (mr.state !== "inactive") mr.stop();
      await stopped;
      stream.getTracks().forEach((t) => t.stop());
      if (raf) cancelAnimationFrame(raf);
      if (ctx) ctx.close().catch(() => {});
      const blob = new Blob(chunks, { type: mr.mimeType || "audio/webm" });
      return await blobToWav16k(blob);
    },
  };
}

async function blobToWav16k(blob) {
  const AC = window.AudioContext || window.webkitAudioContext;
  const ctx = new AC({ sampleRate: 16000 });
  const decoded = await ctx.decodeAudioData(await blob.arrayBuffer());
  const ch = decoded.getChannelData(0); // mono
  const pcm = new Int16Array(ch.length);
  for (let i = 0; i < ch.length; i++) {
    const s = Math.max(-1, Math.min(1, ch[i]));
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  await ctx.close();

  // minimal 44-byte WAV header
  const header = new ArrayBuffer(44);
  const v = new DataView(header);
  const str = (off, s) => { for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i)); };
  str(0, "RIFF"); v.setUint32(4, 36 + pcm.byteLength, true); str(8, "WAVE");
  str(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true);
  v.setUint16(22, 1, true); v.setUint32(24, 16000, true);
  v.setUint32(28, 32000, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true);
  str(36, "data"); v.setUint32(40, pcm.byteLength, true);
  return new Blob([header, pcm.buffer], { type: "audio/wav" });
}

export async function transcribeViaCloud(wavBlob, lang = "hi-IN") {
  const fd = new FormData();
  fd.append("file", wavBlob, "utterance.wav");
  const r = await fetch(`/api/stt?lang=${lang}`, { method: "POST", body: fd, headers: authHeaders() });
  if (!r.ok) throw new Error("STT fail: " + r.status);
  const d = await r.json();
  return d; // {transcript, provider}
}

// ---------------- TTS — cloud first, browser fallback ----------------

let currentAudio = null;

export function stopSpeaking() {
  speakSeq++;
  try { window.speechSynthesis.cancel(); } catch {}
  if (currentAudio) {
    try { currentAudio.pause(); } catch {}
    currentAudio = null;
  }
}

let cloudTts = null; // null = not checked yet, false = server has no TTS key (mock mode)
let speakSeq = 0;

export function speak(text, { voice = "", lang = "hi-IN", pitch = 1, rate = 1, onEnd } = {}) {
  if (!text) { onEnd && onEnd(); return; }
  const mySeq = ++speakSeq;                 // a newer speak()/stopSpeaking() cancels this one
  const browserTts = () => {
      if (mySeq !== speakSeq) { onEnd && onEnd(); return; }
      // 2) Browser speechSynthesis (mock mode)
      if (!("speechSynthesis" in window)) { onEnd && onEnd(); return; }
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      const v = pickVoice(lang);
      if (v) u.voice = v;
      u.lang = v?.lang || lang || "hi-IN";
      u.pitch = pitch;
      u.rate = rate;
      let done = false;
      const finish = () => { if (!done) { done = true; onEnd && onEnd(); } };
      u.onend = finish;
      u.onerror = finish;
      window.speechSynthesis.speak(u);
      // safety net sized to the text, in case the browser never fires onend
      setTimeout(finish, Math.min(60000, 4000 + text.length * 110));
  };
  if (cloudTts === false) { browserTts(); return; }

  // 1) cloud TTS (backend proxies; returns audio/wav when configured)
  fetch(`/api/tts?text=${encodeURIComponent(text)}&voice=${encodeURIComponent(voice)}&lang=${lang}`,
        { headers: authHeaders() })
    .then(async (r) => {
      if (r.status === 204) cloudTts = false;      // no key on the server: stop asking
      if (r.status === 204 || !r.ok) throw new Error("no timbre");
      if (mySeq !== speakSeq) { onEnd && onEnd(); return; }
      const blob = await r.blob();
      if (blob.size < 100) throw new Error("empty audio");
      stopListeningIfRecording();
      const audio = new Audio(URL.createObjectURL(blob));
      currentAudio = audio;
      let done = false;
      const finish = () => { if (!done) { done = true; currentAudio = null; onEnd && onEnd(); } };
      audio.onended = finish;
      audio.onerror = finish;
      await audio.play().catch(finish);
      setTimeout(finish, 30000);
    })
    .catch(browserTts);
}

function stopListeningIfRecording() { /* mic+speaker echo guard placeholder */ }

// Warm the browser voice list (Chrome loads async)
// Voice for the reply language (Marathi/Tamil replies are in native script, so a
// Hindi voice cannot read Tamil); falls back to Hindi, then Indian English.
let voiceCache = {};
function pickVoice(lang = "hi-IN") {
  if (lang in voiceCache) return voiceCache[lang];
  const vs = window.speechSynthesis?.getVoices?.() || [];
  if (!vs.length) return null;               // list not loaded yet — don't cache
  const norm = (l) => (l || "").replace("_", "-").toLowerCase();
  const short = lang.slice(0, 2).toLowerCase();
  voiceCache[lang] =
    vs.find((v) => norm(v.lang) === lang.toLowerCase()) ||
    vs.find((v) => norm(v.lang).startsWith(short)) ||
    vs.find((v) => norm(v.lang) === "hi-in") ||
    vs.find((v) => norm(v.lang).startsWith("hi")) ||
    vs.find((v) => norm(v.lang) === "en-in") ||
    vs[0] || null;
  return voiceCache[lang];
}
if (typeof window !== "undefined" && "speechSynthesis" in window) {
  window.speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => { voiceCache = {}; };
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
  // the backend's speaker model reads WAV, not the browser's webm/opus
  return await blobToWav16k(new Blob(chunks, { type: mr.mimeType || "audio/webm" }));
}
