"""Voice lock — sirf malik ki awaaz se ledger badal sakta hai.

Uses SpeechBrain's ECAPA-TDNN speaker embeddings (open source, CPU-friendly).
SpeechBrain is an OPTIONAL dependency: `pip install speechbrain torchaudio`.
Without it, the app still runs — voice endpoints report 'unavailable'.
"""
import logging
from pathlib import Path

from app.config import AUDIO_DIR, settings

log = logging.getLogger("bolkhata.voiceid")
_model = None


def _load():
    global _model
    if _model is not None:
        return _model
    try:
        import torch
        from speechbrain.inference.speaker import EncoderClassifier
    except ImportError:
        return None
    _model = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=str(AUDIO_DIR / "ecapa"),
        run_opts={"device": "cpu"},
    )
    return _model


def _embedding(wav_path: str | Path):
    import torch
    model = _load()
    if model is None:
        return None
    signal, fs = __import__("torchaudio").load(str(wav_path))
    if fs != 16000:
        signal = __import__("torchaudio").functional.resample(signal, fs, 16000)
    with torch.no_grad():
        emb = model.encode_batch(signal)
    return emb.squeeze()


def enroll(shopkeeper_id: int, wav_bytes: bytes) -> dict:
    """Save owner voice sample + embedding."""
    path = AUDIO_DIR / f"owner_{shopkeeper_id}_enroll.wav"
    path.write_bytes(wav_bytes)
    emb = _embedding(path)
    if emb is None:
        return {"ok": False, "reason": "speechbrain not installed — voice lock offline"}
    emb_path = AUDIO_DIR / f"owner_{shopkeeper_id}_emb.pt"
    import torch
    torch.save(emb, emb_path)
    with __import__("app.db", fromlist=["db"]).db() as conn:
        conn.execute("UPDATE shopkeeper SET voice_profile_path=? WHERE id=?",
                     (str(emb_path), shopkeeper_id))
    return {"ok": True}


def verify(shopkeeper_id: int, wav_bytes: bytes) -> dict:
    emb_path = AUDIO_DIR / f"owner_{shopkeeper_id}_emb.pt"
    if not emb_path.exists():
        return {"verified": False, "reason": "owner not enrolled"}
    tmp = AUDIO_DIR / f"owner_{shopkeeper_id}_check.wav"
    tmp.write_bytes(wav_bytes)
    emb = _embedding(tmp)
    if emb is None:
        return {"verified": False, "reason": "speechbrain not installed"}
    import torch
    ref = torch.load(emb_path)
    cos = torch.nn.functional.cosine_similarity(ref, emb, dim=0).item()
    return {"verified": cos >= settings.voice_lock_threshold,
            "similarity": round(cos, 3), "threshold": settings.voice_lock_threshold}
