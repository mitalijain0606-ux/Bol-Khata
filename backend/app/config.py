"""Central configuration. Everything optional -> app degrades gracefully to Mock Mode."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

# BOLKHATA_DATA_DIR lets tests (or a second demo) use a separate database folder
DATA_DIR = Path(os.getenv("BOLKHATA_DATA_DIR") or BACKEND_DIR / "data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR = DATA_DIR / "audio"
AUDIO_DIR.mkdir(exist_ok=True)


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


class Settings:
    # --- speech provider (endpoints per the provider docs quick-start) ---
    gnani_api_key: str = _env("SPEECH_API_KEY")
    speech_base: str = _env("SPEECH_API_BASE", "https://api.vachana.ai") or "https://api.vachana.ai"
    stt_rest_path: str = _env("STT_REST_PATH", "/stt/v3")
    stt_ws_path: str = _env("STT_WS_PATH", "/stt/v3/stream")
    tts_rest_path: str = _env("TTS_REST_PATH", "/api/v1/tts/inference")
    tts_ws_path: str = _env("TTS_WS_PATH", "/api/v1/tts")
    tts_model: str = _env("TTS_MODEL", "timbre-v2.5")
    tts_voice_agent: str = _env("TTS_VOICE_AGENT", "Poorvi")  # Hinglish voice
    tts_voice_customers: list[str] = [
        v for v in (
            _env("TTS_VOICE_CUSTOMER_1", "Deepak"),
            _env("TTS_VOICE_CUSTOMER_2", "Nalini"),
            _env("TTS_VOICE_CUSTOMER_3", "Kaveri"),
        ) if v
    ]
    stt_lang: str = _env("STT_LANG", "hi-IN")

    # --- Reasoning LLM (any OpenAI-compatible endpoint) ---
    # LLM_* is the current spelling; the older EVON_* names still work.
    evon_api_url: str = _env("LLM_API_URL") or _env("EVON_API_URL")
    evon_api_key: str = _env("LLM_API_KEY") or _env("EVON_API_KEY")
    evon_model: str = _env("LLM_MODEL") or _env("EVON_MODEL", "openai/gpt-oss-20b")
    evon_hf_model: str = _env("LLM_HF_MODEL") or _env("EVON_HF_MODEL")

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
    def llm_label(self) -> str:
        """What the reasoning brain actually is, for honest reporting in the UI,
        the health check and the README. Never guess a vendor we are not calling."""
        if not self.evon_configured:
            return "rule engine (no LLM configured)"
        host = (self.evon_api_url or "").split("/")[2] if "//" in self.evon_api_url else ""
        vendor = {"api.groq.com": "Groq"}.get(host, host or "Hugging Face")
        return f"{self.evon_model} via {vendor}"

    @property
    def mode(self) -> str:
        """'cloud' = provider APIs, 'mock' = free browser-speech fallback."""
        return "gnani" if self.gnani_api_key else "mock"


settings = Settings()
