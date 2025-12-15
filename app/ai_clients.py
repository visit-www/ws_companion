import os
import logging
import requests
from openai import OpenAI
import google.generativeai as genai

logger = logging.getLogger(__name__)


def get_openai_client(api_key: str | None = None) -> OpenAI:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=key)


def call_openai_chat(prompt: str, model: str, max_tokens: int, timeout: int, api_key: str | None = None) -> str:
    """
    Thin wrapper around OpenAI chat completion for JSON/tool-like outputs.
    Returns the message content as a string (caller parses JSON).
    """
    client = get_openai_client(api_key)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a concise radiology reporting helper. "
                    "Always return a strict JSON array of helper cards with keys: "
                    "title (string <=120 chars), summary (string <=240 chars), "
                    "bullets (array of short strings <=6 items), "
                    "insert_options (array of {label,text} objects <=3 items), "
                    "kind (one of: info, score, checklist, differential, technique, measurement, classification, other). "
                    "Do not include any patient identifiers. Keep language neutral and evidence-based."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        timeout=timeout,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or "[]"


def get_gemini_client(api_key: str | None = None):
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    genai.configure(api_key=key)
    return genai


def call_gemini_chat(prompt: str, model: str, max_tokens: int, timeout: int, api_key: str | None = None) -> str:
    """
    Thin wrapper around Gemini chat for JSON-ish outputs.
    Returns the response text as a string.
    """
    client = get_gemini_client(api_key)
    mdl = client.GenerativeModel(model)
    resp = mdl.generate_content(
        prompt,
        generation_config={"max_output_tokens": max_tokens},
    )

    # Safely extract text even when the response has multiple parts
    def _extract_text(r):
        try:
            if hasattr(r, "text") and r.text:
                return r.text
        except Exception:
            pass
        # Fall back to joining all candidate parts' text
        try:
            candidates = getattr(r, "candidates", []) or []
            if candidates:
                parts = getattr(candidates[0].content, "parts", []) or []
                texts = [getattr(p, "text", "") for p in parts if getattr(p, "text", "")]
                if texts:
                    return "\n".join(texts)
        except Exception:
            pass
        return "[]"

    return _extract_text(resp)


# DeepSeek client (OpenAI-compatible chat API)
def call_deepseek_chat(prompt: str, model: str, max_tokens: int, timeout: int, api_key: str | None = None) -> str:
    """
    Minimal DeepSeek chat wrapper using the OpenAI-compatible endpoint.
    Returns the message content as a string; caller parses JSON.
    """
    key = api_key or os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set")

    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return "[]"
    content = choices[0].get("message", {}).get("content")
    return content or "[]"


# Qubrid-hosted DeepSeek-R1 Distill LLaMA 70B
def call_qubrid_deepseek(prompt: str, model: str, max_tokens: int, timeout: int, api_key: str | None = None) -> str:
    key = api_key or os.getenv("QUBRID_API_KEY")
    if not key:
        raise RuntimeError("QUBRID_API_KEY is not set")
    mdl = model or "deepseek-ai/deepseek-r1-distill-llama-70b"

    url = "https://platform.qubrid.com/api/v1/qubridai/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": mdl,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": max_tokens,
        "stream": False,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        return "[]"
    content = choices[0].get("message", {}).get("content")
    return content or "[]"
