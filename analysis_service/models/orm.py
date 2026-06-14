from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from models.database import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    __table_args__ = {"schema": "analysis_svc"}

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    audit_id       = Column(UUID(as_uuid=True), nullable=False)
    analyzer_type  = Column(String, nullable=False)
    status         = Column(String, default="pending")
    result_payload = Column(JSONB, nullable=True)
    error_message  = Column(Text, nullable=True)
    completed_at   = Column(DateTime, nullable=True)
