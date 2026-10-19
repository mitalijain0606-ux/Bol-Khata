"""Cloud STT wrapper (REST + realtime WebSocket).

REST : POST {base}/stt/v3          multipart(audio_file, language_code) -> {transcript}
WS   : wss://{base}/stt/v3/stream  headers x-api-key-id + lang_code,
                                   binary PCM 16-bit mono 8/16kHz (~1024B frames)
"""
import json

import httpx
import websockets

from app.config import settings


class ProviderNotConfigured(Exception):
    pass


def _headers() -> dict:
    return {"X-API-Key-ID": settings.gnani_api_key}


async def transcribe_clip(audio_bytes: bytes, lang: str = "") -> str:
    """One-shot STT for clips <= 60s. Returns transcript text."""
    if not settings.stt_configured:
        raise ProviderNotConfigured("Speech API key missing — frontend uses browser STT in Mock Mode")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            settings.speech_base + settings.stt_rest_path,
            headers=_headers(),
            files={"audio_file": ("clip.wav", audio_bytes, "audio/wav")},
            data={"language_code": lang or settings.stt_lang},
        )
        resp.raise_for_status()
        data = resp.json()
    if isinstance(data, dict) and data.get("transcript"):
        return str(data["transcript"])
    return json.dumps(data)[:400]


async def open_stream(lang: str = ""):
    """Open the realtime STT WebSocket (caller sends PCM frames)."""
    url = settings.speech_base.replace("https", "wss").replace("http", "ws") + settings.stt_ws_path
    return await websockets.connect(
        url,
        extra_headers={
            "x-api-key-id": settings.gnani_api_key,
            "lang_code": lang or settings.stt_lang,
        },
    )
