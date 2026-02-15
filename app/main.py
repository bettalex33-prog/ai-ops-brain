from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import os
from fastapi import Header, HTTPException, Depends
from dotenv import load_dotenv

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="API key missing")

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


load_dotenv()

API_KEY = os.getenv("API_KEY")


from engine import (
    calculate_cash_flow,
    estimate_burn_rate,
    estimate_runway,
    risk_level,
    project_cash_flow,
    run_monte_carlo_simulation
)

app = FastAPI(title="AI Ops Brain API")


class Transaction(BaseModel):
    date: str
    amount: float
    type: str


class TransactionRequest(BaseModel):
    transactions: List[Transaction]


@app.post("/analyze")
def analyze(data: TransactionRequest, _: str = Depends(verify_api_key)):
    transactions = [t.dict() for t in data.transactions]

    cash_flow = calculate_cash_flow(transactions)
    daily_burn = estimate_burn_rate(transactions)
    runway = estimate_runway(cash_flow["current_balance"], daily_burn)
    risk = risk_level(runway)

    return {
        "cash_flow": cash_flow,
        "daily_burn": daily_burn,
        "runway_days": runway,
        "risk_level": risk
    }


@app.post("/analyze")
def analyze(data: TransactionRequest, _: str = Depends(verify_api_key)):
    transactions = [t.dict() for t in data.transactions]

    projection, cashout_day = project_cash_flow(transactions, projection_days=60)

    return {
        "projection": projection,
        "cashout_day": cashout_day
    }


from engine import apply_scenario_modifiers

class RiskRequest(BaseModel):
    transactions: List[Transaction]
    scenario: str = "base"


@app.post("/analyze")
def analyze(data: TransactionRequest, _: str = Depends(verify_api_key)):
    transactions = [t.dict() for t in data.transactions]

    adjusted = apply_scenario_modifiers(transactions, data.scenario)

    result = run_monte_carlo_simulation(
        adjusted,
        simulations=200,
        projection_days=60
    )

    return {
        "scenario": data.scenario,
        "result": result
    }

