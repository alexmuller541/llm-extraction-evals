"""Prüft nur die Anbindung (Laden der Datei, Feld-Mapping, Cache) mit Fake-Antworten, ohne API-Aufruf.
Wird übersprungen, wenn ORIGIN_PATH nicht gesetzt ist."""
import asyncio
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))

from schema import GOLD_TODAY  # noqa: E402

PAYLOAD = {
    "po_number": {"value": "PO-4471", "confidence": 0.95, "evidence": "Ihre Bestellung: PO-4471"},
    "confirmed_delivery_date": {"value": "2026-09-03", "confidence": 0.9, "evidence": "Liefertermin: 03.09.2026"},
    "confirmed_quantity": {"value": "120", "confidence": 0.9, "evidence": "120 Stk"},
    "unit_price": {"value": "1.250,50", "confidence": 0.9, "evidence": "1.250,50 EUR"},
    "currency": {"value": "eur", "confidence": 0.9, "evidence": "EUR"},
    "supplier_name": {"value": "Nordstahl AG", "confidence": 0.9, "evidence": "Nordstahl AG"},
}


class _FakeClient:
    class messages:  # noqa: N801
        @staticmethod
        async def create(**kwargs):
            return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(PAYLOAD))])


def test_origin_adapter_maps_fields():
    if not os.environ.get("ORIGIN_PATH"):
        return  # übersprungen
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")
    from adapters import origin_ab_parser

    origin_ab_parser._get_service()._client = _FakeClient()
    pred = asyncio.run(origin_ab_parser.extract("irgendein Text", GOLD_TODAY))
    assert pred["fields"]["confirmed_delivery_date"]["value"] == "2026-09-03"
    assert pred["fields"]["unit_price"]["value"] == 1250.5
    assert pred["fields"]["currency"]["value"] == "EUR"
    assert pred["needs_review"] is False


def test_nim_adapter_uses_origin_prompt_parses_fenced_json_and_caches(tmp_path=None):
    if not os.environ.get("ORIGIN_PATH"):
        return
    import tempfile

    from adapters import origin_ab_parser_nim as nim

    os.environ["NIM_API_KEY"] = "test-key-not-used"
    nim.MIN_INTERVAL_S = 0
    nim.CACHE_DIR = Path(tempfile.mkdtemp()) / "cache"
    calls = []

    def fake_post(payload, api_key, timeout=120.0):
        calls.append(payload)
        fenced = "```json\n" + json.dumps(PAYLOAD) + "\n```"
        return {"choices": [{"message": {"content": fenced}}]}

    nim._post = fake_post
    pred = asyncio.run(nim.extract("Beispieltext", GOLD_TODAY))
    assert pred["fields"]["po_number"]["value"] == "PO-4471" and pred["needs_review"] is False
    assert calls[0]["messages"][0]["content"].startswith("You extract structured data")  # Prompt aus ORIGIN
    assert calls[0]["temperature"] == 0 and calls[0]["model"] == "meta/llama-3.3-70b-instruct"
    asyncio.run(nim.extract("Beispieltext", GOLD_TODAY))
    assert len(calls) == 1  # zweiter Aufruf kommt aus dem Cache


def test_nim_adapter_without_json_falls_back_to_review():
    if not os.environ.get("ORIGIN_PATH"):
        return
    import tempfile

    from adapters import origin_ab_parser_nim as nim

    os.environ["NIM_API_KEY"] = "test-key-not-used"
    nim.MIN_INTERVAL_S = 0
    nim.CACHE_DIR = Path(tempfile.mkdtemp()) / "cache"
    nim._post = lambda payload, api_key, timeout=120.0: {"choices": [{"message": {"content": "Sorry, no."}}]}
    pred = asyncio.run(nim.extract("anderer Text", GOLD_TODAY))
    assert pred["needs_review"] is True and pred["fields"] == {}
