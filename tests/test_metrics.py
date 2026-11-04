import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))

from metrics import expected_calibration_error, normalize, regression_failures, score_documents  # noqa: E402

F = ["order_no", "quantity"]


def test_normalize_numbers_and_codes():
    assert normalize("quantity", "12,5") == 12.5
    assert normalize("incoterm", " dap ") == "DAP"
    assert normalize("supplier", None) is None


def test_perfect_prediction():
    pairs = [({"order_no": "A1", "quantity": 10}, {"order_no": "a1", "quantity": "10"})]
    s = score_documents(pairs, F)
    assert s["order_no"]["f1"] == 1.0 and s["quantity"]["f1"] == 1.0


def test_wrong_and_missing_values():
    pairs = [
        ({"order_no": "A1", "quantity": 10}, {"order_no": "B2", "quantity": None}),
    ]
    s = score_documents(pairs, F)
    assert s["order_no"]["fp"] == 1 and s["order_no"]["fn"] == 1 and s["order_no"]["f1"] == 0.0
    assert s["quantity"]["fn"] == 1 and s["quantity"]["fp"] == 0


def test_ece_perfectly_calibrated_is_zero():
    assert expected_calibration_error([1.0, 1.0], [True, True]) == 0.0


def test_ece_overconfident():
    assert expected_calibration_error([0.95] * 10, [True] * 5 + [False] * 5) > 0.4


def test_regression_gate():
    base = {"order_no": {"f1": 0.95}}
    assert regression_failures({"order_no": {"f1": 0.80}}, base)
    assert not regression_failures({"order_no": {"f1": 0.94}}, base)
