"""Reasoning-LLM wrapper (OpenAI-compatible chat + tools).

Access options (free, Apache 2.0):
  A) EVON_API_URL  -> OpenAI-compatible /chat/completions endpoint (platform or
     any local/remote inference server hosting the open weights)
  B) EVON_HF_MODEL -> Hugging Face inference after open-weights approval
If neither is set, the agent falls back to the local Hinglish rule engine so the
product still works end-to-end at zero cost.
"""
import httpx

from app.config import settings
from app.speech.stt import ProviderNotConfigured

SYSTEM_PROMPT = (
    "Tum 'Bol-Khata' ho — ek kirana dukaan ke malik ka AI manager. Tum Hinglish "
    "(Hindi-English mix) me baat karte ho, seedha aur dost ki tarah. Tumhare paas "
    "khata (ledger) manage karne ke tools hain. Kabhi bhi galat amount ya galat "
    "customer ka use mat karo — agar transcript me amount clear nahi hai to poochho. "
    "Chhota jawab do (1-2 line), wahi jo malik ko sunana hai. Numbers ko lakhs/crores "
    "me sahi bolo. Paise ki reminder calls ke waqt polite raho lekin date ka wada "
    "zaroor tulwao."
)


async def chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Return an OpenAI-style response dict with 'choices[0].message'."""
    if settings.evon_api_url:
        return await _chat_openai_compatible(messages, tools)
    if settings.evon_hf_model:
        return await _chat_hf(messages)
    raise ProviderNotConfigured("LLM not configured — rule engine active")


async def _chat_openai_compatible(messages: list[dict], tools: list[dict] | None) -> dict:
    headers = {"Content-Type": "application/json"}
    if settings.evon_api_key:
        headers["Authorization"] = f"Bearer {settings.evon_api_key}"
    payload: dict = {
        "model": settings.evon_model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
        "temperature": 0.3,
        "max_tokens": 300,
    }
    if tools:
        payload["tools"] = [
            {"type": "function", "function": t} for t in tools
        ]
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(settings.evon_api_url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


async def _chat_hf(messages: list[dict]) -> dict:
    prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"https://api-inference.huggingface.co/models/{settings.evon_hf_model}",
            json={"inputs": prompt, "parameters": {"max_new_tokens": 300}},
        )
        resp.raise_for_status()
        text = resp.json()[0].get("generated_text", "")
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}
