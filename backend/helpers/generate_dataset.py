import pandas as pd
import numpy as np
from faker import Faker
import random
import os

fake = Faker("en_US")
random.seed(42)
np.random.seed(42)

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "customer_data.csv")

STATES = [
    "California", "Texas", "Florida", "New York", "Illinois",
    "Pennsylvania", "Ohio", "Georgia", "North Carolina", "Michigan",
]
SEGMENTS = ["Premium", "Standard", "Basic"]
CARD_TYPES = ["Cashback", "Rewards", "Travel", "Basic"]
PAYMENT_HISTORY = ["Excellent", "Good", "Fair", "Poor"]
COMPLAINT_CATEGORIES = ["Billing Dispute", "High Interest Rate", "Fraud Concern", "Credit Limit", "General"]
LOGIN_FREQUENCY = ["Daily", "Weekly", "Monthly", "Rarely"]


def _clamp(val, lo, hi):
    return max(lo, min(hi, val))


def generate_customer(customer_index: int) -> dict:
    customer_id = f"C{customer_index:04d}"

    # --- Demographics ---
    age = random.randint(22, 68)
    gender = random.choice(["Male", "Female"])
    state = random.choice(STATES)
    segment = random.choices(SEGMENTS, weights=[20, 55, 25])[0]

    # --- Account ---
    tenure_months = random.randint(1, 96)
    card_type = random.choice(CARD_TYPES)
    num_products = random.randint(1, 4)
    account_status = random.choices(["Active", "Dormant"], weights=[85, 15])[0]

    # --- Credit & Balance ---
    credit_limit = random.choice([25000, 50000, 75000, 100000, 150000, 200000, 300000])
    # Controlled distribution: ~18% high utilization (churn signal), rest moderate/low
    if random.random() < 0.18:
        utilization_rate = round(random.uniform(81, 99), 1)
    else:
        utilization_rate = round(random.uniform(5, 78), 1)
    current_balance = int(credit_limit * utilization_rate / 100)
    overlimit_count_6m = random.choices([0, 1, 2, 3], weights=[70, 18, 8, 4])[0]

    # --- Transactions ---
    # Controlled distribution: ~20% inactive >30 days (churn signal)
    if random.random() < 0.20:
        days_since_last_transaction = random.randint(31, 110)
    else:
        days_since_last_transaction = random.randint(1, 29)
    total_transactions_6m = random.randint(0, 60)
    avg_monthly_spend_6m = round(random.uniform(1000, 40000), 2)

    # Controlled distribution: ~18% significant spend drop (churn signal)
    if random.random() < 0.18:
        last_month_spend = round(avg_monthly_spend_6m * random.uniform(0.1, 0.55), 2)
    else:
        last_month_spend = round(avg_monthly_spend_6m * random.uniform(0.65, 1.4), 2)
    spend_drop_pct = round((last_month_spend - avg_monthly_spend_6m) / avg_monthly_spend_6m * 100, 1)

    # --- Payments ---
    payment_history = random.choices(PAYMENT_HISTORY, weights=[30, 35, 25, 10])[0]
    num_late_payments_6m = random.choices([0, 1, 2, 3, 4], weights=[55, 20, 13, 8, 4])[0]
    min_payment_missed = random.choices([True, False], weights=[15, 85])[0]
    avg_payment_ratio = round(random.uniform(0.1, 1.0), 2)

    # --- Satisfaction ---
    complaints_6m = random.choices([0, 1, 2, 3, 4], weights=[60, 20, 12, 5, 3])[0]
    if complaints_6m == 0:
        complaint_resolved = "NA"
        last_complaint_category = "NA"
    else:
        complaint_resolved = random.choices(["Yes", "No"], weights=[55, 45])[0]
        last_complaint_category = random.choice(COMPLAINT_CATEGORIES)
    nps_score = random.randint(0, 10)
    app_login_frequency = random.choice(LOGIN_FREQUENCY)

    # --- Competitor & Engagement ---
    # Controlled distribution: ~20% clicked competitor offer (churn signal)
    competitor_offer_clicked = random.choices([True, False], weights=[20, 80])[0]
    reward_points_balance = random.randint(0, 15000)
    email_open_rate = round(random.uniform(0, 100), 1)

    # Realistic correlations: churn signals cluster together naturally
    # High utilization customers -> more complaints, lower NPS, more competitor interest
    if utilization_rate > 80:
        if random.random() < 0.4:
            complaints_6m = max(complaints_6m, random.randint(1, 3))
            complaint_resolved = random.choices(["Yes", "No"], weights=[40, 60])[0]
            last_complaint_category = random.choice(COMPLAINT_CATEGORIES)
        nps_score = _clamp(nps_score - random.randint(1, 4), 0, 10)
        if random.random() < 0.3:
            competitor_offer_clicked = True

    # Long inactivity -> reduced spend, lower NPS
    if days_since_last_transaction > 30:
        last_month_spend = round(avg_monthly_spend_6m * random.uniform(0.05, 0.3), 2)
        spend_drop_pct = round((last_month_spend - avg_monthly_spend_6m) / avg_monthly_spend_6m * 100, 1)
        nps_score = _clamp(nps_score - random.randint(0, 3), 0, 10)

    # Low NPS -> more likely competitor interest
    if nps_score <= 4:
        if random.random() < 0.3:
            competitor_offer_clicked = True

    return {
        "customer_id": customer_id,
        "age": age,
        "gender": gender,
        "state": state,
        "customer_segment": segment,
        "tenure_months": tenure_months,
        "card_type": card_type,
        "num_products": num_products,
        "account_status": account_status,
        "credit_limit": credit_limit,
        "current_balance": current_balance,
        "utilization_rate": utilization_rate,
        "overlimit_count_6m": overlimit_count_6m,
        "days_since_last_transaction": days_since_last_transaction,
        "total_transactions_6m": total_transactions_6m,
        "avg_monthly_spend_6m": avg_monthly_spend_6m,
        "last_month_spend": last_month_spend,
        "spend_drop_pct": spend_drop_pct,
        "payment_history": payment_history,
        "num_late_payments_6m": num_late_payments_6m,
        "min_payment_missed": min_payment_missed,
        "avg_payment_ratio": avg_payment_ratio,
        "complaints_6m": complaints_6m,
        "complaint_resolved": complaint_resolved,
        "last_complaint_category": last_complaint_category,
        "nps_score": nps_score,
        "app_login_frequency": app_login_frequency,
        "competitor_offer_clicked": competitor_offer_clicked,
        "reward_points_balance": reward_points_balance,
        "email_open_rate": email_open_rate,
    }


def generate_dataset(n: int = 1000) -> pd.DataFrame:
    rows = [generate_customer(i + 1) for i in range(n)]
    df = pd.DataFrame(rows)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Dataset saved: {OUTPUT_PATH}")
    print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")

    print("\n--- Signal Distribution ---")
    print(f"S1 High Utilization  (>80%):       {(df['utilization_rate'] > 80).sum()} customers")
    print(f"S2 Inactive          (>30 days):    {(df['days_since_last_transaction'] > 30).sum()} customers")
    print(f"S3 Unresolved Complaint:            {((df['complaints_6m'] > 0) & (df['complaint_resolved'] == 'No')).sum()} customers")
    print(f"S4 Competitor Click:                {df['competitor_offer_clicked'].sum()} customers")
    print(f"S5 Spend Drop        (<-40%):       {(df['spend_drop_pct'] < -40).sum()} customers")

    return df


if __name__ == "__main__":
    generate_dataset()