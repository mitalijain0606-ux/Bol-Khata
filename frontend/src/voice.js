// Voice engine — dual mode, automatic:
//   Gnani Mode : mic audio -> backend /api/stt -> Gnani PRISMA transcript
//                replies  -> backend /api/tts -> Gnani TIMBRE audio (Poorvi etc.)
//   Mock Mode  : browser SpeechRecognition + speechSynthesis (free fallback)
// The app only calls startListening()/recordUtterance() and speak().

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

// ---------------- STT (Gnani Prisma path) ----------------

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
      clearTimeout(null);
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

export async function transcribeViaPrisma(wavBlob, lang = "hi-IN") {
  const fd = new FormData();
  fd.append("file", wavBlob, "utterance.wav");
  const r = await fetch(`/api/stt?lang=${lang}`, { method: "POST", body: fd });
  if (!r.ok) throw new Error("STT fail: " + r.status);
  const d = await r.json();
  return d; // {transcript, provider}
}

// ---------------- TTS — Timbre first, browser fallback ----------------

let currentAudio = null;

export function stopSpeaking() {
  try { window.speechSynthesis.cancel(); } catch {}
  if (currentAudio) {
    try { currentAudio.pause(); } catch {}
    currentAudio = null;
  }
}

export function speak(text, { voice = "", pitch = 1, rate = 1, onEnd } = {}) {
  // 1) Gnani Timbre (backend proxies; returns audio/wav in Gnani mode)
  fetch(`/api/tts?text=${encodeURIComponent(text)}&voice=${encodeURIComponent(voice)}`)
    .then(async (r) => {
      if (r.status === 204 || !r.ok) throw new Error("no timbre");
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
    .catch(() => {
      // 2) Browser speechSynthesis (mock mode)
      if (!("speechSynthesis" in window)) { onEnd && onEnd(); return; }
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      const v = pickVoice();
      if (v) u.voice = v;
      u.lang = v?.lang || "hi-IN";
      u.pitch = pitch;
      u.rate = rate;
      let done = false;
      const finish = () => { if (!done) { done = true; onEnd && onEnd(); } };
      u.onend = finish;
      u.onerror = finish;
      window.speechSynthesis.speak(u);
      setTimeout(finish, 12000);
    });
}

function stopListeningIfRecording() { /* mic+speaker echo guard placeholder */ }

// Warm the browser voice list (Chrome loads async)
let cachedVoice = null;
function pickVoice() {
  if (cachedVoice) return cachedVoice;
  const vs = window.speechSynthesis?.getVoices?.() || [];
  cachedVoice =
    vs.find((v) => /hi-IN/i.test(v.lang)) ||
    vs.find((v) => /en-IN/i.test(v.lang)) ||
    vs.find((v) => /hi|in/i.test(v.lang)) ||
    vs[0] || null;
  return cachedVoice;
}
if (typeof window !== "undefined" && "speechSynthesis" in window) {
  window.speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => { cachedVoice = null; };
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
