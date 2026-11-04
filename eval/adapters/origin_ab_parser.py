"""Adapter für die ORIGIN-Extraktion (AbParserService).

Die Datei `backend/app/services/ab_parser_service.py` wird UNVERÄNDERT aus dem ORIGIN-Repo geladen
(Pfad per ORIGIN_PATH). Es wird nichts aus ORIGIN ins Eval-Repo kopiert. Damit das Modul ohne die
komplette ORIGIN-Umgebung läuft, werden nur `app.core.config` und `app.core.timeouts` durch
minimale Ersatz-Module ersetzt. Gebraucht werden: `pip install anthropic` und ANTHROPIC_API_KEY
als Umgebungsvariable.

    export ORIGIN_PATH=/pfad/zu/ORIGIN
    export ANTHROPIC_API_KEY=...
    python eval/run_eval.py --adapter origin_ab_parser
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types
from datetime import date

_service = None


def _load():
    global _service
    if _service is not None:
        return _service
    root = os.environ.get("ORIGIN_PATH")
    if not root:
        raise SystemExit("ORIGIN_PATH ist nicht gesetzt (Pfad zum ORIGIN-Repo).")
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY ist nicht gesetzt.")
    path = os.path.join(root, "backend", "app", "services", "ab_parser_service.py")

    # Minimale Ersatz-Module für die zwei internen Importe
    app = types.ModuleType("app")
    core = types.ModuleType("app.core")
    config = types.ModuleType("app.core.config")
    config.settings = types.SimpleNamespace(anthropic_api_key=key)
    timeouts = types.ModuleType("app.core.timeouts")

    async def run_with_timeout(coro, timeout_seconds=100, dependency=""):
        return await asyncio.wait_for(coro, timeout=timeout_seconds)

    timeouts.run_with_timeout = run_with_timeout
    for name, mod in [("app", app), ("app.core", core), ("app.core.config", config), ("app.core.timeouts", timeouts)]:
        sys.modules[name] = mod

    spec = importlib.util.spec_from_file_location("ab_parser_service_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses braucht das Modul in sys.modules
    spec.loader.exec_module(module)
    _service = module.AbParserService()
    return _service


async def extract(text: str, today: date) -> dict:
    r = await _load().parse(text, today=today)
    fields = {}
    typed = {
        "po_number": r.po_number, "confirmed_delivery_date": r.confirmed_eta,
        "confirmed_quantity": r.confirmed_qty, "unit_price": r.unit_price,
        "currency": r.currency, "supplier_name": r.supplier_name,
    }
    for name, value in typed.items():
        raw = (r.fields or {}).get(name) or {}
        fields[name] = {"value": value, "confidence": raw.get("confidence", 0.0), "evidence": raw.get("evidence")}
    return {"fields": fields, "needs_review": r.needs_review, "review_reason": r.review_reason}
