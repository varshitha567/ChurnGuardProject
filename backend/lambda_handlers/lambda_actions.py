import os
import sys
import json
sys.path.insert(0, "/var/task")

from agents.action_agent import run_action_pipeline
from helpers.s3_utils import get_latest_pipeline_results, save_pipeline_results


def handler(event, context):
    """
    Lambda 2 — triggered by API Gateway when manager clicks Approve.
    Reads latest signal results from S3 and fires retention emails + calls.
    """
    try:
        signal_results = get_latest_pipeline_results()

        if not signal_results:
            return {
                "statusCode": 404,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "No pipeline results found. Run the insights pipeline first."}),
            }

        action_results = run_action_pipeline(signal_results)
        save_pipeline_results(action_results)

        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "status": "actions_completed",
                "action_thread_id": action_results["thread_id"],
                "summary": action_results["actions_taken"][:500],
            }),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)}),
        }