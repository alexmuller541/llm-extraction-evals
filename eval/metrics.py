"""Metriken für den Feldvergleich. Reine Standardbibliothek, voll getestet."""
from __future__ import annotations

from collections import defaultdict


def normalize(field: str, value):
    if value is None:
        return None
    if field in ("quantity", "unit_price"):
        return round(float(str(value).replace(",", ".")), 4)
    if field in ("currency", "incoterm", "order_no"):
        return str(value).strip().upper()
    return str(value).strip().lower()


def score_documents(pairs: list[tuple[dict, dict]], fields: list[str]) -> dict:
    """pairs = [(gold, pred), ...]. Gibt pro Feld tp/fp/fn und P/R/F1 zurück.

    tp: gold und pred gesetzt und gleich
    fp: pred gesetzt, aber falsch oder gold fehlt
    fn: gold gesetzt, aber pred fehlt oder falsch
    """
    counts = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    for gold, pred in pairs:
        for f in fields:
            g, p = normalize(f, gold.get(f)), normalize(f, pred.get(f))
            if g is not None and p is not None and g == p:
                counts[f]["tp"] += 1
            else:
                if p is not None:
                    counts[f]["fp"] += 1
                if g is not None:
                    counts[f]["fn"] += 1
    out = {}
    for f in fields:
        c = counts[f]
        prec = c["tp"] / (c["tp"] + c["fp"]) if (c["tp"] + c["fp"]) else 0.0
        rec = c["tp"] / (c["tp"] + c["fn"]) if (c["tp"] + c["fn"]) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        out[f] = {**c, "precision": prec, "recall": rec, "f1": f1}
    return out


def expected_calibration_error(confidences: list[float], correct: list[bool], bins: int = 10) -> float:
    """ECE: gewichteter Abstand zwischen mittlerer Konfidenz und Trefferquote je Bin."""
    n = len(confidences)
    if n == 0:
        return 0.0
    total = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, c in enumerate(confidences) if (lo <= c < hi) or (b == bins - 1 and c == 1.0)]
        if not idx:
            continue
        acc = sum(correct[i] for i in idx) / len(idx)
        conf = sum(confidences[i] for i in idx) / len(idx)
        total += len(idx) / n * abs(acc - conf)
    return total


def regression_failures(current: dict, baseline: dict, tolerance: float = 0.02) -> list[str]:
    """Felder, deren F1 mehr als `tolerance` unter der Baseline liegt."""
    return [
        f"{f}: {current[f]['f1']:.3f} < baseline {b['f1']:.3f} - {tolerance}"
        for f, b in baseline.items()
        if f in current and current[f]["f1"] < b["f1"] - tolerance
    ]
