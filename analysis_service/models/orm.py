from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from models.database import AnalysisBase, AuditWriteBase


class AnalysisResult(AnalysisBase):
    __tablename__ = "analysis_results"
    __table_args__ = {"schema": "analysis_svc"}

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    audit_id       = Column(UUID(as_uuid=True), nullable=False, index=True)
    analyzer_type  = Column(String(50), nullable=False)
    status         = Column(String(50), nullable=False)
    result_payload = Column(JSONB, nullable=True)
    error_message  = Column(Text, nullable=True)
    started_at     = Column(DateTime, nullable=True)
    completed_at   = Column(DateTime, nullable=True)


class AuditStatus(AuditWriteBase):
    __tablename__ = "audits"
    __table_args__ = {"schema": "audit_svc"}

    id     = Column(UUID(as_uuid=True), primary_key=True)
    status = Column(String(50))
