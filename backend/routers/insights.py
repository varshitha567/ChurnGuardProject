from fastapi import APIRouter, HTTPException, BackgroundTasks
from models.schemas import PipelineResults, RunHistoryItem
from helpers.s3_utils import get_latest_pipeline_results, list_all_pipeline_results, save_pipeline_results

router = APIRouter(tags=["insights"])


def _run_and_save():
    from agents.signal_agent import run_signal_pipeline
    results = run_signal_pipeline()
    save_pipeline_results(results)


@router.post("/run")
def trigger_pipeline(background_tasks: BackgroundTasks):
    """
    Manually trigger a fresh signal pipeline run.
    Returns immediately — results appear in /api/insights once complete (2-3 min).
    """
    background_tasks.add_task(_run_and_save)
    return {"status": "started", "message": "Pipeline is running. Refresh in 2-3 minutes to see results."}


@router.get("/insights", response_model=PipelineResults)
def get_latest_insights():
    """
    Returns the most recent pipeline run results.
    React dashboard calls this on load to populate all panels.
    """
    results = get_latest_pipeline_results()
    if not results:
        raise HTTPException(
            status_code=404,
            detail="No pipeline results found. Run the pipeline first.",
        )
    return results


@router.get("/insights/history", response_model=list[RunHistoryItem])
def get_insights_history():
    """
    Returns metadata for all past pipeline runs.
    Used by the dashboard run history dropdown.
    """
    return list_all_pipeline_results()