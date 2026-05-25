from pydantic import BaseModel
from typing import Optional


class PipelineResults(BaseModel):
    thread_id: str
    run_timestamp: str
    signal_responses: dict[str, str]
    signal_counts: dict[str, int] = {}
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