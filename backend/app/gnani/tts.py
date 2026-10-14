"""Gnani Timbre v2.5 TTS wrapper — exact API per docs.gnani.ai/api/TTS.

REST : POST {base}/api/v1/tts/inference
       {text, model: timbre-v2.5, voice: <name>, language, speed, audio_config}
       -> raw audio bytes (wav).
Voice catalog (v2.5, 42 voices): Poorvi = Hinglish, Deepak/Nalini = Hindi,
Kaveri = English. v3.0 voices speak all 10 languages.
"""
import httpx

from app.config import settings
from app.gnani.stt import ProviderNotConfigured


async def synthesize(text: str, voice: str = "", lang: str = "hi-IN") -> bytes:
    """Return audio bytes (wav)."""
    if not settings.tts_configured:
        raise ProviderNotConfigured("Gnani key missing — frontend uses browser TTS in Mock Mode")
    payload = {
        "text": text,
        "model": settings.tts_model,
        "voice": voice or settings.tts_voice_agent,
        "language": lang,
        "speed": 1.0,
        "audio_config": {
            "sample_rate": 16000,
            "num_channels": 1,
            "sample_width": 2,
            "encoding": "linear_pcm",
            "container": "wav",
        },
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            settings.gnani_base + settings.tts_rest_path,
            headers={"X-API-Key-ID": settings.gnani_api_key},
            json=payload,
        )
        resp.raise_for_status()
        return resp.content
