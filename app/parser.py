import pandas as pd


def parse_csv(file_path):
    """
    Expects CSV with columns:
    date, amount, type
    """

    df = pd.read_csv(file_path)

    transactions = []

    for _, row in df.iterrows():
        transactions.append({
            "date": row["date"],
            "amount": float(row["amount"]),
            "type": row["type"].lower()
        })

    return transactions

