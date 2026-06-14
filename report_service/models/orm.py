from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from models.database import ReadOnlyBase as Base


# Read-only mirror dari audit_svc.audits
# Jangan write ke tabel ini dari report_service
class Audit(Base):
    __tablename__ = "audits"
    __table_args__ = {"schema": "audit_svc"}

    id           = Column(UUID(as_uuid=True), primary_key=True)
    dataset_id   = Column(UUID(as_uuid=True))
    status       = Column(String)
    created_at   = Column(DateTime)
    completed_at = Column(DateTime, nullable=True)


# Read-only mirror dari analysis_svc.analysis_results
# Jangan write ke tabel ini dari report_service
class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    __table_args__ = {"schema": "analysis_svc"}

    id             = Column(UUID(as_uuid=True), primary_key=True)
    audit_id       = Column(UUID(as_uuid=True))
    analyzer_type  = Column(String)
    status         = Column(String)
    result_payload = Column(JSONB, nullable=True)
    error_message  = Column(Text, nullable=True)
    completed_at   = Column(DateTime, nullable=True)
