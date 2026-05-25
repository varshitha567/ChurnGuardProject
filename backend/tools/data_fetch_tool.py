import os
import io
import pandas as pd
import boto3
from langchain_core.tools import tool
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Columns included in every signal response (for agent context + customer identification)
BASE_COLS = ["customer_id", "age", "customer_segment", "tenure_months", "nps_score"]

# Only the columns relevant to each signal are sent to Claude — keeps tokens low
SIGNAL_COLS = {
    "high_utilization":      ["utilization_rate", "current_balance", "credit_limit",
                               "overlimit_count_6m", "payment_history", "num_late_payments_6m"],

    "inactivity":            ["days_since_last_transaction", "total_transactions_6m",
                               "avg_monthly_spend_6m", "last_month_spend", "app_login_frequency",
                               "account_status"],

    "unresolved_complaints": ["complaints_6m", "complaint_resolved",
                               "last_complaint_category", "payment_history"],

    "competitor_interest":   ["competitor_offer_clicked", "email_open_rate",
                               "reward_points_balance", "app_login_frequency"],

    "spend_drop":            ["spend_drop_pct", "last_month_spend",
                               "avg_monthly_spend_6m", "total_transactions_6m", "payment_history"],
}

# Filter condition per signal
SIGNAL_CONDITIONS = {
    "high_utilization":      lambda df: df[df["utilization_rate"] > 80],
    "inactivity":            lambda df: df[df["days_since_last_transaction"] > 30],
    "unresolved_complaints": lambda df: df[(df["complaints_6m"] > 0) & (df["complaint_resolved"] == "No")],
    "competitor_interest":   lambda df: df[df["competitor_offer_clicked"] == True],
    "spend_drop":            lambda df: df[df["spend_drop_pct"] < -40],
}


def _load_dataframe() -> pd.DataFrame:
    """
    Reads from S3 when AWS credentials are configured.
    Falls back to local CSV during development.
    """
    bucket = os.getenv("S3_BUCKET_NAME")
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "")

    if access_key and access_key != "your_aws_access_key_here" and bucket:
        s3 = boto3.client("s3")
        obj = s3.get_object(Bucket=bucket, Key="customer_data.csv")
        return pd.read_csv(io.BytesIO(obj["Body"].read()))

    # Local fallback during development
    local_path = os.path.join(os.path.dirname(__file__), "..", "data", "customer_data.csv")
    return pd.read_csv(local_path)


@tool
def fetch_customers_by_signal(signal: str) -> str:
    """
    Fetches filtered customer data for a given churn signal.
    Returns only the columns relevant to that signal to stay within token limits.

    Valid signals:
    - high_utilization
    - inactivity
    - unresolved_complaints
    - competitor_interest
    - spend_drop
    """
    if signal not in SIGNAL_CONDITIONS:
        return f"Unknown signal '{signal}'. Valid options: {list(SIGNAL_CONDITIONS.keys())}"

    df = _load_dataframe()
    filtered = SIGNAL_CONDITIONS[signal](df)

    if filtered.empty:
        return f"No customers flagged for signal: {signal}"

    cols = BASE_COLS + SIGNAL_COLS[signal]
    result = filtered[cols].to_string(index=False)

    return (
        f"Signal: {signal}\n"
        f"Customers flagged: {len(filtered)}\n\n"
        f"{result}"
    )