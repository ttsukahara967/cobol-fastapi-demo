# COBOL x FastAPI Loan Calculator

A sample showing the most common way to expose COBOL logic as a REST API:
**FastAPI handles HTTP / validation / JSON, and a GnuCOBOL program does the math.**
Everything builds and runs inside Docker — no local COBOL compiler needed.

![Loan calculator UI: monthly payment, totals and the repayment schedule](docs/screenshot.jpg)

```
Browser / client
   │  JSON
   ▼
FastAPI (app/main.py)          validation, HTTP, OpenAPI docs
   │  fixed-length record via stdin
   ▼
app/cobol_bridge.py            record encode/decode, subprocess call
   │
   ▼
cobol/loancalc.cob             level-payment loan schedule (GnuCOBOL)
   │  D/T/E fixed-length records via stdout
   └──────────► back to FastAPI → JSON
```

## Run

```bash
docker compose up --build api
```

- UI: http://localhost:8090/
- API docs (Swagger): http://localhost:8090/docs

Change the host port with `API_PORT=9000 docker compose up api`.

## Test

```bash
docker compose --profile test run --rm --build test
```

The tests compare COBOL's results with an independent Python implementation
of the same formula, and check invariants (final balance is 0, principal parts
sum to the loan amount, etc.).

## API

`POST /api/loan/schedule`

```json
{ "principal": 30000000, "annual_rate": "1.5", "months": 420 }
```

Response (truncated):

```json
{
  "monthly_payment": 91855,
  "total_paid": 38579007,
  "total_interest": 8579007,
  "installments": [
    { "month": 1, "payment": 91855, "principal": 54355, "interest": 37500, "balance": 29945645 }
  ]
}
```

## COBOL record layout

Input (22 chars): `principal 9(12)` + `annual rate 9(2)V9(4)` + `months 9(4)`

| Record | Layout |
|---|---|
| `D` detail (per month) | month 9(4), payment 9(12), principal 9(12), interest 9(12), balance 9(12) |
| `T` trailer | monthly payment 9(12), total paid 9(12), total interest 9(12) |
| `E` error | code X(2): 01 non-numeric, 02 zero principal, 03 rate > 20%, 04 months out of range |

Calculation rules: monthly payment is rounded to the nearest yen, monthly
interest is truncated, and the last installment absorbs the remainder.

## Design notes

- Input is validated twice: Pydantic at the API boundary, and the COBOL program
  itself (so it stays safe if called from batch jobs or other callers).
- `subprocess` starts one process per request — simple and isolated. For high
  throughput, build the program as a shared library (`cobc -m`) and call it
  through `ctypes` instead.
