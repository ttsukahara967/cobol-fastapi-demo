"""Bridge between Python and the LOANCALC COBOL program.

The COBOL side speaks fixed-length records over stdin/stdout; this module
converts to and from Python objects so the API layer never sees them.
"""

import os
import subprocess
from dataclasses import dataclass
from decimal import Decimal

COBOL_BIN = os.environ.get("LOANCALC_BIN", "/app/bin/loancalc")
TIMEOUT_SECONDS = 5

ERROR_MESSAGES = {
    "01": "input is not numeric",
    "02": "principal must be greater than 0",
    "03": "annual rate must be 20% or less",
    "04": "months must be between 1 and 600",
}


class CobolError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Installment:
    month: int
    payment: int
    principal: int
    interest: int
    balance: int


@dataclass
class LoanSchedule:
    monthly_payment: int
    total_paid: int
    total_interest: int
    installments: list[Installment]


def build_input_record(principal: int, annual_rate: Decimal, months: int) -> str:
    """Encode the request as the 22-char record LOANCALC expects."""
    rate_scaled = int((annual_rate * 10000).to_integral_value())
    return f"{principal:012d}{rate_scaled:06d}{months:04d}"


def parse_output(stdout: str) -> LoanSchedule:
    installments: list[Installment] = []
    trailer = None
    for line in stdout.splitlines():
        if not line:
            continue
        kind = line[0]
        if kind == "E":
            code = line[1:3]
            raise CobolError(code, ERROR_MESSAGES.get(code, "unknown COBOL error"))
        if kind == "D":
            installments.append(
                Installment(
                    month=int(line[1:5]),
                    payment=int(line[5:17]),
                    principal=int(line[17:29]),
                    interest=int(line[29:41]),
                    balance=int(line[41:53]),
                )
            )
        elif kind == "T":
            trailer = (int(line[1:13]), int(line[13:25]), int(line[25:37]))
    if trailer is None:
        raise CobolError("99", "COBOL program produced no trailer record")
    return LoanSchedule(
        monthly_payment=trailer[0],
        total_paid=trailer[1],
        total_interest=trailer[2],
        installments=installments,
    )


def calculate_schedule(principal: int, annual_rate: Decimal, months: int) -> LoanSchedule:
    record = build_input_record(principal, annual_rate, months)
    try:
        result = subprocess.run(
            [COBOL_BIN],
            input=record + "\n",
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise CobolError("98", "COBOL program timed out") from exc
    # Error records are emitted on stdout with a non-zero return code,
    # so parse first and only fall back to the generic error afterwards.
    schedule_or_error = result.stdout
    if result.returncode != 0 and not schedule_or_error.startswith("E"):
        raise CobolError("97", f"COBOL program failed: {result.stderr.strip()}")
    return parse_output(schedule_or_error)
