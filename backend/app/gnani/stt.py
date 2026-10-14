"""Gnani Prisma v2.5 STT wrapper.

Real-mode HTTP surface per docs.gnani.ai:
  - REST  : POST {GNANI_API_BASE}{GNANI_STT_REST_PATH}   (clips <= 60s)
  - WS    : {GNANI_API_BASE}{GNANI_STT_WS_PATH}          (realtime streaming)
Auth header: X-API-Key-ID.

NOTE: The endpoint paths are env-configurable because the exact path must be
confirmed against the quickstart in docs.gnani.ai once API access is live.
Until GNANI_API_KEY_ID is set, callers use Mock Mode instead.
"""
import json

import httpx
import websockets

from app.config import settings


class ProviderNotConfigured(Exception):
    pass


def _headers() -> dict:
    return {"X-API-Key-ID": settings.gnani_api_key}


async def transcribe_clip(audio_bytes: bytes, lang: str = "", fmt: str = "wav") -> str:
    """One-shot STT for short clips. Returns transcript text."""
    if not settings.stt_configured:
        raise ProviderNotConfigured("Gnani key missing — frontend uses browser STT in Mock Mode")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            settings.gnani_base + settings.stt_rest_path,
            headers=_headers(),
            files={"audio": (f"clip.{fmt}", audio_bytes)},
            data={"language": lang or settings.stt_lang},
        )
        resp.raise_for_status()
        data = resp.json()
    # Response shape to be confirmed against quickstart; handle common variants.
    for key in ("transcript", "text", "display", "transcription"):
        if isinstance(data, dict) and data.get(key):
            return str(data[key])
    if isinstance(data, dict) and isinstance(data.get("alternatives"), list) and data["alternatives"]:
        return str(data["alternatives"][0].get("transcript", ""))
    return json.dumps(data)[:400]
