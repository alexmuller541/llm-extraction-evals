import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))

import generate_gold  # noqa: E402
from adapters import regex_baseline  # noqa: E402
from schema import GOLD_TODAY  # noqa: E402


def _generate(n=60, seed=7):
    import random
    rng = random.Random(seed)
    return [generate_gold.make_doc(rng, sc) for sc in generate_gold.scenario_pool(n, rng)]


def test_generation_is_deterministic():
    assert _generate() == _generate()


def test_gold_dates_are_present_in_text_or_null():
    for text, gold in _generate():
        if gold["scenario"] in ("clean", "both_dates") and gold["confirmed_delivery_date"]:
            d = gold["confirmed_delivery_date"]
            y, m, day = d.split("-")
            variants = [d, f"{day}.{m}.{y}"]
            assert any(v in text for v in variants) or gold["lang"] == "en"  # EN nutzt Monatsnamen


def test_trap_scenarios_have_null_gold():
    docs = _generate(100)
    for text, gold in docs:
        if gold["scenario"] in ("only_requested", "ambiguous_date"):
            assert gold["confirmed_delivery_date"] is None
        if gold["scenario"] == "missing_po":
            assert gold["po_number"] is None and "Bestellung:" not in text and "Your PO" not in text


def test_all_scenarios_are_generated():
    names = {g["scenario"] for _, g in _generate(100)}
    assert names == {s for s, _ in generate_gold.SCENARIO_WEIGHTS}


def test_baseline_extracts_clean_german_form():
    text = ("Auftragsbestätigung AB-1\nLieferant: Nordstahl AG\nIhre Bestellung: PO-4471\n"
            "Pos. 1  Menge: 120 Stk\nPreis/Stk: 1.250,50 EUR\nLiefertermin: 03.09.2026\n")
    p = asyncio.run(regex_baseline.extract(text, GOLD_TODAY))["fields"]
    assert p["po_number"]["value"] == "PO-4471"
    assert p["confirmed_delivery_date"]["value"] == "2026-09-03"
    assert p["unit_price"]["value"] == 1250.5 and p["currency"]["value"] == "EUR"


def test_baseline_falls_for_requested_date_trap():
    """Die Baseline muss hier scheitern - das ist der Sinn des Szenarios."""
    text = "Ihre Bestellung: PO-1\nGewünschter Liefertermin: 01.10.2026\nBestätigter Liefertermin: 08.10.2026\n"
    p = asyncio.run(regex_baseline.extract(text, GOLD_TODAY))["fields"]
    assert p["confirmed_delivery_date"]["value"] == "2026-10-01"
