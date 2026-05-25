import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from tools.data_fetch_tool import fetch_customers_by_signal, _load_dataframe, SIGNAL_CONDITIONS

load_dotenv()

# ── Prompt for each signal ──────────────────────────────────────────────────

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

# ── Final summary prompt — runs after all 5 signals ─────────────────────────

SUMMARY_PROMPT = """
You have now analyzed all 5 churn signals across the customer portfolio:
1. high_utilization
2. inactivity
3. unresolved_complaints
4. competitor_interest
5. spend_drop

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


# ── Main pipeline function ───────────────────────────────────────────────────

def run_signal_pipeline(thread_id: str | None = None) -> dict:
    if thread_id is None:
        thread_id = f"churn_run_{datetime.now().strftime('%Y%m%d_%H%M')}"

    llm = ChatOpenAI(
        model="gpt-4.1",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    agent = create_agent(
        model=llm,
        tools=[fetch_customers_by_signal],
        checkpointer=InMemorySaver(),
    )

    config = {"configurable": {"thread_id": thread_id}}
    signal_responses = {}

    print(f"Starting pipeline — thread: {thread_id}")

    # 5 signals sequentially — same thread_id maintains memory across all
    for signal_name, prompt in SIGNAL_PROMPTS.items():
        print(f"  Analysing: {signal_name}...")
        response = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config=config,
        )
        signal_responses[signal_name] = response["messages"][-1].content

    # Summary — agent has full context of all 5 signals in memory
    print("  Running cross-signal summary...")
    summary_response = agent.invoke(
        {"messages": [{"role": "user", "content": SUMMARY_PROMPT}]},
        config=config,
    )

    print("Pipeline complete.")

    df = _load_dataframe()
    signal_counts = {s: len(cond(df)) for s, cond in SIGNAL_CONDITIONS.items()}

    return {
        "thread_id": thread_id,
        "run_timestamp": datetime.now().isoformat(),
        "signal_responses": signal_responses,
        "signal_counts": signal_counts,
        "summary": summary_response["messages"][-1].content,
    }


if __name__ == "__main__":
    results = run_signal_pipeline()
    print("\n===== SUMMARY =====")
    print(results["summary"])