import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, confloat

app = FastAPI(title="Finance Calculators API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------- Models -----------
class SimpleInterestInput(BaseModel):
    principal: confloat(gt=0) = Field(..., description="Initial amount")
    annual_rate_percent: confloat(ge=0) = Field(..., description="Annual interest rate in %")
    years: confloat(gt=0) = Field(..., description="Time in years")

class CompoundInterestInput(BaseModel):
    principal: confloat(ge=0) = 0
    annual_rate_percent: confloat(ge=0) = 0
    times_per_year: int = Field(1, ge=1)
    years: confloat(ge=0) = 0
    contribution_per_period: confloat(ge=0) = 0

class LoanPaymentInput(BaseModel):
    principal: confloat(gt=0)
    annual_rate_percent: confloat(ge=0)
    years: confloat(gt=0)
    payments_per_year: int = Field(12, ge=1)

class SavingsFutureValueInput(BaseModel):
    present_value: confloat(ge=0) = 0
    contribution_per_period: confloat(ge=0) = 0
    annual_rate_percent: confloat(ge=0) = 0
    years: confloat(ge=0) = 0
    times_per_year: int = Field(12, ge=1)

class RoommateShare(BaseModel):
    name: str
    weight: confloat(gt=0) = 1.0

class RentSplitInput(BaseModel):
    total_rent: confloat(ge=0) = 0
    total_utilities: confloat(ge=0) = 0
    roommates: list[RoommateShare] = Field(..., min_length=1)


# ----------- Utility functions -----------

def round2(x: float) -> float:
    return round(float(x), 2)


# ----------- Routes -----------
@app.get("/")
def read_root():
    return {"message": "Finance Calculators API is running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if backend is available. Database is optional for this app."""
    response = {
        "backend": "✅ Running",
        "database": "ℹ️ Not required for calculators",
        "database_url": None,
        "database_name": None,
        "connection_status": "N/A",
        "collections": []
    }
    # Keep env checks for visibility
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


@app.post("/api/calc/simple-interest")
def calc_simple_interest(payload: SimpleInterestInput):
    P = payload.principal
    r = payload.annual_rate_percent / 100.0
    t = payload.years
    interest = P * r * t
    total = P + interest
    return {
        "principal": round2(P),
        "interest": round2(interest),
        "total": round2(total)
    }


@app.post("/api/calc/compound-interest")
def calc_compound_interest(payload: CompoundInterestInput):
    P = payload.principal
    r = payload.annual_rate_percent / 100.0
    n = payload.times_per_year
    t = payload.years
    c = payload.contribution_per_period

    # Future value of principal compounded
    if n == 0:
        raise HTTPException(status_code=400, detail="times_per_year must be >= 1")

    fv_principal = P * (1 + r / n) ** (n * t)

    # Future value of an annuity due at end of each period (ordinary annuity)
    fv_contrib = 0.0
    if c > 0 and r > 0:
        fv_contrib = c * (((1 + r / n) ** (n * t) - 1) / (r / n))
    elif c > 0 and r == 0:
        fv_contrib = c * n * t

    total = fv_principal + fv_contrib
    interest_earned = total - (P + c * n * t)

    return {
        "future_value": round2(total),
        "interest_earned": round2(interest_earned),
        "principal": round2(P),
        "total_contributions": round2(c * n * t)
    }


@app.post("/api/calc/loan-payment")
def calc_loan_payment(payload: LoanPaymentInput):
    P = payload.principal
    r_annual = payload.annual_rate_percent / 100.0
    m = payload.payments_per_year
    years = payload.years

    if m <= 0:
        raise HTTPException(status_code=400, detail="payments_per_year must be >= 1")

    r = r_annual / m
    N = int(m * years)

    if r == 0:
        payment = P / N
    else:
        payment = P * (r * (1 + r) ** N) / ((1 + r) ** N - 1)

    total_paid = payment * N
    total_interest = total_paid - P

    return {
        "payment_per_period": round2(payment),
        "number_of_payments": N,
        "total_paid": round2(total_paid),
        "total_interest": round2(total_interest)
    }


@app.post("/api/calc/savings-future-value")
def calc_savings_fv(payload: SavingsFutureValueInput):
    PV = payload.present_value
    c = payload.contribution_per_period
    r = payload.annual_rate_percent / 100.0
    n = payload.times_per_year
    t = payload.years

    # grow PV
    fv_pv = PV * (1 + r / n) ** (n * t) if n > 0 else PV

    # grow contributions as ordinary annuity
    if n == 0:
        raise HTTPException(status_code=400, detail="times_per_year must be >= 1")

    if r == 0:
        fv_contrib = c * n * t
    else:
        fv_contrib = c * (((1 + r / n) ** (n * t) - 1) / (r / n))

    fv_total = fv_pv + fv_contrib
    total_contributions = c * n * t
    interest_earned = fv_total - (PV + total_contributions)

    return {
        "future_value": round2(fv_total),
        "interest_earned": round2(interest_earned),
        "total_contributions": round2(total_contributions)
    }


@app.post("/api/calc/rent-split")
def calc_rent_split(payload: RentSplitInput):
    total = payload.total_rent + payload.total_utilities
    total_weight = sum(r.weight for r in payload.roommates)
    if total_weight <= 0:
        raise HTTPException(status_code=400, detail="Sum of weights must be > 0")

    shares = []
    for r in payload.roommates:
        share_amount = total * (r.weight / total_weight)
        shares.append({
            "name": r.name,
            "weight": r.weight,
            "amount": round2(share_amount)
        })

    return {
        "total": round2(total),
        "roommates": shares
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
