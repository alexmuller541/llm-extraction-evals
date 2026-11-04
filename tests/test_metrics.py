import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))

from metrics import (  # noqa: E402
    evidence_grounding, expected_calibration_error, normalize, outcome, regression_failures,
    review_quality, score_fields, summarize,
)


def _pred(po="PO-1", date="2026-09-01", conf=0.95, review=False, evidence=None):
    f = lambda v: {"value": v, "confidence": conf, "evidence": evidence}  # noqa: E731
    return {"fields": {"po_number": f(po), "confirmed_delivery_date": f(date)}, "needs_review": review}


def test_normalize():
    assert normalize("po_number", " po-4471 ") == "po4471"
    assert normalize("currency", "eur") == "EUR"
    assert normalize("unit_price", "12.5") == 12.5
    assert normalize("confirmed_delivery_date", "") is None


def test_outcome_five_cases():
    assert outcome("currency", "EUR", "eur") == "correct"
    assert outcome("currency", "EUR", "USD") == "wrong"
    assert outcome("currency", "EUR", None) == "missed"
    assert outcome("currency", None, "EUR") == "hallucinated"
    assert outcome("currency", None, None) == "correct_null"


def test_hallucination_hurts_precision_and_abstention():
    pairs = [({"confirmed_delivery_date": None}, _pred(date="2026-09-01")),
             ({"confirmed_delivery_date": "2026-09-01"}, _pred(date="2026-09-01"))]
    s = score_fields(pairs, ["confirmed_delivery_date"])["confirmed_delivery_date"]
    assert s["hallucinated"] == 1 and s["correct"] == 1
    assert s["precision"] == 0.5 and s["recall"] == 1.0
    assert s["abstention_accuracy"] == 0.0


def test_unflagged_error_is_the_dangerous_case():
    gold = {"po_number": "PO-1", "confirmed_delivery_date": "2026-09-01"}
    wrong_unflagged = (gold, _pred(date="2026-08-01", review=False))
    wrong_flagged = (gold, _pred(date="2026-08-01", review=True))
    r = review_quality([wrong_unflagged, wrong_flagged])
    assert r["docs_with_key_error"] == 2 and r["unflagged_errors"] == 1
    assert r["error_catch_rate"] == 0.5


def test_over_flag_only_counts_fully_correct_docs():
    gold = {"po_number": "PO-1", "confirmed_delivery_date": "2026-09-01"}
    assert review_quality([(gold, _pred(review=True))])["over_flag_rate"] == 1.0
    missing_gold = {"po_number": None, "confirmed_delivery_date": "2026-09-01"}
    assert review_quality([(missing_gold, _pred(po=None, review=True))])["over_flag_rate"] == 0.0


def test_ece():
    assert expected_calibration_error([1.0, 1.0], [True, True]) == 0.0
    assert expected_calibration_error([0.95] * 10, [True] * 5 + [False] * 5) > 0.4


def test_evidence_grounding_requires_verbatim_snippets():
    r = evidence_grounding([("Liefertermin:  03.09.2026", _pred(evidence="liefertermin: 03.09.2026")),
                            ("Liefertermin: 03.09.2026", _pred(evidence="Delivery on 3 Sept"))])
    assert r["n"] == 4 and r["grounded"] == 2


def test_regression_gate_checks_f1_and_unflagged_errors():
    base = {"fields": {"po_number": {"f1": 0.95}}, "review": {"unflagged_error_rate": 0.02}}
    cur_bad = {"fields": {"po_number": {"f1": 0.80}}, "review": {"unflagged_error_rate": 0.10}}
    cur_ok = {"fields": {"po_number": {"f1": 0.94}}, "review": {"unflagged_error_rate": 0.02}}
    assert len(regression_failures(cur_bad, base)) == 2
    assert regression_failures(cur_ok, base) == []


def test_summarize_runs_end_to_end():
    gold = {"po_number": "PO-1", "confirmed_delivery_date": "2026-09-01", "scenario": "clean"}
    s = summarize([{"text": "x", "gold": gold, "pred": _pred()}])
    assert s["fields"]["po_number"]["f1"] == 1.0 and "clean" in s["by_scenario"]
