# Churn Prevention AI Pipeline — Full Project Notes
> Complete record of all decisions, architecture, code, and progress from start to finish.

---

## Table of Contents
1. [Project Idea & Workflow](#1-project-idea--workflow)
2. [Architecture Decisions](#2-architecture-decisions)
3. [Finalised Design](#3-finalised-design)
4. [Data Design — 30 Columns & 5 Signals](#4-data-design--30-columns--5-signals)
5. [Two-Pipeline Design with Approve Button](#5-two-pipeline-design-with-approve-button)
6. [Agent Design — LangChain create_agent](#6-agent-design--langchain-create_agent)
7. [Project Structure](#7-project-structure)
8. [Phase 1 — Local Environment Setup](#8-phase-1--local-environment-setup)
9. [Phase 2 — Dataset Generation](#9-phase-2--dataset-generation)
10. [Phase 4 — Data Fetch Tool](#10-phase-4--data-fetch-tool)
11. [Phase 5 — Signal Agent](#11-phase-5--signal-agent)
12. [Phase 6 — Action Agent](#12-phase-6--action-agent)
13. [Phase 7 — S3 Utils](#13-phase-7--s3-utils)
14. [Phase 8 — FastAPI Routes](#14-phase-8--fastapi-routes)
15. [Remaining Phases](#15-remaining-phases)
16. [Environment Variables Reference](#16-environment-variables-reference)

---

## 1. Project Idea & Workflow

### Original Concept
Build an AI-powered churn prevention pipeline for a financial services company (Synchrony Financial).

### Full Real-Time Workflow (Finalised)

```
EventBridge (9am daily)
      ↓
Lambda 1 — Signal Analysis (Insights Pipeline)
  → reads customer_data.csv from S3 (pandas)
  → 5 signal prompts loop through Agent 1
      same messages[] array passed each time
      GPT-4.1 builds context across all 5 signals
  → Agent 1 identifies common flagged customers
  → saves results JSON to S3
      ↓
React Dashboard reads from S3 via FastAPI
Manager reviews insights + priority list
Manager clicks "Approve & Initiate Actions"
      ↓
API Gateway → Lambda 2 — Action Pipeline
  → reads flagged customers from S3
  → Agent 2 sends personalised retention emails (AWS SES)
  → Agent 2 hits call pipeline endpoint per customer
  → logs all actions taken back to S3
```

---

## 2. Architecture Decisions

### Decision 1 — S3 vs RDS Database

**Question:** Should we store data in S3 (CSV) or AWS RDS (SQL database)?

**Decision: Keep S3 + CSV**

| Option | Setup Time | Cost | SQL Queries | Best For |
|--------|-----------|------|-------------|----------|
| S3 + CSV (pandas) | 30 min | Free tier | No | This project |
| S3 + Athena | 3–4 hrs | ~free but overhead | Yes | 10M+ rows |
| RDS Database | 1–2 hrs | ~$15–25/month | Yes | Transactional apps |

For 1000 rows, reading the CSV directly with pandas in Lambda is more efficient than Athena. Athena is designed for terabytes of data, adds Glue catalog setup, and writes results to a second S3 bucket — overkill for this scale.

**In production:** this would use RDS. For this project, S3 + CSV is the right call.

---

### Decision 2 — 4 Agents vs 3 Agents

**Original design:** 4 agents (Investigator → Analyst → Strategist → Dispatcher)

**Problem:** Agents 1 and 2 were artificially separated. Claude/GPT can find signals AND assess risk in a single prompt.

**Decision: 3 agents**

| Agent | Role |
|-------|------|
| Agent 1 (Signal Analyser) | 5-signal loop with memory — finds patterns and overlaps |
| Agent 2 (Action Agent) | Sends emails + initiates calls for top priority customers |
| (Dispatcher logic) | Folded into s3_utils + FastAPI routes |

**Benefits:**
- 2 Claude/GPT API calls per signal instead of 3 (33% cheaper, 33% faster)
- Simpler code, easier to debug
- No information lost

---

### Decision 3 — Lambda Timeout

**Original concern:** Lambda has a 15-minute max timeout.

**Resolution:** The new architecture makes only 5–6 GPT API calls total (one per signal + summary). This takes ~75 seconds worst case — well within the 15-minute limit. The original concern was based on the old design where every customer got 3 individual API calls.

**Lambda 1 (Insights):** ~2–3 minutes total → safe
**Lambda 2 (Actions):** emails + call triggers for top 10 customers → safe

---

### Decision 4 — Athena vs Pandas

**Decision: Read CSV directly with pandas in Lambda**

- No Glue catalog setup needed
- No second S3 bucket for query results
- No IAM permissions for Athena
- Instant results vs Athena's async query pattern
- For 1000 rows, pandas filter is faster than an Athena query round-trip

**Note:** `data_fetch_tool.py` filters the CSV before sending to GPT — only relevant columns for each signal are passed. This keeps token usage low.

---

### Decision 5 — Thread ID / Memory

**How it actually works:** There is no server-side thread_id in the OpenAI/Claude API. Memory is maintained by passing the full message history in each API call.

LangChain's `create_agent` with `InMemorySaver` checkpointer handles this automatically. The `thread_id` in the config tells `InMemorySaver` which conversation thread to load/save.

```python
config = {"configurable": {"thread_id": "churn_run_20240115_0900"}}
# All invocations with this config share the same conversation history
```

**Important:** `InMemorySaver` stores memory in RAM. All 5 signal prompts must run in the same Lambda invocation for memory to persist. This is guaranteed since they run sequentially in a single function call.

---

### Decision 6 — Approve Button Architecture

**Decision:** Two separate Lambda functions with a human-in-the-loop gate.

```
Lambda 1 → saves results to S3 → dashboard shows insights
                                          ↓
                                   Manager reviews
                                          ↓
                                  Clicks "Approve"
                                          ↓
                              API Gateway → Lambda 2
                                          ↓
                              Emails + Calls fired
```

**Why:** Prevents accidental emails/calls going out. Manager verifies insights are correct before any customer contact. Industry best practice for AI-driven customer actions.

---

### Decision 7 — Frontend

- **Rejected:** Streamlit (limited, not production-quality)
- **Chosen:** React (discussed in detail when we reach Phase 9 — Frontend)

---

## 3. Finalised Design

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Data generation | Python + Faker + Pandas |
| Storage | AWS S3 (CSV + JSON results) |
| AI Agents | LangChain `create_agent` + GPT-4.1 |
| Agent memory | `InMemorySaver` + `thread_id` |
| Backend API | FastAPI |
| Email alerts | AWS SES |
| Call pipeline | Existing endpoint (name + phone + context) |
| Scheduling | AWS EventBridge (cron 9am daily) |
| Lambda 1 | Insights pipeline |
| Lambda 2 | Action pipeline (triggered by Approve button) |
| API Gateway | Exposes Lambda 2 to React frontend |
| Frontend | React |

---

## 4. Data Design — 30 Columns & 5 Signals

### The 5 Churn Signals

| # | Signal Name | Condition | What It Means |
|---|------------|-----------|---------------|
| S1 | `high_utilization` | `utilization_rate > 80%` | Financial stress, card maxed out |
| S2 | `inactivity` | `days_since_last_transaction > 30` | Stopped using the card |
| S3 | `unresolved_complaints` | `complaints_6m > 0` AND `complaint_resolved == 'No'` | Active dissatisfaction |
| S4 | `competitor_interest` | `competitor_offer_clicked == True` | Actively exploring alternatives |
| S5 | `spend_drop` | `spend_drop_pct < -40%` | Significant disengagement |

---

### The 30 Columns

**Customer Identity (4)**
| # | Column | Type | Example |
|---|--------|------|---------|
| 1 | `customer_id` | string | C0047 |
| 2 | `age` | int | 34 |
| 3 | `gender` | string | Male |
| 4 | `state` | string | California |

**Account Profile (5)**
| # | Column | Type | Example |
|---|--------|------|---------|
| 5 | `customer_segment` | string | Premium / Standard / Basic |
| 6 | `tenure_months` | int | 8 |
| 7 | `card_type` | string | Cashback / Rewards / Travel |
| 8 | `num_products` | int | 2 |
| 9 | `account_status` | string | Active / Dormant |

**Credit & Balance (4)**
| # | Column | Type | Example |
|---|--------|------|---------|
| 10 | `credit_limit` | int | 150000 |
| 11 | `current_balance` | int | 136500 |
| 12 | `utilization_rate` | float | 91.0 ← S1 |
| 13 | `overlimit_count_6m` | int | 1 |

**Transaction Activity (5)**
| # | Column | Type | Example |
|---|--------|------|---------|
| 14 | `days_since_last_transaction` | int | 52 ← S2 |
| 15 | `total_transactions_6m` | int | 14 |
| 16 | `avg_monthly_spend_6m` | float | 12000 |
| 17 | `last_month_spend` | float | 3200 |
| 18 | `spend_drop_pct` | float | -73.3 ← S5 |

**Payment Behaviour (4)**
| # | Column | Type | Example |
|---|--------|------|---------|
| 19 | `payment_history` | string | Excellent / Good / Fair / Poor |
| 20 | `num_late_payments_6m` | int | 2 |
| 21 | `min_payment_missed` | bool | True |
| 22 | `avg_payment_ratio` | float | 0.45 |

**Satisfaction & Support (5)**
| # | Column | Type | Example |
|---|--------|------|---------|
| 23 | `complaints_6m` | int | 2 ← S3 |
| 24 | `complaint_resolved` | string | No ← S3 |
| 25 | `last_complaint_category` | string | Billing / Interest Rate / Fraud |
| 26 | `nps_score` | int | 3 |
| 27 | `app_login_frequency` | string | Daily / Weekly / Monthly / Rarely |

**Competitor & Engagement (3)**
| # | Column | Type | Example |
|---|--------|------|---------|
| 28 | `competitor_offer_clicked` | bool | True ← S4 |
| 29 | `reward_points_balance` | int | 340 |
| 30 | `email_open_rate` | float | 12.5 |

### Signal Distribution (from generated dataset)
| Signal | Count | % of Portfolio |
|--------|-------|----------------|
| S1 High Utilization >80% | 169 | 16.9% |
| S2 Inactive >30 days | 198 | 19.8% |
| S3 Unresolved Complaints | 186 | 18.6% |
| S4 Competitor Click | 364 | 36.4% |
| S5 Spend Drop <-40% | 354 | 35.4% |

S4 and S5 being higher is intentional — competitor browsing and spend fluctuations are soft signals genuinely common in any credit card portfolio.

---

## 5. Two-Pipeline Design with Approve Button

```
EventBridge (9am daily)
      ↓
Lambda 1 — Insights Pipeline
  → 5 signal agent analysis
  → saves flagged_customers.json to S3
  → FastAPI reads S3 → dashboard displays results

      [Manager reviews dashboard]
      [Clicks "Approve & Initiate Actions"]
            ↓
      React → POST /api/approve → FastAPI
            ↓ (BackgroundTask)
      Lambda 2 — Action Pipeline
        → reads results from S3
        → Agent 2 sends emails per customer (AWS SES)
        → Agent 2 hits call pipeline endpoint per customer
        → logs all actions taken back to S3
```

**Key benefit:** If insights look wrong on a given day, manager simply doesn't click Approve. No accidental emails or calls ever go out.

---

## 6. Agent Design — LangChain create_agent

### Correct Import (verified via docs)

```python
from langchain.agents import create_agent          # NOT create_react_agent
from langgraph.checkpoint.memory import InMemorySaver  # NOT MemorySaver
```

### How the 5-Signal Loop Works

```python
config = {"configurable": {"thread_id": "churn_run_20240115_0900"}}

for signal_name, prompt in SIGNAL_PROMPTS.items():
    response = agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config=config,   # same thread_id every iteration
    )
```

Each iteration adds to the same memory thread. After all 5 signals, the summary prompt has full context of everything found. Without the shared `thread_id`, the summary would start fresh with no knowledge of the signal analyses.

**Memory diagram:**
```
InMemorySaver (thread: "churn_run_20240115_0900")
│
├── Turn 1: high_utilization  → tool call → analysis stored
├── Turn 2: inactivity        → tool call → analysis stored
├── Turn 3: complaints        → tool call → analysis stored
├── Turn 4: competitor        → tool call → analysis stored
├── Turn 5: spend_drop        → tool call → analysis stored
│
└── Turn 6: SUMMARY → agent reads all 5 turns → identifies overlaps
```

### Token Efficiency

Agent never sees the full 1000-row CSV. The `fetch_customers_by_signal` tool filters first:

| Signal | Rows sent to GPT | Columns sent |
|--------|-----------------|--------------|
| high_utilization | ~169 | 11 columns |
| inactivity | ~198 | 12 columns |
| unresolved_complaints | ~186 | 9 columns |
| competitor_interest | ~364 | 9 columns |
| spend_drop | ~354 | 10 columns |

vs. sending all 1000 rows × 30 columns every call.

---

## 7. Project Structure

```
aws_project1/
│
├── backend/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── signal_agent.py          ← Agent 1 (5-signal analysis + memory)
│   │   └── action_agent.py          ← Agent 2 (emails + calls)
│   │
│   ├── helpers/
│   │   ├── __init__.py
│   │   ├── generate_dataset.py      ← generates customer_data.csv (1000×30)
│   │   └── s3_utils.py              ← upload/download helpers for S3
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py               ← Pydantic models (request/response shapes)
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── insights.py              ← GET /api/insights, GET /api/insights/history
│   │   └── actions.py               ← POST /api/approve
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   └── data_fetch_tool.py       ← LangChain tool (pandas filter per signal)
│   │
│   ├── lambda_handlers/
│   │   ├── lambda_insights.py       ← Lambda 1 handler
│   │   └── lambda_actions.py        ← Lambda 2 handler
│   │
│   ├── data/
│   │   ├── .gitkeep
│   │   └── customer_data.csv        ← generated, then uploaded to S3
│   │
│   ├── .env                         ← all credentials (never commit)
│   ├── .gitignore
│   ├── .python-version              ← 3.13
│   ├── main.py                      ← FastAPI app entry point
│   └── pyproject.toml
│
└── frontend/
    └── (React — Phase 9)
```

---

## 8. Phase 1 — Local Environment Setup

### Dependencies (pyproject.toml)

```toml
dependencies = [
    "boto3",
    "pandas",
    "numpy",
    "faker",
    "langchain",
    "langgraph",
    "langchain-openai",
    "openai",
    "fastapi",
    "uvicorn[standard]",
    "pydantic",
    "python-dotenv",
    "httpx",
]
```

### Setup Commands

```bash
# Create venv
uv venv

# Install all dependencies
uv sync

# Verify
python -c "import boto3, pandas, langchain, openai, fastapi; print('OK')"
```

### main.py (FastAPI entry point)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers import insights, actions

load_dotenv()

app = FastAPI(title="Churn Prevention API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(insights.router, prefix="/api")
app.include_router(actions.router, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}
```

---

## 9. Phase 2 — Dataset Generation

**File:** `helpers/generate_dataset.py`

**Output:** `data/customer_data.csv` — 1000 rows × 30 columns

### Key Design Choices

- Controlled signal distributions (~15–20% per signal) not random
- Realistic correlations baked in:
  - High utilization → more complaints, lower NPS, more competitor clicks
  - Long inactivity → reduced last month spend, lower NPS
  - Low NPS → more competitor interest
- `random.seed(42)` and `np.random.seed(42)` for reproducibility

### Full Code

```python
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
    age = random.randint(22, 68)
    gender = random.choice(["Male", "Female"])
    state = random.choice(STATES)
    segment = random.choices(SEGMENTS, weights=[20, 55, 25])[0]
    tenure_months = random.randint(1, 96)
    card_type = random.choice(CARD_TYPES)
    num_products = random.randint(1, 4)
    account_status = random.choices(["Active", "Dormant"], weights=[85, 15])[0]
    credit_limit = random.choice([25000, 50000, 75000, 100000, 150000, 200000, 300000])

    # Controlled distributions for signal columns
    if random.random() < 0.18:
        utilization_rate = round(random.uniform(81, 99), 1)
    else:
        utilization_rate = round(random.uniform(5, 78), 1)

    current_balance = int(credit_limit * utilization_rate / 100)
    overlimit_count_6m = random.choices([0, 1, 2, 3], weights=[70, 18, 8, 4])[0]

    if random.random() < 0.20:
        days_since_last_transaction = random.randint(31, 110)
    else:
        days_since_last_transaction = random.randint(1, 29)

    total_transactions_6m = random.randint(0, 60)
    avg_monthly_spend_6m = round(random.uniform(1000, 40000), 2)

    if random.random() < 0.18:
        last_month_spend = round(avg_monthly_spend_6m * random.uniform(0.1, 0.55), 2)
    else:
        last_month_spend = round(avg_monthly_spend_6m * random.uniform(0.65, 1.4), 2)

    spend_drop_pct = round((last_month_spend - avg_monthly_spend_6m) / avg_monthly_spend_6m * 100, 1)
    payment_history = random.choices(PAYMENT_HISTORY, weights=[30, 35, 25, 10])[0]
    num_late_payments_6m = random.choices([0, 1, 2, 3, 4], weights=[55, 20, 13, 8, 4])[0]
    min_payment_missed = random.choices([True, False], weights=[15, 85])[0]
    avg_payment_ratio = round(random.uniform(0.1, 1.0), 2)
    complaints_6m = random.choices([0, 1, 2, 3, 4], weights=[60, 20, 12, 5, 3])[0]

    if complaints_6m == 0:
        complaint_resolved = "NA"
        last_complaint_category = "NA"
    else:
        complaint_resolved = random.choices(["Yes", "No"], weights=[55, 45])[0]
        last_complaint_category = random.choice(COMPLAINT_CATEGORIES)

    nps_score = random.randint(0, 10)
    app_login_frequency = random.choice(LOGIN_FREQUENCY)
    competitor_offer_clicked = random.choices([True, False], weights=[20, 80])[0]
    reward_points_balance = random.randint(0, 15000)
    email_open_rate = round(random.uniform(0, 100), 1)

    # Correlations
    if utilization_rate > 80:
        if random.random() < 0.4:
            complaints_6m = max(complaints_6m, random.randint(1, 3))
            complaint_resolved = random.choices(["Yes", "No"], weights=[40, 60])[0]
            last_complaint_category = random.choice(COMPLAINT_CATEGORIES)
        nps_score = _clamp(nps_score - random.randint(1, 4), 0, 10)
        if random.random() < 0.3:
            competitor_offer_clicked = True

    if days_since_last_transaction > 30:
        last_month_spend = round(avg_monthly_spend_6m * random.uniform(0.05, 0.3), 2)
        spend_drop_pct = round((last_month_spend - avg_monthly_spend_6m) / avg_monthly_spend_6m * 100, 1)
        nps_score = _clamp(nps_score - random.randint(0, 3), 0, 10)

    if nps_score <= 4:
        if random.random() < 0.3:
            competitor_offer_clicked = True

    return {
        "customer_id": customer_id, "age": age, "gender": gender, "state": state,
        "customer_segment": segment, "tenure_months": tenure_months, "card_type": card_type,
        "num_products": num_products, "account_status": account_status, "credit_limit": credit_limit,
        "current_balance": current_balance, "utilization_rate": utilization_rate,
        "overlimit_count_6m": overlimit_count_6m, "days_since_last_transaction": days_since_last_transaction,
        "total_transactions_6m": total_transactions_6m, "avg_monthly_spend_6m": avg_monthly_spend_6m,
        "last_month_spend": last_month_spend, "spend_drop_pct": spend_drop_pct,
        "payment_history": payment_history, "num_late_payments_6m": num_late_payments_6m,
        "min_payment_missed": min_payment_missed, "avg_payment_ratio": avg_payment_ratio,
        "complaints_6m": complaints_6m, "complaint_resolved": complaint_resolved,
        "last_complaint_category": last_complaint_category, "nps_score": nps_score,
        "app_login_frequency": app_login_frequency, "competitor_offer_clicked": competitor_offer_clicked,
        "reward_points_balance": reward_points_balance, "email_open_rate": email_open_rate,
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
```

---

## 10. Phase 4 — Data Fetch Tool

**File:** `tools/data_fetch_tool.py`

**Purpose:** LangChain `@tool` that Agent 1 calls. Reads CSV, filters by signal, returns only relevant columns. Never sends the full 1000-row CSV to GPT.

**S3 vs Local logic:** Checks `AWS_ACCESS_KEY_ID` in `.env`. If filled, reads from S3. If placeholder, reads local CSV. Zero code changes needed when switching to production.

### Full Code

```python
import os
import io
import pandas as pd
import boto3
from pathlib import Path
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

BASE_COLS = ["customer_id", "age", "customer_segment", "tenure_months", "nps_score"]

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

SIGNAL_CONDITIONS = {
    "high_utilization":      lambda df: df[df["utilization_rate"] > 80],
    "inactivity":            lambda df: df[df["days_since_last_transaction"] > 30],
    "unresolved_complaints": lambda df: df[(df["complaints_6m"] > 0) & (df["complaint_resolved"] == "No")],
    "competitor_interest":   lambda df: df[df["competitor_offer_clicked"] == True],
    "spend_drop":            lambda df: df[df["spend_drop_pct"] < -40],
}


def _load_dataframe() -> pd.DataFrame:
    bucket = os.getenv("S3_BUCKET_NAME")
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
    if access_key and access_key != "your_aws_access_key_here" and bucket:
        s3 = boto3.client("s3")
        obj = s3.get_object(Bucket=bucket, Key="customer_data.csv")
        return pd.read_csv(io.BytesIO(obj["Body"].read()))
    local_path = os.path.join(os.path.dirname(__file__), "..", "data", "customer_data.csv")
    return pd.read_csv(local_path)


@tool
def fetch_customers_by_signal(signal: str) -> str:
    """
    Fetches filtered customer data for a given churn signal.
    Valid signals: high_utilization, inactivity, unresolved_complaints,
                   competitor_interest, spend_drop
    """
    if signal not in SIGNAL_CONDITIONS:
        return f"Unknown signal '{signal}'. Valid options: {list(SIGNAL_CONDITIONS.keys())}"
    df = _load_dataframe()
    filtered = SIGNAL_CONDITIONS[signal](df)
    if filtered.empty:
        return f"No customers flagged for signal: {signal}"
    cols = BASE_COLS + SIGNAL_COLS[signal]
    result = filtered[cols].to_string(index=False)
    return f"Signal: {signal}\nCustomers flagged: {len(filtered)}\n\n{result}"
```

---

## 11. Phase 5 — Signal Agent

**File:** `agents/signal_agent.py`

**Purpose:** Main analysis agent. Runs 5 signal prompts sequentially with shared memory, ends with cross-signal summary identifying customers who appear in multiple signals.

**Model:** GPT-4.1 via `langchain-openai`

**Live test result:**
- 46 customers flagged across multiple signals
- 6 customers hit 4 signals simultaneously (highest priority)
- Top customers: C0001, C0097, C0111, C0125, C0164, C0174
- Standard segment most at-risk overall

### Full Code

```python
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from pathlib import Path
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv

from tools.data_fetch_tool import fetch_customers_by_signal

load_dotenv(Path(__file__).parent.parent / ".env")

SIGNAL_PROMPTS = {
    "high_utilization": """
Use the fetch_customers_by_signal tool with signal='high_utilization'.
Analyze customers with credit utilization above 80%:
- Identify patterns across segment, tenure, and payment history
- Note which customers are closest to their credit limit
- List the top 10 highest-risk customers by utilization rate
Keep your response concise and data-driven.
""",
    "inactivity": """
Use the fetch_customers_by_signal tool with signal='inactivity'.
Analyze customers who have not transacted in over 30 days:
- Look for patterns in login frequency and account status
- Note how long the worst cases have been inactive
- List the top 10 most at-risk by days since last transaction
Keep your response concise and data-driven.
""",
    "unresolved_complaints": """
Use the fetch_customers_by_signal tool with signal='unresolved_complaints'.
Analyze customers with open unresolved complaints:
- Identify the most common complaint categories
- Flag customers with multiple complaints and low NPS scores
- List the top 10 most urgent cases
Keep your response concise and data-driven.
""",
    "competitor_interest": """
Use the fetch_customers_by_signal tool with signal='competitor_interest'.
Analyze customers who clicked competitor offers:
- Look for patterns in NPS score and engagement
- Identify which segments are most vulnerable
- List the top 10 highest defection-risk customers
Keep your response concise and data-driven.
""",
    "spend_drop": """
Use the fetch_customers_by_signal tool with signal='spend_drop'.
Analyze customers with a spending drop greater than 40%:
- Note the magnitude of drops and payment history patterns
- Look for customers whose drop aligns with other risk factors
- List the top 10 customers with the steepest declines
Keep your response concise and data-driven.
""",
}

SUMMARY_PROMPT = """
You have now analyzed all 5 churn signals across the customer portfolio.
Based on everything you found:

1. OVERLAP ANALYSIS
   Which customers appeared in more than one signal?
   For each: customer_id | signals triggered | total signal count

2. PRIORITY LIST
   Top 10 most at-risk customers ranked by number of signals triggered.
   For ties, prioritise by severity (unresolved complaint + competitor click = most severe).

3. PORTFOLIO SUMMARY
   - Total unique at-risk customers across all signals
   - Most common signal combinations
   - Which customer segment is most at risk overall
   - One-line recommended action per segment

Use the exact customer IDs from your analysis throughout.
"""


def run_signal_pipeline(thread_id: str | None = None) -> dict:
    if thread_id is None:
        thread_id = f"churn_run_{datetime.now().strftime('%Y%m%d_%H%M')}"

    llm = ChatOpenAI(model="gpt-4.1", api_key=os.getenv("OPENAI_API_KEY"))
    agent = create_agent(
        model=llm,
        tools=[fetch_customers_by_signal],
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": thread_id}}
    signal_responses = {}

    print(f"Starting pipeline — thread: {thread_id}")
    for signal_name, prompt in SIGNAL_PROMPTS.items():
        print(f"  Analysing: {signal_name}...")
        response = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config=config,
        )
        signal_responses[signal_name] = response["messages"][-1].content

    print("  Running cross-signal summary...")
    summary_response = agent.invoke(
        {"messages": [{"role": "user", "content": SUMMARY_PROMPT}]},
        config=config,
    )
    print("Pipeline complete.")

    return {
        "thread_id": thread_id,
        "run_timestamp": datetime.now().isoformat(),
        "signal_responses": signal_responses,
        "summary": summary_response["messages"][-1].content,
    }


if __name__ == "__main__":
    results = run_signal_pipeline()
    print("\n===== SUMMARY =====")
    print(results["summary"])
```

---

## 12. Phase 6 — Action Agent

**File:** `agents/action_agent.py`

**Purpose:** Takes the top 10 priority customers from signal pipeline results, fetches their profiles, writes personalised retention emails, sends them via SES, and initiates outbound calls via the existing call pipeline endpoint.

**Contact info approach:** Customer CSV has no email/phone columns (contact info belongs in a CRM, not an analytics CSV). The `get_customer_details` tool generates consistent fake contact info using Faker seeded by customer index. In production this would be a real CRM API call.

**Dev mode:** Both email and call tools simulate in dev mode when AWS/endpoint not configured. No code changes needed for production.

### Full Code

```python
import os
import sys
import json
import httpx
import boto3
import pandas as pd
from faker import Faker
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


@tool
def get_customer_details(customer_id: str) -> str:
    """Fetch the full profile for a customer by their ID."""
    local_path = os.path.join(os.path.dirname(__file__), "..", "data", "customer_data.csv")
    df = pd.read_csv(local_path)
    row = df[df["customer_id"] == customer_id]
    if row.empty:
        return f"Customer {customer_id} not found."
    index = int(customer_id.replace("C", ""))
    fake = Faker()
    Faker.seed(index)
    data = row.iloc[0].to_dict()
    data["email"] = fake.email()
    data["phone"] = fake.phone_number()
    return json.dumps(data, default=str)


@tool
def send_retention_email(customer_id: str, email: str, subject: str, body: str) -> str:
    """Send a personalised retention email via AWS SES."""
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "")
    if not access_key or access_key == "your_aws_access_key_here":
        return (
            f"[DEV] Email simulated for {customer_id}\n"
            f"  To: {email}\n  Subject: {subject}\n"
            f"  Body preview: {body[:120]}..."
        )
    ses = boto3.client("ses", region_name=os.getenv("AWS_REGION", "us-east-1"))
    ses.send_email(
        Source=os.getenv("SENDER_EMAIL"),
        Destination={"ToAddresses": [email]},
        Message={"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}},
    )
    return f"Email sent to {email} for customer {customer_id}"


@tool
def initiate_customer_call(customer_id: str, name: str, phone: str, context: str) -> str:
    """Trigger an outbound retention call via the existing call pipeline."""
    endpoint = os.getenv("CALL_PIPELINE_ENDPOINT", "")
    if not endpoint or endpoint == "your_call_pipeline_url_here":
        return (
            f"[DEV] Call simulated for {customer_id}\n"
            f"  Name: {name} | Phone: {phone}\n"
            f"  Context: {context[:120]}..."
        )
    response = httpx.post(endpoint, json={"name": name, "phone": phone, "context": context}, timeout=30)
    if response.status_code == 200:
        return f"Call initiated for {name} ({customer_id})"
    return f"Call failed for {customer_id}: HTTP {response.status_code}"


ACTION_PROMPT = """
You are a customer retention specialist. Take action on the TOP 10 priority customers.

For each customer:
1. Call get_customer_details with their customer_id
2. Write a warm personalised retention email (never mention "churn" or "at risk")
3. Call send_retention_email
4. Call initiate_customer_call with a 2-sentence context briefing

After all 10, give a summary table:
customer_id | signals | email sent | call initiated

PRIORITY LIST:
{priority_summary}
"""


def run_action_pipeline(signal_results: dict) -> dict:
    llm = ChatOpenAI(model="gpt-4.1", api_key=os.getenv("OPENAI_API_KEY"))
    agent = create_agent(
        model=llm,
        tools=[get_customer_details, send_retention_email, initiate_customer_call],
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": f"action_{signal_results['thread_id']}"}}
    prompt = ACTION_PROMPT.format(priority_summary=signal_results["summary"])

    print(f"Starting action pipeline — thread: {config['configurable']['thread_id']}")
    response = agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config=config,
    )
    print("Action pipeline complete.")
    return {
        "thread_id": config["configurable"]["thread_id"],
        "actions_taken": response["messages"][-1].content,
    }
```

---

## 13. Phase 7 — S3 Utils

**File:** `helpers/s3_utils.py`

**Purpose:** All S3 read/write operations. Every function has a dev mode fallback that uses the local `data/` folder when AWS credentials are not configured.

### Functions

| Function | Purpose |
|----------|---------|
| `upload_csv` | Uploads `customer_data.csv` to S3 at pipeline start |
| `save_pipeline_results` | Saves signal + action results as dated JSON |
| `get_latest_pipeline_results` | Fetches most recent run's JSON |
| `list_all_pipeline_results` | Returns metadata of all past runs (for history dropdown) |

### Full Code

```python
import os
import json
import boto3
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


def _get_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )


def _is_aws_configured() -> bool:
    key = os.getenv("AWS_ACCESS_KEY_ID", "")
    return bool(key and key != "your_aws_access_key_here")


def upload_csv(local_path: str, s3_key: str = "customer_data.csv") -> None:
    if not _is_aws_configured():
        print(f"[DEV] Skipping S3 upload — using local file: {local_path}")
        return
    bucket = os.getenv("S3_BUCKET_NAME")
    _get_client().upload_file(local_path, bucket, s3_key)
    print(f"Uploaded {local_path} to s3://{bucket}/{s3_key}")


def save_pipeline_results(results: dict) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    payload = json.dumps(results, indent=2, default=str)
    if not _is_aws_configured():
        local_out = os.path.join(os.path.dirname(__file__), "..", "data", f"pipeline_{timestamp}.json")
        with open(local_out, "w") as f:
            f.write(payload)
        print(f"[DEV] Results saved locally: {local_out}")
        return local_out
    s3_key = f"results/pipeline_{timestamp}.json"
    bucket = os.getenv("S3_BUCKET_NAME")
    _get_client().put_object(Bucket=bucket, Key=s3_key, Body=payload, ContentType="application/json")
    print(f"Results saved to s3://{bucket}/{s3_key}")
    return s3_key


def get_latest_pipeline_results() -> dict:
    if not _is_aws_configured():
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        files = sorted(
            [f for f in os.listdir(data_dir) if f.startswith("pipeline_") and f.endswith(".json")],
            reverse=True,
        )
        if not files:
            return {}
        with open(os.path.join(data_dir, files[0])) as f:
            return json.load(f)
    bucket = os.getenv("S3_BUCKET_NAME")
    s3 = _get_client()
    response = s3.list_objects_v2(Bucket=bucket, Prefix="results/pipeline_")
    objects = response.get("Contents", [])
    if not objects:
        return {}
    latest = sorted(objects, key=lambda x: x["LastModified"], reverse=True)[0]
    obj = s3.get_object(Bucket=bucket, Key=latest["Key"])
    return json.loads(obj["Body"].read())


def list_all_pipeline_results() -> list[dict]:
    if not _is_aws_configured():
        data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        files = sorted(
            [f for f in os.listdir(data_dir) if f.startswith("pipeline_") and f.endswith(".json")],
            reverse=True,
        )
        return [{"key": f, "timestamp": f.replace("pipeline_", "").replace(".json", "")} for f in files]
    bucket = os.getenv("S3_BUCKET_NAME")
    s3 = _get_client()
    response = s3.list_objects_v2(Bucket=bucket, Prefix="results/pipeline_")
    objects = response.get("Contents", [])
    return [
        {"key": obj["Key"], "timestamp": obj["LastModified"].isoformat()}
        for obj in sorted(objects, key=lambda x: x["LastModified"], reverse=True)
    ]
```

---

## 14. Phase 8 — FastAPI Routes

### models/schemas.py

```python
from pydantic import BaseModel
from typing import Optional


class PipelineResults(BaseModel):
    thread_id: str
    run_timestamp: str
    signal_responses: dict[str, str]
    summary: str


class RunHistoryItem(BaseModel):
    key: str
    timestamp: str


class ApproveRequest(BaseModel):
    thread_id: Optional[str] = None


class ApproveResponse(BaseModel):
    status: str
    message: str
    action_thread_id: str
```

### routers/insights.py

```python
from fastapi import APIRouter, HTTPException
from models.schemas import PipelineResults, RunHistoryItem
from helpers.s3_utils import get_latest_pipeline_results, list_all_pipeline_results

router = APIRouter(tags=["insights"])


@router.get("/insights", response_model=PipelineResults)
def get_latest_insights():
    """Returns most recent pipeline run results. Called by dashboard on load."""
    results = get_latest_pipeline_results()
    if not results:
        raise HTTPException(status_code=404, detail="No pipeline results found.")
    return results


@router.get("/insights/history", response_model=list[RunHistoryItem])
def get_insights_history():
    """Returns metadata for all past pipeline runs."""
    return list_all_pipeline_results()
```

### routers/actions.py

```python
from fastapi import APIRouter, BackgroundTasks, HTTPException
from models.schemas import ApproveRequest, ApproveResponse
from helpers.s3_utils import get_latest_pipeline_results, save_pipeline_results
from agents.action_agent import run_action_pipeline

router = APIRouter(tags=["actions"])


def _run_and_save(signal_results: dict):
    action_results = run_action_pipeline(signal_results)
    signal_results["action_results"] = action_results
    save_pipeline_results(signal_results)


@router.post("/approve", response_model=ApproveResponse)
def approve_and_initiate(request: ApproveRequest, background_tasks: BackgroundTasks):
    """
    Triggered by dashboard Approve button.
    Returns immediately (202 accepted), runs action pipeline in background.
    """
    signal_results = get_latest_pipeline_results()
    if not signal_results:
        raise HTTPException(status_code=404, detail="No pipeline results to approve.")
    background_tasks.add_task(_run_and_save, signal_results)
    return ApproveResponse(
        status="accepted",
        message="Action pipeline started. Emails and calls are being initiated.",
        action_thread_id=f"action_{signal_results.get('thread_id', 'unknown')}",
    )
```

### Test Results
```
Health              GET  /health          200 OK
Insights            GET  /api/insights    200 OK
History             GET  /api/insights/history  200 OK
Approve             POST /api/approve     200 OK (background task ran)
```

---

## 15. Remaining Phases

### Phase 9 — Lambda Handlers
- `lambda_handlers/lambda_insights.py` — wraps `run_signal_pipeline()` in Lambda handler
- `lambda_handlers/lambda_actions.py` — wraps `run_action_pipeline()` in Lambda handler
- Both packaged as zip files with all dependencies

### Phase 10 — React Frontend
- Vite + React
- Pages: Dashboard (signal cards + priority table + approve button), History
- Calls `GET /api/insights` on load
- Approve button calls `POST /api/approve`
- Framework/component library TBD (discussed when we start frontend)

### Phase 11 — AWS Setup (deferred to end)
Do all AWS setup in one go after all code is written:
1. Create AWS account + IAM user
2. Attach policies: S3, SNS, SES, Lambda, EventBridge, API Gateway
3. `aws configure` with access keys
4. Create S3 bucket: `churn-prevention-data`
5. Set up SNS topic for alerts
6. Verify sender email in SES
7. Deploy Lambda 1 + Lambda 2
8. Create API Gateway → Lambda 2
9. Set EventBridge cron: `cron(0 9 * * ? *)`
10. Fill `.env` with all real values
11. End-to-end test

### Phase 12 — End-to-End Test
1. Run `generate_dataset.py` → CSV generated
2. `upload_csv()` → CSV in S3
3. Invoke Lambda 1 manually → results in S3
4. Open React dashboard → data displays
5. Click Approve → emails + calls fire
6. Verify EventBridge triggers Lambda 1 at 9am next day

---

## 16. Environment Variables Reference

**File:** `backend/.env`

```env
# OPENAI
# Get from: https://platform.openai.com/api-keys
OPENAI_API_KEY=your_openai_api_key_here

# AWS CREDENTIALS
# Get from: AWS Console -> IAM -> Users -> Your User -> Security Credentials
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=us-east-1

# S3
# Create this bucket in: AWS Console -> S3
S3_BUCKET_NAME=churn-prevention-data

# SNS (Email Alerts to manager/team)
# Get from: AWS Console -> SNS -> Topics -> Your Topic -> ARN
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:YOUR_ACCOUNT_ID:churn-alerts

# SES (Sending emails to customers)
# Verify this email in: AWS Console -> SES -> Verified Identities
SENDER_EMAIL=your_verified_email@example.com

# CALL PIPELINE
# Your existing pipeline endpoint that takes name, phone, context
CALL_PIPELINE_ENDPOINT=your_call_pipeline_url_here

# API GATEWAY
# Get after Lambda deploy: AWS Console -> API Gateway -> Stages -> Invoke URL
API_GATEWAY_APPROVE_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/approve
```

---

## Progress Tracker

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Local environment setup | DONE |
| 2 | Dataset generation (1000×30) | DONE |
| 3 | AWS setup | DEFERRED TO END |
| 4 | Data fetch tool | DONE |
| 5 | Signal agent (GPT-4.1, 5 signals, memory) | DONE + LIVE TESTED |
| 6 | Action agent (email + calls) | DONE + LIVE TESTED |
| 7 | S3 utils | DONE |
| 8 | FastAPI routes | DONE + ALL ENDPOINTS TESTED |
| 9 | Lambda handlers | PENDING |
| 10 | React frontend | PENDING |
| 11 | AWS setup + deploy | PENDING |
| 12 | End-to-end test | PENDING |
