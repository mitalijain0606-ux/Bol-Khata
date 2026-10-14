"""Run once after cloning: teeno Gnani APIs pe 1-1 test call -> 'all green'.

  python -m scripts.health_check
"""
import asyncio

from app.config import settings
from app.gnani import stt, tts
from app.gnani.evon import chat as evon_chat


async def main():
    print(f"Mode: {settings.mode.upper()}")
    print(f"STT configured : {settings.stt_configured}")
    print(f"TTS configured : {settings.tts_configured}")
    print(f"Evon configured: {settings.evon_configured}")

    if settings.stt_configured:
        silence = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
        try:
            text = await stt.transcribe_clip(silence)
            print(f"STT ping OK -> {text[:80]}")
        except Exception as e:
            print(f"STT ping FAILED -> {e}")
    if settings.tts_configured:
        try:
            audio = await tts.synthesize("Namaste, ye Bol-Khata ki test hai.")
            print(f"TTS ping OK -> {len(audio)} bytes")
        except Exception as e:
            print(f"TTS ping FAILED -> {e}")
    if settings.evon_configured:
        try:
            r = await evon_chat([{"role": "user", "content": "Ek line me apna naam batao."}])
            print(f"Evon ping OK -> {r['choices'][0]['message'].get('content', '')[:80]}")
        except Exception as e:
            print(f"Evon ping FAILED -> {e}")

    if settings.mode == "mock":
        print("\nMock Mode active — app poora chalega (browser speech + rule brain).")
        print("Gnani pe shift hone ke liye: .env me keys bharo (see .env.example).")


if __name__ == "__main__":
    asyncio.run(main())
