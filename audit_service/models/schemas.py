from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID


class CreateAuditRequest(BaseModel):
    dataset_id: UUID


class AuditSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                  UUID
    dataset_id:          UUID
    status:              str
    requested_analyzers: list[str]
    created_at:          datetime
    completed_at:        datetime | None
    error_message:       str | None
