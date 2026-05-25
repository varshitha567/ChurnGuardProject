import os
import sys
import json
sys.path.insert(0, "/var/task")

from agents.signal_agent import run_signal_pipeline
from helpers.s3_utils import upload_csv, save_pipeline_results


def handler(event, context):
    """
    Lambda 1 — triggered by EventBridge at 9am daily.
    Runs the 5-signal churn analysis and saves results to S3.
    """
    try:
        local_csv = os.path.join(os.path.dirname(__file__), "..", "data", "customer_data.csv")
        upload_csv(local_csv)

        results = run_signal_pipeline()
        s3_key = save_pipeline_results(results)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Pipeline completed",
                "thread_id": results["thread_id"],
                "s3_key": s3_key,
            }),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }