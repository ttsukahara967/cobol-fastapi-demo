from decimal import ROUND_HALF_UP, Decimal

import pytest
from fastapi.testclient import TestClient

from app.cobol_bridge import CobolError, build_input_record, calculate_schedule
from app.main import app

client = TestClient(app)


def reference_payment(principal: int, annual_rate: str, months: int) -> int:
    """Independent Python implementation of the level-payment formula."""
    r = Decimal(annual_rate) / 1200
    if r == 0:
        return int((Decimal(principal) / months).quantize(Decimal(1), ROUND_HALF_UP))
    factor = (1 + r) ** months
    payment = Decimal(principal) * r * factor / (factor - 1)
    return int(payment.quantize(Decimal(1), ROUND_HALF_UP))


def test_input_record_layout():
    assert build_input_record(30_000_000, Decimal("1.5"), 420) == "000030000000" "015000" "0420"


@pytest.mark.parametrize(
    "principal,rate,months",
    [(30_000_000, "1.5", 420), (1_000_000, "3.25", 60), (500_000, "0", 12), (12_345_678, "0.875", 360)],
)
def test_schedule_matches_reference(principal, rate, months):
    res = client.post(
        "/api/loan/schedule",
        json={"principal": principal, "annual_rate": rate, "months": months},
    )
    assert res.status_code == 200
    body = res.json()
    rows = body["installments"]

    assert body["monthly_payment"] == reference_payment(principal, rate, months)
    assert len(rows) == months
    assert rows[-1]["balance"] == 0
    assert sum(r["principal"] for r in rows) == principal
    assert sum(r["payment"] for r in rows) == body["total_paid"]
    assert body["total_paid"] - body["total_interest"] == principal
    for r in rows:
        assert r["payment"] == r["principal"] + r["interest"]


def test_pydantic_rejects_bad_input():
    res = client.post("/api/loan/schedule", json={"principal": 0, "annual_rate": "1", "months": 12})
    assert res.status_code == 422


def test_cobol_side_validation():
    # Bypass the API layer to prove COBOL validates on its own too.
    with pytest.raises(CobolError) as exc:
        calculate_schedule(1_000_000, Decimal("25"), 12)
    assert exc.value.code == "03"


def test_index_served():
    res = client.get("/")
    assert res.status_code == 200
    assert "ローン返済シミュレーター" in res.text
