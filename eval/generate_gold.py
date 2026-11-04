"""Erzeugt synthetische Auftragsbestätigungen + Ground Truth (reproduzierbar per Seed).

Jedes Dokument gehört zu einem Szenario. Die Szenarien sind so gewählt, dass sie typische
Fehlerquellen einer Extraktion treffen:

  clean            ein Termin, klar beschriftet
  both_dates       Wunschtermin des Käufers UND bestätigter Termin -> bestätigter ist gesucht
  only_requested   nur der Wunschtermin steht im Dokument -> Soll: kein Termin (null)
  ambiguous_date   04/05/2026 -> Tag/Monat nicht unterscheidbar -> Soll: null
  missing_po       keine Bestellnummer des Käufers -> Soll: null (AB-Nummer ist keine PO)
  email            informeller Fließtext statt Formular
  distractor       zusätzlich Termin/PO einer anderen, früheren Lieferung
  ocr_noise        Beschriftungen mit typischen OCR-Verwechslungen (Werte bleiben intakt)

Die Labels entstehen zusammen mit dem Dokument: kein manuelles Labeln nötig.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from schema import GOLD_TODAY

SUPPLIERS = [
    "Jakarta Oils Ltd", "Müller Antriebstechnik GmbH", "Nordstahl AG", "Bayern Kunststoff KG",
    "Acme Fasteners Ltd", "Dubois Composants SAS", "Hanseatic Packaging GmbH",
    "Shenzhen Microtech Co., Ltd.", "Alpine Hydraulik GmbH", "Baltic Cables OÜ",
]
CURRENCIES = ["EUR", "EUR", "EUR", "USD", "CHF", "GBP"]
QUANTITIES = [10, 25, 48, 120, 500, 1200, 2400]
SCENARIO_WEIGHTS = [
    ("clean", 30), ("both_dates", 20), ("email", 12), ("only_requested", 8),
    ("ambiguous_date", 8), ("missing_po", 8), ("distractor", 8), ("ocr_noise", 6),
]
MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]


# ---------- Formatierung ----------
def fmt_date(d: date, style: str) -> str:
    if style == "de":
        return d.strftime("%d.%m.%Y")
    if style == "iso":
        return d.isoformat()
    if style == "en_long":
        return f"{d.day} {MONTHS_EN[d.month - 1]} {d.year}"
    return f"{MONTHS_EN[d.month - 1]} {d.day}, {d.year}"  # en_us_long


def fmt_number(x: float, lang: str, decimals: int) -> str:
    s = f"{x:,.{decimals}f}"  # 1,250.50
    if lang == "de":
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")  # 1.250,50
    return s


def make_po(rng: random.Random) -> str:
    kind = rng.choice(["PO", "SAP", "BTC"])
    if kind == "PO":
        return f"PO-{rng.randint(1000, 99999)}"
    if kind == "SAP":
        return f"45{rng.randint(10000000, 99999999)}"
    return f"B-2026-{rng.randint(1, 9999):04d}"


def ambiguous_date(rng: random.Random) -> Tuple[date, str]:
    """Tag und Monat <= 12 und verschieden -> 04/05/2026 ist nicht eindeutig."""
    while True:
        day, month = rng.randint(1, 12), rng.randint(1, 12)
        if day != month:
            d = date(2026, month, day)
            return d, f"{day:02d}/{month:02d}/2026"


# ---------- Rendering ----------
LABELS = {
    "de": {
        "confirmed": ["Bestätigter Liefertermin", "Liefertermin bestätigt", "Lieferdatum (bestätigt)"],
        "plain": ["Liefertermin"],
        "requested": ["Ihr Wunschtermin", "Gewünschter Liefertermin"],
    },
    "en": {
        "confirmed": ["Confirmed delivery date", "Delivery confirmed for", "Confirmed ship date"],
        "plain": ["Delivery date"],
        "requested": ["Your requested date", "Requested delivery date"],
    },
}


def add_ocr_noise(text: str, rng: random.Random) -> str:
    """Verwechslungen nur im Beschriftungsteil (links vom ersten ':'), Werte bleiben intakt."""
    swap = {"i": "1", "l": "1", "o": "0", "e": "c", "a": "o"}
    out = []
    for line in text.split("\n"):
        if ":" in line:
            label, rest = line.split(":", 1)
            label = "".join(swap[c] if c in swap and rng.random() < 0.12 else c for c in label)
            line = label + ":" + rest
        out.append(line)
    return "\n".join(out)


def render_form(rng, lang, v, scenario) -> str:
    L = LABELS[lang]
    de = lang == "de"
    lines = [("Auftragsbestätigung" if de else "ORDER CONFIRMATION") + f" {v['ab_no']}"]
    lines.append(("Lieferant: " if de else "Supplier: ") + v["supplier"])
    if v["po"]:
        lines.append(("Ihre Bestellung: " if de else "Your PO: ") + v["po"])
    lines.append(("Belegdatum: " if de else "Document date: ") + v["doc_date"])
    unit = "Stk" if de else "pcs"
    lines.append(f"Pos. 1  {'Menge' if de else 'Qty'}: {v['qty']} {unit}")
    lines.append(f"{'Preis/Stk' if de else 'Unit price'}: {v['price']} {v['cur']}")
    if v["requested"]:
        lines.append(f"{rng.choice(L['requested'])}: {v['requested']}")
    if v["confirmed"]:
        key = "plain" if scenario in ("clean", "ocr_noise", "distractor") else "confirmed"
        lines.append(f"{rng.choice(L[key])}: {v['confirmed']}")
    elif scenario == "only_requested":
        lines.append("Liefertermin wird nachgereicht." if de else "Delivery date will follow.")
    if scenario == "distractor":
        note = (f"Hinweis: Die Lieferung zu {v['other_po']} erfolgte am {v['other_date']}."
                if de else f"Note: delivery for {v['other_po']} was completed on {v['other_date']}.")
        lines.insert(rng.randint(2, len(lines)), note)
    return "\n".join(lines) + "\n"


def render_email(rng, lang, v) -> str:
    de = lang == "de"
    po = f" {v['po']}" if v["po"] else ""
    if de:
        body = (f"Betreff: AB zu Ihrer Bestellung{po}\n\nGuten Tag,\n\nvielen Dank für Ihre Bestellung{po}. "
                f"Wir bestätigen die Lieferung von {v['qty']} Stück zum {v['confirmed']}. "
                f"Der Preis beträgt {v['price']} {v['cur']} je Stück.\n\nViele Grüße\n{v['supplier']}\n")
        if v["requested"]:
            body = body.replace("Wir bestätigen", f"Ihr Wunsch war der {v['requested']}. Wir bestätigen")
    else:
        body = (f"Subject: Order acknowledgement{po}\n\nHello,\n\nthank you for your order{po}. "
                f"We confirm delivery of {v['qty']} pieces on {v['confirmed']}. "
                f"The unit price is {v['price']} {v['cur']}.\n\nBest regards\n{v['supplier']}\n")
        if v["requested"]:
            body = body.replace("We confirm", f"You asked for {v['requested']}. We confirm")
    return body


def make_doc(rng: random.Random, scenario: str) -> Tuple[str, Dict]:
    lang = rng.choice(["de", "en"])
    style = rng.choice(["de", "iso"] if lang == "de" else ["en_long", "en_us_long", "iso"])
    supplier = rng.choice(SUPPLIERS)
    cur = rng.choice(CURRENCIES)
    qty = rng.choice(QUANTITIES)
    price = round(rng.uniform(0.5, 2500), 2)
    doc_day = GOLD_TODAY - timedelta(days=rng.randint(0, 6))
    confirmed_day = GOLD_TODAY + timedelta(days=rng.randint(14, 120))
    requested_day = confirmed_day - timedelta(days=rng.randint(3, 21))

    po = None if scenario == "missing_po" else make_po(rng)
    gold_date: Optional[str] = confirmed_day.isoformat()
    confirmed_txt: Optional[str] = fmt_date(confirmed_day, style)
    requested_txt: Optional[str] = None

    if scenario in ("both_dates",) or (scenario == "email" and rng.random() < 0.4):
        requested_txt = fmt_date(requested_day, style)
    if scenario == "only_requested":
        requested_txt, confirmed_txt, gold_date = fmt_date(requested_day, style), None, None
    if scenario == "ambiguous_date":
        _, confirmed_txt = ambiguous_date(rng)
        gold_date = None

    v = {
        "ab_no": f"AB-{rng.randint(100000, 999999)}", "supplier": supplier, "po": po,
        "doc_date": fmt_date(doc_day, style), "qty": fmt_number(qty, lang, 0),
        "price": fmt_number(price, lang, 2), "cur": cur,
        "requested": requested_txt, "confirmed": confirmed_txt,
        "other_po": make_po(rng), "other_date": fmt_date(GOLD_TODAY - timedelta(days=rng.randint(20, 90)), style),
    }
    text = render_email(rng, lang, v) if scenario == "email" else render_form(rng, lang, v, scenario)
    if scenario == "ocr_noise":
        text = add_ocr_noise(text, rng)

    gold = {
        "po_number": po,
        "confirmed_delivery_date": gold_date,
        "confirmed_quantity": float(qty),
        "unit_price": price,
        "currency": cur,
        "supplier_name": supplier,
        "scenario": scenario,
        "lang": lang,
    }
    return text, gold


def scenario_pool(n: int, rng: random.Random) -> List[str]:
    pool = [s for s, w in SCENARIO_WEIGHTS for _ in range(w)]
    rng.shuffle(pool)
    return [pool[i % len(pool)] for i in range(n)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=80)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/gold")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in list(out.glob("doc_*")):
        old.unlink()
    rng = random.Random(a.seed)
    counts: Dict[str, int] = {}
    for i, sc in enumerate(scenario_pool(a.n, rng)):
        text, gold = make_doc(rng, sc)
        (out / f"doc_{i:03d}.txt").write_text(text, encoding="utf-8")
        (out / f"doc_{i:03d}.json").write_text(json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8")
        counts[sc] = counts.get(sc, 0) + 1
    (out / "manifest.json").write_text(json.dumps(
        {"n": a.n, "seed": a.seed, "today": GOLD_TODAY.isoformat(), "scenarios": counts}, indent=2), encoding="utf-8")
    print(f"{a.n} Dokumente nach {out}/ (seed={a.seed}) – {counts}")


if __name__ == "__main__":
    main()
