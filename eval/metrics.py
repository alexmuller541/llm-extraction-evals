"""Metriken für Extraktions-Evals. Nur Standardbibliothek.

Eine Vorhersage ist ein dict:
    {"fields": {feld: {"value": ..., "confidence": float, "evidence": str|None}},
     "needs_review": bool}

Pro Dokument und Feld gibt es genau ein Ergebnis:
    correct        Gold gesetzt, Vorhersage gleich
    wrong          Gold gesetzt, Vorhersage anders
    missed         Gold gesetzt, Vorhersage fehlt
    hallucinated   Gold fehlt (null), Vorhersage gesetzt
    correct_null   Gold fehlt, Vorhersage fehlt (richtig verzichtet)
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Optional

from schema import CONFIDENT, FIELDS, KEY_FIELDS

# ---------- Normalisierung ----------


def _alnum(s) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).casefold())


def normalize(field: str, value):
    if value is None or str(value).strip() == "":
        return None
    if field in ("confirmed_quantity", "unit_price"):
        try:
            return round(float(value), 4)
        except (TypeError, ValueError):
            return None
    if field == "currency":
        return str(value).strip().upper()[:3]
    if field in ("po_number", "supplier_name"):
        return _alnum(value)
    return str(value).strip()  # Datum: ISO-String


def outcome(field: str, gold, pred_value) -> str:
    g, p = normalize(field, gold), normalize(field, pred_value)
    if g is None:
        return "correct_null" if p is None else "hallucinated"
    if p is None:
        return "missed"
    return "correct" if g == p else "wrong"


# ---------- Feldmetriken ----------


def _field_value(pred: dict, field: str):
    return ((pred or {}).get("fields", {}).get(field) or {}).get("value")


def _field_conf(pred: dict, field: str) -> float:
    try:
        return float(((pred or {}).get("fields", {}).get(field) or {}).get("confidence") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def score_fields(pairs: List[tuple], fields: List[str] = FIELDS) -> Dict[str, dict]:
    """pairs = [(gold, pred), ...] -> pro Feld Zähler, Precision, Recall, F1, Abstention."""
    out = {}
    for f in fields:
        c = defaultdict(int)
        for gold, pred in pairs:
            c[outcome(f, gold.get(f), _field_value(pred, f))] += 1
        returned = c["correct"] + c["wrong"] + c["hallucinated"]
        relevant = c["correct"] + c["wrong"] + c["missed"]
        prec = c["correct"] / returned if returned else 0.0
        rec = c["correct"] / relevant if relevant else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        nulls = c["correct_null"] + c["hallucinated"]
        out[f] = {
            "correct": c["correct"], "wrong": c["wrong"], "missed": c["missed"],
            "hallucinated": c["hallucinated"], "correct_null": c["correct_null"],
            "precision": prec, "recall": rec, "f1": f1,
            "abstention_accuracy": (c["correct_null"] / nulls) if nulls else None,
            "n_gold_null": nulls,
        }
    return out


# ---------- Konfidenz ----------


def expected_calibration_error(confidences: List[float], correct: List[bool], bins: int = 10) -> float:
    n = len(confidences)
    if n == 0:
        return 0.0
    total = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        idx = [i for i, c in enumerate(confidences) if (lo <= c < hi) or (b == bins - 1 and c == 1.0)]
        if idx:
            acc = sum(correct[i] for i in idx) / len(idx)
            conf = sum(confidences[i] for i in idx) / len(idx)
            total += len(idx) / n * abs(acc - conf)
    return total


def calibration(pairs: List[tuple], fields: List[str] = FIELDS) -> dict:
    """ECE über alle gesetzten Vorhersagen (Wert vorhanden) + Genauigkeit oberhalb/unterhalb CONFIDENT."""
    confs, ok = [], []
    for gold, pred in pairs:
        for f in fields:
            if normalize(f, _field_value(pred, f)) is None:
                continue
            confs.append(_field_conf(pred, f))
            ok.append(outcome(f, gold.get(f), _field_value(pred, f)) == "correct")
    hi = [o for c, o in zip(confs, ok) if c >= CONFIDENT]
    lo = [o for c, o in zip(confs, ok) if c < CONFIDENT]
    return {
        "ece": expected_calibration_error(confs, ok),
        "n": len(confs),
        "accuracy_confident": (sum(hi) / len(hi)) if hi else None,
        "n_confident": len(hi),
        "accuracy_unconfident": (sum(lo) / len(lo)) if lo else None,
        "n_unconfident": len(lo),
    }


# ---------- Review-Logik (der Teil, der teure Fehler verhindert) ----------


def review_quality(pairs: List[tuple], key_fields: List[str] = KEY_FIELDS) -> dict:
    """
    unflagged_error: ein Schlüsselfeld ist falsch/halluziniert, aber needs_review == False.
                     Das ist der gefährliche Fall: ein falscher Wert wird ohne Prüfung übernommen.
    over_flag:       alles korrekt und beide Schlüsselfelder im Dokument vorhanden, trotzdem needs_review.
    """
    n = len(pairs)
    unflagged_error = over_flag = errors = 0
    for gold, pred in pairs:
        outs = [outcome(f, gold.get(f), _field_value(pred, f)) for f in key_fields]
        bad = any(o in ("wrong", "hallucinated") for o in outs)
        flagged = bool((pred or {}).get("needs_review", True))
        if bad:
            errors += 1
            if not flagged:
                unflagged_error += 1
        elif all(gold.get(f) is not None for f in key_fields) and all(o == "correct" for o in outs) and flagged:
            over_flag += 1
    return {
        "n": n,
        "docs_with_key_error": errors,
        "unflagged_errors": unflagged_error,
        "unflagged_error_rate": unflagged_error / n if n else 0.0,
        "error_catch_rate": ((errors - unflagged_error) / errors) if errors else None,
        "over_flag_rate": over_flag / n if n else 0.0,
    }


# ---------- Evidenz ----------


def _squash(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().casefold()


def evidence_grounding(docs_and_preds: List[tuple], fields: List[str] = FIELDS) -> dict:
    """Anteil der gelieferten Evidenz-Snippets, die wörtlich im Dokument stehen."""
    total = grounded = 0
    for text, pred in docs_and_preds:
        haystack = _squash(text)
        for f in fields:
            ev = ((pred or {}).get("fields", {}).get(f) or {}).get("evidence")
            if ev:
                total += 1
                grounded += _squash(ev) in haystack
    return {"n": total, "grounded": grounded, "rate": (grounded / total) if total else None}


# ---------- Szenarien ----------


def by_scenario(pairs: List[tuple]) -> Dict[str, dict]:
    """Pro Szenario: wie viele Dokumente waren bei PO und Termin richtig (inkl. richtigem Verzicht)?"""
    groups = defaultdict(list)
    for gold, pred in pairs:
        groups[gold.get("scenario", "unknown")].append((gold, pred))
    res = {}
    for sc, g in sorted(groups.items()):
        po = [outcome("po_number", gl.get("po_number"), _field_value(pr, "po_number")) for gl, pr in g]
        dt = [outcome("confirmed_delivery_date", gl.get("confirmed_delivery_date"),
                      _field_value(pr, "confirmed_delivery_date")) for gl, pr in g]
        ok = ("correct", "correct_null")
        res[sc] = {
            "n": len(g),
            "po_ok": sum(o in ok for o in po),
            "date_ok": sum(o in ok for o in dt),
            "date_wrong": dt.count("wrong"),
            "date_hallucinated": dt.count("hallucinated"),
            "unflagged_errors": review_quality(g)["unflagged_errors"],
        }
    return res


# ---------- Gesamtauswertung + Regressions-Gate ----------


def summarize(items: List[dict]) -> dict:
    """items: [{"text", "gold", "pred"}]"""
    pairs = [(i["gold"], i["pred"]) for i in items]
    fields = score_fields(pairs)
    return {
        "n_docs": len(items),
        "fields": fields,
        "macro_f1": sum(v["f1"] for v in fields.values()) / len(fields),
        "calibration": calibration(pairs),
        "review": review_quality(pairs),
        "evidence": evidence_grounding([(i["text"], i["pred"]) for i in items]),
        "by_scenario": by_scenario(pairs),
    }


def regression_failures(current: dict, baseline: dict, tolerance: float = 0.02) -> List[str]:
    """Gate: Feld-F1 darf nicht um mehr als `tolerance` fallen; unflagged_error_rate nicht steigen."""
    fails = []
    for f, b in baseline.get("fields", {}).items():
        cur = current.get("fields", {}).get(f)
        if cur and cur["f1"] < b["f1"] - tolerance:
            fails.append(f"{f}: F1 {cur['f1']:.3f} < baseline {b['f1']:.3f} - {tolerance}")
    cu, bu = current["review"]["unflagged_error_rate"], baseline.get("review", {}).get("unflagged_error_rate")
    if bu is not None and cu > bu + tolerance:
        fails.append(f"unflagged_error_rate {cu:.3f} > baseline {bu:.3f} + {tolerance}")
    return fails
