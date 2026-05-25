from fastapi import APIRouter, BackgroundTasks, HTTPException
from models.schemas import ApproveRequest, ApproveResponse
from helpers.s3_utils import get_latest_pipeline_results, save_pipeline_results
from agents.action_agent import run_action_pipeline

router = APIRouter(tags=["actions"])


def _run_and_save(signal_results: dict):
    """Background task: runs action pipeline and saves results back to S3."""
    action_results = run_action_pipeline(signal_results)
    signal_results["action_results"] = action_results
    save_pipeline_results(signal_results)


@router.post("/approve", response_model=ApproveResponse)
def approve_and_initiate(request: ApproveRequest, background_tasks: BackgroundTasks):
    """
    Triggered by the dashboard Approve button.
    Fetches the latest pipeline results and kicks off the action pipeline
    — emails + calls — as a background task.
    Returns immediately so the UI does not hang.
    """
    signal_results = get_latest_pipeline_results()
    if not signal_results:
        raise HTTPException(
            status_code=404,
            detail="No pipeline results to approve.",
        )

    background_tasks.add_task(_run_and_save, signal_results)

    return ApproveResponse(
        status="accepted",
        message="Action pipeline started. Emails and calls are being initiated.",
        action_thread_id=f"action_{signal_results.get('thread_id', 'unknown')}",
    )