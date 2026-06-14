from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from models.database import Base


class Audit(Base):
    __tablename__ = "audits"
    __table_args__ = {"schema": "audit_svc"}

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id   = Column(UUID(as_uuid=True), nullable=False)
    status       = Column(String, default="pending")
    created_at   = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
