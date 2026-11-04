"""Erzeugt synthetische Auftragsbestätigungen + Ground-Truth-JSON (reproduzierbar per Seed).

Die Labels entstehen zusammen mit dem Dokument – kein manuelles Labeln für den Hauptteil.
TODO: mehr Layouts, OCR-Rauschen, Mehrpositions-Dokumente, 15 handgebaute Härtefälle.
"""
import argparse
import json
import random
from pathlib import Path

SUPPLIERS = ["Müller Antriebstechnik GmbH", "Nordstahl AG", "Bayern Kunststoff KG", "Acme Fasteners Ltd"]
INCOTERMS = ["EXW", "FCA", "DAP", "DDP", "CIF"]
DATE_FORMATS = {"iso": "%Y-%m-%d", "de": "%d.%m.%Y", "us": "%m/%d/%Y"}
TEMPLATES = [
    "Auftragsbestätigung\nLieferant: {supplier}\nBestellnummer: {order_no}\nMenge: {quantity} Stk\nPreis/Stk: {unit_price} {currency}\nLiefertermin: {date}\nIncoterm: {incoterm}\n",
    "ORDER CONFIRMATION\nFrom: {supplier}\nYour PO: {order_no}\nQty {quantity} pcs @ {unit_price} {currency}\nDelivery: {date}\nTerms: {incoterm}\n",
]


def make_doc(rng: random.Random, i: int):
    from datetime import date, timedelta

    d = date(2026, 1, 1) + timedelta(days=rng.randint(0, 300))
    fmt_name = rng.choice(list(DATE_FORMATS))
    gold = {
        "supplier": rng.choice(SUPPLIERS),
        "order_no": f"45{rng.randint(10000000, 99999999)}",
        "delivery_date": d.isoformat(),
        "quantity": rng.choice([10, 50, 120, 500, 2400]),
        "unit_price": round(rng.uniform(0.5, 250), 2),
        "currency": rng.choice(["EUR", "USD", "CHF"]),
        "incoterm": rng.choice(INCOTERMS),
    }
    text = rng.choice(TEMPLATES).format(date=d.strftime(DATE_FORMATS[fmt_name]), **gold)
    return f"doc_{i:03d}", text, gold


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/gold")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(a.seed)
    for i in range(a.n):
        doc_id, text, gold = make_doc(rng, i)
        (out / f"{doc_id}.txt").write_text(text, encoding="utf-8")
        (out / f"{doc_id}.json").write_text(json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{a.n} Dokumente nach {out}/ geschrieben (seed={a.seed})")


if __name__ == "__main__":
    main()
