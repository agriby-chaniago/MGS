from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Any


class AnalysisResultSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    audit_id: UUID
    analyzer_type: str
    status: str
    result_payload: dict[str, Any] | None
    error_message: str | None
    completed_at: datetime | None
