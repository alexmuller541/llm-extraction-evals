"""Pipeline über das Gold-Set laufen lassen und Metriken schreiben.

TODO: extract() an die echte Extraktions-Pipeline anbinden (Prompt + Modell-Aufruf,
liefert dict mit Feldern und je Feld eine Konfidenz).
"""
import argparse
import json
from pathlib import Path

from metrics import regression_failures, score_documents
from schema import FIELDS


def extract(text: str, model: str) -> dict:
    raise NotImplementedError("Hier die LLM-Extraktion einbauen.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--gold", default="data/gold")
    ap.add_argument("--baseline", default="eval/baseline.json")
    a = ap.parse_args()

    pairs = []
    for txt in sorted(Path(a.gold).glob("*.txt")):
        gold = json.loads(txt.with_suffix(".json").read_text(encoding="utf-8"))
        pairs.append((gold, extract(txt.read_text(encoding="utf-8"), a.model)))

    scores = score_documents(pairs, FIELDS)
    Path("results").mkdir(exist_ok=True)
    Path("results/latest.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    for f, s in scores.items():
        print(f"{f:14s} P={s['precision']:.2f} R={s['recall']:.2f} F1={s['f1']:.2f}")

    bl = Path(a.baseline)
    if bl.exists():
        fails = regression_failures(scores, json.loads(bl.read_text()))
        if fails:
            raise SystemExit("Regression:\n" + "\n".join(fails))


if __name__ == "__main__":
    main()
