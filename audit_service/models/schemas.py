from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID


class AuditSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_id: UUID
    status: str
    created_at: datetime
    completed_at: datetime | None
