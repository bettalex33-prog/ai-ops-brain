from datetime import datetime, timedelta
import random


def calculate_cash_flow(transactions):
    total_income = 0
    total_expense = 0

    for tx in transactions:
        if tx["type"] == "income":
            total_income += tx["amount"]
        elif tx["type"] == "expense":
            total_expense += tx["amount"]

    current_balance = total_income - total_expense

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "current_balance": current_balance
    }


def estimate_burn_rate(transactions, window_days=30):
    """
    Calculates rolling burn rate over last X days
    """

    if not transactions:
        return 0

    # Convert dates
    parsed_transactions = []
    for tx in transactions:
        tx_date = datetime.strptime(tx["date"], "%Y-%m-%d")
        parsed_transactions.append({**tx, "parsed_date": tx_date})

    # Find latest date
    latest_date = max(tx["parsed_date"] for tx in parsed_transactions)

    # Define window start
    window_start = latest_date - timedelta(days=window_days)

    expense_total = 0

    for tx in parsed_transactions:
        if tx["type"] == "expense" and tx["parsed_date"] >= window_start:
            expense_total += tx["amount"]

    daily_burn = expense_total / window_days

    return round(daily_burn, 2)


def estimate_runway(current_balance, daily_burn):
    if daily_burn == 0:
        return float("inf")

    runway_days = current_balance / daily_burn
    return round(runway_days, 2)


def risk_level(runway_days):
    if runway_days == float("inf"):
        return "No Risk"

    if runway_days < 7:
        return "High Risk 🔴"
    elif runway_days < 21:
        return "Medium Risk 🟡"
    else:
        return "Low Risk 🟢"


def project_cash_flow(transactions, projection_days=60):
    """
    Simulates future cash balance over projection period
    """

    if not transactions:
        return []

    # Calculate current balance
    cash_flow = calculate_cash_flow(transactions)
    current_balance = cash_flow["current_balance"]

    # Calculate rolling burn
    daily_burn = estimate_burn_rate(transactions)

    # Calculate average daily income (30-day window)
    income_dates = {}
    for tx in transactions:
        if tx["type"] == "income":
            income_dates.setdefault(tx["date"], 0)
            income_dates[tx["date"]] += tx["amount"]

    if income_dates:
        avg_income_per_income_day = sum(income_dates.values()) / len(income_dates)
        income_frequency = len(income_dates) / 30
    else:
        avg_income_per_income_day = 0
        income_frequency = 0

    projected_balance = current_balance
    projection = []

    for day in range(1, projection_days + 1):
        # Simulate income probabilistically
        if income_frequency > 0:
            income_variation = avg_income_per_income_day * income_frequency
            income_variation *= random.uniform(0.9, 1.1)  # ±10%
            projected_balance += income_variation

        burn_variation = daily_burn * random.uniform(0.95, 1.05)  # ±5%
        projected_balance -= burn_variation

        projection.append({
            "day": day,
            "projected_balance": round(projected_balance, 2)
        })

    return projection

def project_cash_flow(
    transactions,
    projection_days=60,
    window_days=30,
    income_volatility=0.10,  # ±10%
    burn_volatility=0.05,    # ±5%
    seed=None
):
    """
    Returns:
      projection: list of {"day": int, "projected_balance": float}
      cashout_day: int | None   (day balance first goes <= 0)
    """
    if seed is not None:
        random.seed(seed)

    if not transactions:
        return [], None

    # Current balance
    cash_flow = calculate_cash_flow(transactions)
    projected_balance = cash_flow["current_balance"]

    # Rolling burn
    daily_burn = estimate_burn_rate(transactions, window_days=window_days)

    # Income pattern: average per income-day and frequency
    income_dates = {}
    for tx in transactions:
        if tx["type"] == "income":
            income_dates.setdefault(tx["date"], 0.0)
            income_dates[tx["date"]] += float(tx["amount"])

    if income_dates:
        avg_income_per_income_day = sum(income_dates.values()) / len(income_dates)
        income_frequency = len(income_dates) / window_days
    else:
        avg_income_per_income_day = 0.0
        income_frequency = 0.0

    projection = []
    cashout_day = None

    for day in range(1, projection_days + 1):
        # Income contribution (expected daily income) with volatility
        if income_frequency > 0:
            income_expected = avg_income_per_income_day * income_frequency
            income_expected *= random.uniform(1 - income_volatility, 1 + income_volatility)
            projected_balance += income_expected

        # Burn with volatility
        burn = daily_burn * random.uniform(1 - burn_volatility, 1 + burn_volatility)
        projected_balance -= burn

        projection.append({"day": day, "projected_balance": round(projected_balance, 2)})

        if cashout_day is None and projected_balance <= 0:
            cashout_day = day

    return projection, cashout_day


def run_monte_carlo_simulation(
    transactions,
    simulations=200,
    projection_days=60,
    window_days=30,
    income_volatility=0.10,
    burn_volatility=0.05,
    seed=42
):
    """
    Runs many simulated futures and returns risk summary.
    """
    endings = []
    cashouts = []  # list of cashout_day for failed runs

    for i in range(simulations):
        # Different seed per run for reproducibility
        sim_seed = None if seed is None else (seed + i)

        projection, cashout_day = project_cash_flow(
            transactions,
            projection_days=projection_days,
            window_days=window_days,
            income_volatility=income_volatility,
            burn_volatility=burn_volatility,
            seed=sim_seed
        )

        ending_balance = projection[-1]["projected_balance"] if projection else 0.0
        endings.append(float(ending_balance))

        if cashout_day is not None:
            cashouts.append(cashout_day)

    endings_sorted = sorted(endings)
    n = len(endings_sorted)

    def percentile(p):
        if n == 0:
            return 0.0
        # nearest-rank style
        idx = max(0, min(n - 1, int(round((p / 100) * (n - 1)))))
        return endings_sorted[idx]

    prob_cashout = (len(cashouts) / simulations) if simulations > 0 else 0.0

    result = {
        "simulations": simulations,
        "projection_days": projection_days,
        "window_days": window_days,
        "income_volatility": income_volatility,
        "burn_volatility": burn_volatility,
        "probability_cashout": round(prob_cashout, 4),  # e.g. 0.2350
        "cashout_count": len(cashouts),
        "ending_balance_worst": round(endings_sorted[0], 2) if n else 0.0,
        "ending_balance_median": round(percentile(50), 2),
        "ending_balance_best": round(endings_sorted[-1], 2) if n else 0.0,
        "ending_balance_p10": round(percentile(10), 2),
        "ending_balance_p90": round(percentile(90), 2),
        "avg_cashout_day": round(sum(cashouts) / len(cashouts), 2) if cashouts else None,
        "min_cashout_day": min(cashouts) if cashouts else None,
        "max_cashout_day": max(cashouts) if cashouts else None,
    }

    return result

def apply_scenario_modifiers(transactions, scenario="base"):
    """
    Adjusts income and expense values based on scenario
    """

    adjusted = []

    for tx in transactions:
        new_tx = tx.copy()

        if scenario == "optimistic":
            if tx["type"] == "income":
                new_tx["amount"] *= 1.15  # +15% income
            if tx["type"] == "expense":
                new_tx["amount"] *= 0.95  # -5% expenses

        elif scenario == "conservative":
            if tx["type"] == "income":
                new_tx["amount"] *= 0.85  # -15% income
            if tx["type"] == "expense":
                new_tx["amount"] *= 1.10  # +10% expenses

        # base = no change

        adjusted.append(new_tx)

    return adjusted

