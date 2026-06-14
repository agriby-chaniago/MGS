from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase


class ReadOnlyBase(DeclarativeBase):
    """Semua model di sini TIDAK ikut create_all() — hanya untuk query."""
    pass


class Audit(ReadOnlyBase):
    __tablename__ = "audits"
    __table_args__ = {"schema": "audit_svc"}

    id                  = Column(UUID(as_uuid=True), primary_key=True)
    dataset_id          = Column(UUID(as_uuid=True))
    status              = Column(String(50))
    requested_analyzers = Column(JSONB)
    created_at          = Column(DateTime)
    completed_at        = Column(DateTime)


class AnalysisResult(ReadOnlyBase):
    __tablename__ = "analysis_results"
    __table_args__ = {"schema": "analysis_svc"}

    id             = Column(UUID(as_uuid=True), primary_key=True)
    audit_id       = Column(UUID(as_uuid=True), index=True)
    analyzer_type  = Column(String(50))
    status         = Column(String(50))
    result_payload = Column(JSONB)
    error_message  = Column(String)
    completed_at   = Column(DateTime)
