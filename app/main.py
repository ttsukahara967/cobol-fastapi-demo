"""FastAPI front end for the COBOL loan calculator.

FastAPI owns HTTP, validation and JSON; the arithmetic lives in COBOL.
"""

from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.cobol_bridge import CobolError, calculate_schedule

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="COBOL x FastAPI Loan Calculator",
    description="Level-payment loan schedules computed by a GnuCOBOL program.",
    version="1.0.0",
)


class LoanRequest(BaseModel):
    principal: int = Field(..., gt=0, le=999_999_999_999, examples=[30_000_000])
    annual_rate: Decimal = Field(
        ..., ge=0, le=20, max_digits=6, decimal_places=4, examples=["1.5"]
    )
    months: int = Field(..., ge=1, le=600, examples=[420])


class InstallmentOut(BaseModel):
    month: int
    payment: int
    principal: int
    interest: int
    balance: int


class LoanResponse(BaseModel):
    monthly_payment: int
    total_paid: int
    total_interest: int
    installments: list[InstallmentOut]


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/loan/schedule", response_model=LoanResponse)
def loan_schedule(req: LoanRequest) -> LoanResponse:
    try:
        schedule = calculate_schedule(req.principal, req.annual_rate, req.months)
    except CobolError as exc:
        status = 422 if exc.code in {"01", "02", "03", "04"} else 500
        raise HTTPException(status_code=status, detail={"code": exc.code, "message": exc.message})
    return LoanResponse(
        monthly_payment=schedule.monthly_payment,
        total_paid=schedule.total_paid,
        total_interest=schedule.total_interest,
        installments=[InstallmentOut(**vars(i)) for i in schedule.installments],
    )
