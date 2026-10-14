"""Gnani Timbre v2.5 TTS wrapper.

Real-mode surface per docs.gnani.ai:
  - REST : POST {GNANI_API_BASE}{GNANI_TTS_REST_PATH}   -> audio bytes
  - SSE  : streaming
  - WS   : lowest-latency realtime
Supports 10+ Indic languages, SSML, correct lakh/crore numerals.
Voice IDs come from the Timbre voice catalog (env-configured).
"""
import httpx

from app.config import settings
from app.gnani.stt import ProviderNotConfigured


async def synthesize(text: str, voice_id: str = "", lang: str = "hi-IN") -> bytes:
    """Return audio bytes (content-type preserved by caller)."""
    if not settings.tts_configured:
        raise ProviderNotConfigured("Gnani key missing — frontend uses browser TTS in Mock Mode")
    payload = {
        "text": text,
        "voice_id": voice_id or settings.tts_voice_agent,
        "language": lang,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            settings.gnani_base + settings.tts_rest_path,
            headers={"X-API-Key-ID": settings.gnani_api_key},
            json=payload,
        )
        resp.raise_for_status()
        return resp.content
