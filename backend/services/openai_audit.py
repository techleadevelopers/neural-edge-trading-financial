import os
from typing import Dict

import httpx

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")


def _headers() -> Dict[str, str]:
    return {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}


def explain_signal(payload: dict) -> str:
    if not OPENAI_API_KEY:
        return "OpenAI desativado."
    prompt = (
        "Explique em portugues claro o sinal abaixo. "
        "Se houver risco alto, deixe isso evidente. "
        "Responda em no maximo 6 linhas.\n\n"
        f"SINAL: {payload}"
    )
    body = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 180,
    }
    with httpx.Client(timeout=20) as client:
        res = client.post(f"{OPENAI_BASE_URL}/chat/completions", headers=_headers(), json=body)
        res.raise_for_status()
        data = res.json()
    return data["choices"][0]["message"]["content"].strip()


def audit_signal(payload: dict) -> str:
    if not OPENAI_API_KEY:
        return "OpenAI desativado."
    prompt = (
        "Audite o sinal abaixo considerando regime, volatilidade e contexto. "
        "Se risco alto, recomende NEUTRO e explique o porque. "
        "Nao altere o sinal diretamente, apenas recomende.\n\n"
        f"SINAL: {payload}"
    )
    body = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 180,
    }
    with httpx.Client(timeout=20) as client:
        res = client.post(f"{OPENAI_BASE_URL}/chat/completions", headers=_headers(), json=body)
        res.raise_for_status()
        data = res.json()
    return data["choices"][0]["message"]["content"].strip()
