"""Prüft nur die Anbindung (Laden der Datei, Feld-Mapping) mit einem Fake-Client, ohne API-Aufruf.
Wird übersprungen, wenn ORIGIN_PATH nicht gesetzt ist."""
import asyncio
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))

from schema import GOLD_TODAY  # noqa: E402


class _FakeClient:
    class messages:  # noqa: N801
        @staticmethod
        async def create(**kwargs):
            payload = {
                "po_number": {"value": "PO-4471", "confidence": 0.95, "evidence": "Ihre Bestellung: PO-4471"},
                "confirmed_delivery_date": {"value": "2026-09-03", "confidence": 0.9, "evidence": "Liefertermin: 03.09.2026"},
                "confirmed_quantity": {"value": "120", "confidence": 0.9, "evidence": "120 Stk"},
                "unit_price": {"value": "1.250,50", "confidence": 0.9, "evidence": "1.250,50 EUR"},
                "currency": {"value": "eur", "confidence": 0.9, "evidence": "EUR"},
                "supplier_name": {"value": "Nordstahl AG", "confidence": 0.9, "evidence": "Nordstahl AG"},
            }
            return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(payload))])


def test_origin_adapter_maps_fields():
    if not os.environ.get("ORIGIN_PATH"):
        return  # übersprungen
    os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-used")
    from adapters import origin_ab_parser

    origin_ab_parser._load()._client = _FakeClient()
    pred = asyncio.run(origin_ab_parser.extract("irgendein Text", GOLD_TODAY))
    assert pred["fields"]["confirmed_delivery_date"]["value"] == "2026-09-03"
    assert pred["fields"]["unit_price"]["value"] == 1250.5
    assert pred["fields"]["currency"]["value"] == "EUR"
    assert pred["needs_review"] is False
