import os
import sys
import json
import httpx
import boto3
import pandas as pd
from faker import Faker
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


# ── Tool 1: Fetch customer details from CSV ──────────────────────────────────

@tool
def get_customer_details(customer_id: str) -> str:
    """
    Fetch the full profile for a customer by their ID.
    Returns their churn signals, segment, and contact details.
    """
    local_path = os.path.join(os.path.dirname(__file__), "..", "data", "customer_data.csv")
    df = pd.read_csv(local_path)
    row = df[df["customer_id"] == customer_id]

    if row.empty:
        return f"Customer {customer_id} not found."

    # Generate consistent fake contact info seeded by customer index
    # In production this would be a CRM lookup
    index = int(customer_id.replace("C", ""))
    fake = Faker()
    Faker.seed(index)
    email = fake.email()
    phone = fake.phone_number()

    data = row.iloc[0].to_dict()
    data["email"] = email
    data["phone"] = phone

    return json.dumps(data, default=str)


# ── Tool 2: Send retention email via AWS SES ─────────────────────────────────

@tool
def send_retention_email(customer_id: str, email: str, subject: str, body: str) -> str:
    """
    Send a personalised retention email to a customer via AWS SES.
    In dev mode (no AWS credentials), simulates the send.
    """
    access_key = os.getenv("AWS_ACCESS_KEY_ID", "")

    if not access_key or access_key == "your_aws_access_key_here":
        return (
            f"[DEV] Email simulated for {customer_id}\n"
            f"  To: {email}\n"
            f"  Subject: {subject}\n"
            f"  Body preview: {body[:120]}..."
        )

    ses = boto3.client("ses", region_name=os.getenv("AWS_REGION", "us-east-1"))
    ses.send_email(
        Source=os.getenv("SENDER_EMAIL"),
        Destination={"ToAddresses": [email]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": body}},
        },
    )
    return f"Email sent to {email} for customer {customer_id}"


# ── Tool 3: Initiate outbound call via your pipeline endpoint ─────────────────

@tool
def initiate_customer_call(customer_id: str, name: str, phone: str, context: str) -> str:
    """
    Trigger an outbound retention call via the existing call pipeline.
    Sends customer name, phone number, and call context to the endpoint.
    In dev mode (no endpoint configured), simulates the call.
    """
    endpoint = os.getenv("CALL_PIPELINE_ENDPOINT", "")

    if not endpoint or endpoint == "your_call_pipeline_url_here":
        return (
            f"[DEV] Call simulated for {customer_id}\n"
            f"  Name: {name} | Phone: {phone}\n"
            f"  Context: {context[:120]}..."
        )

    response = httpx.post(
        endpoint,
        json={"name": name, "phone": phone, "context": context},
        timeout=30,
    )

    if response.status_code == 200:
        return f"Call initiated for {name} ({customer_id})"
    return f"Call failed for {customer_id}: HTTP {response.status_code}"


# ── Action prompt ─────────────────────────────────────────────────────────────

ACTION_PROMPT = """
You are a customer retention specialist. The churn analysis pipeline has identified
at-risk customers. Your job is to take action on the TOP 10 priority customers.

For each customer work through these steps in order:
1. Call get_customer_details with their customer_id to get their full profile
2. Based on their specific signals, write a warm personalised retention email:
   - Subject: relevant but never mention "churn" or "at risk"
   - Body: acknowledge their situation, offer something specific to their signals
     (e.g. credit limit increase for high utilization, complaint resolution for complaints)
3. Call send_retention_email with the customer's email, your subject and body
4. Call initiate_customer_call with a 2-sentence context briefing for the call agent

After completing all 10 customers, give a summary table:
customer_id | signals | email sent | call initiated

PRIORITY LIST:
{priority_summary}
"""


# ── Main pipeline function ────────────────────────────────────────────────────

def run_action_pipeline(signal_results: dict) -> dict:
    llm = ChatOpenAI(
        model="gpt-4.1",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

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


if __name__ == "__main__":
    mock_results = {
        "thread_id": "churn_run_test",
        "summary": (
            "Top priority customers:\n"
            "1. C0001 - 4 signals: inactivity, competitor_interest, spend_drop, high_utilization\n"
            "2. C0097 - 4 signals: high_utilization, inactivity, competitor_interest, spend_drop\n"
            "3. C0111 - 4 signals: high_utilization, inactivity, competitor_interest, spend_drop\n"
        ),
    }
    result = run_action_pipeline(mock_results)
    print(result["actions_taken"])