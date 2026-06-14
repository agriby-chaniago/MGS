from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Any


class AnalysisResultSummary(BaseModel):
    analyzer_type: str
    status: str
    result_payload: dict[str, Any] | None
    completed_at: datetime | None


class ReportSchema(BaseModel):
    audit_id: UUID
    dataset_id: UUID
    health_score: float | None
    status: str
    analysis_results: list[AnalysisResultSummary]
    created_at: datetime


class ReportSummarySchema(BaseModel):
    audit_id: UUID
    health_score: float | None
    grade: str | None
    status: str
