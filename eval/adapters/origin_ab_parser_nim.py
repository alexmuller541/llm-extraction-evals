"""ORIGIN-Parser-Prompt auf NVIDIA NIM (Llama 3.3 70B) statt Anthropic Haiku.

WICHTIG für die Einordnung der Ergebnisse: ORIGIN ruft den Parser produktiv über Anthropic Haiku
auf. Dieser Adapter misst etwas anderes: den **unveränderten Prompt und die unveränderte
Validierungslogik** aus `ab_parser_service.py` (SYSTEM_PROMPT, `_extract_json`, `build_result`),
aber mit einem NIM-Modell. Die Ergebnisse gelten für "ORIGIN-Parser-Prompt auf Llama 3.3 70B",
nicht für den Haiku-Pfad.

    export ORIGIN_PATH=/pfad/zu/ORIGIN
    export NIM_API_KEY=nvapi-...            # derselbe Key wie `nim_api_key` in ORIGIN
    python eval/run_eval.py --adapter origin_ab_parser_nim --limit 5 --concurrency 1

Free-Tier-Limit (laut ORIGIN-Konfiguration): 5 Aufrufe pro Minute. Der Adapter hält deshalb
mindestens 12,5 s Abstand, wartet bei HTTP 429 und speichert jede Antwort in results/cache/.
Ein abgebrochener Lauf setzt dort fort, ohne bereits beantwortete Dokumente neu zu bezahlen.
Nur Standardbibliothek (urllib), kein openai-Paket nötig.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from adapters.origin_ab_parser import load_module, map_result

NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"
MIN_INTERVAL_S = 12.5      # 5 Aufrufe pro Minute
COOLDOWN_429_S = 30.0      # wie nim_rate_limit_cooldown_seconds in ORIGIN
MAX_RETRIES = 3
CACHE_DIR = Path("results/cache/origin_ab_parser_nim")

_lock = None
_last_call = 0.0


def _model() -> str:
    return os.environ.get("NIM_MODEL", DEFAULT_MODEL)


def _cache_path(text: str) -> Path:
    key = hashlib.sha256((_model() + "\n" + text).encode("utf-8")).hexdigest()[:24]
    return CACHE_DIR / f"{key}.json"


def _post(payload: dict, api_key: str, timeout: float = 120.0) -> dict:
    req = urllib.request.Request(
        NIM_URL, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


async def _throttle() -> None:
    global _lock, _last_call
    if _lock is None:
        _lock = asyncio.Lock()
    async with _lock:
        wait = _last_call + MIN_INTERVAL_S - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call = time.monotonic()


async def _complete(text: str, api_key: str) -> str:
    mod = load_module()
    cache = _cache_path(text)
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))["content"]
    payload = {
        "model": _model(), "temperature": 0, "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": mod.SYSTEM_PROMPT},
            {"role": "user", "content": f"Order confirmation document:\n\n{text[:20000]}"},
        ],
    }
    for attempt in range(MAX_RETRIES + 1):
        await _throttle()
        try:
            data = await asyncio.to_thread(_post, payload, api_key)
            content = data["choices"][0]["message"]["content"] or ""
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps({"model": _model(), "content": content}), encoding="utf-8")
            print(f"[nim] ok ({attempt + 1}. Versuch)", file=sys.stderr, flush=True)
            return content
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < MAX_RETRIES:
                retry = exc.headers.get("Retry-After")
                delay = float(retry) if retry and retry.replace(".", "", 1).isdigit() else COOLDOWN_429_S
                print(f"[nim] 429, warte {delay:.0f}s", file=sys.stderr, flush=True)
                await asyncio.sleep(delay)
                continue
            raise
    raise RuntimeError("NIM: Wiederholungen aufgebraucht")


async def extract(text: str, today: date) -> dict:
    api_key = os.environ.get("NIM_API_KEY")
    if not api_key:
        raise SystemExit("NIM_API_KEY ist nicht gesetzt.")
    mod = load_module()
    if not text.strip():
        raise ValueError("document_text is empty")
    content = await _complete(text, api_key)
    payload = mod._extract_json(content.strip())
    if payload is None:  # gleiche Rückfall-Semantik wie in ORIGIN: kein JSON -> Prüfung nötig
        return {"fields": {}, "needs_review": True, "review_reason": "parser returned no usable JSON"}
    return map_result(mod.build_result(payload, today=today))
