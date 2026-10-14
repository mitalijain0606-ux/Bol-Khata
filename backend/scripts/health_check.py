"""Run once after cloning: teeno Gnani APIs pe 1-1 test call -> 'all green'.

  python -m scripts.health_check
"""
import asyncio
import io
import wave


def tiny_wav(seconds: float = 0.6) -> bytes:
    """Valid silent 16kHz mono WAV — enough for a real STT ping."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * int(16000 * seconds))
    return buf.getvalue()


async def main():
    from app.config import settings
    from app.gnani import stt, tts
    from app.gnani.evon import chat as evon_chat

    print(f"Mode: {settings.mode.upper()}")
    print(f"STT configured : {settings.stt_configured}")
    print(f"TTS configured : {settings.tts_configured}")
    print(f"Evon configured: {settings.evon_configured}")

    if settings.stt_configured:
        try:
            text = await stt.transcribe_clip(tiny_wav())
            print(f"STT ping OK -> {text[:80]!r}")
        except Exception as e:
            print(f"STT ping FAILED -> {e}")
    if settings.tts_configured:
        try:
            audio = await tts.synthesize("Namaste, ye Bol-Khata ki test hai.")
            print(f"TTS ping OK -> {len(audio)} bytes (wav)")
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
