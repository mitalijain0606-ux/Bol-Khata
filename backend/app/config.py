"""Central configuration. Everything optional -> app degrades gracefully to Mock Mode."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

DATA_DIR = BACKEND_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
AUDIO_DIR = DATA_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


class Settings:
    # --- Gnani platform ---
    gnani_api_key: str = _env("GNANI_API_KEY_ID")
    gnani_base: str = _env("GNANI_API_BASE", "https://api.vachana.ai") or "https://api.vachana.ai"
    stt_rest_path: str = _env("GNANI_STT_REST_PATH", "/v1/speech/to/text")
    stt_ws_path: str = _env("GNANI_STT_WS_PATH", "/v1/speech/to/text/ws")
    tts_rest_path: str = _env("GNANI_TTS_REST_PATH", "/v1/text/to/speech")
    tts_ws_path: str = _env("GNANI_TTS_WS_PATH", "/v1/text/to/speech/ws")
    tts_voice_agent: str = _env("GNANI_TTS_VOICE_AGENT")
    tts_voice_customers: list[str] = [
        v for v in (
            _env("GNANI_TTS_VOICE_CUSTOMER_1"),
            _env("GNANI_TTS_VOICE_CUSTOMER_2"),
            _env("GNANI_TTS_VOICE_CUSTOMER_3"),
        ) if v
    ]
    stt_lang: str = _env("GNANI_STT_LANG", "hi-IN")

    # --- Evon ---
    evon_api_url: str = _env("EVON_API_URL")
    evon_api_key: str = _env("EVON_API_KEY")
    evon_model: str = _env("EVON_MODEL", "evon-v3.3")
    evon_hf_model: str = _env("EVON_HF_MODEL")

    # --- Voice lock ---
    voice_lock_enabled: bool = _env("VOICE_LOCK_ENABLED", "1") == "1"
    voice_lock_threshold: float = float(_env("VOICE_LOCK_THRESHOLD", "0.55") or 0.55)

    @property
    def stt_configured(self) -> bool:
        return bool(self.gnani_api_key)

    @property
    def tts_configured(self) -> bool:
        return bool(self.gnani_api_key)

    @property
    def evon_configured(self) -> bool:
        return bool(self.evon_api_url or self.evon_hf_model)

    @property
    def mode(self) -> str:
        """'gnani' = full Gnani stack, 'mock' = free browser-speech fallback."""
        return "gnani" if self.gnani_api_key else "mock"


settings = Settings()
