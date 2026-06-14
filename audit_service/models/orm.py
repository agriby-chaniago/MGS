from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from models.database import AuditBase, ReadOnlyBase


class Audit(AuditBase):
    __tablename__ = "audits"
    __table_args__ = {"schema": "audit_svc"}

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id          = Column(UUID(as_uuid=True), nullable=False)
    status              = Column(String(50), default="pending")
    requested_analyzers = Column(JSONB, default=lambda: [
                              "corruption", "empty", "resolution",
                              "distribution", "phash"
                          ])
    created_at          = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at        = Column(DateTime, nullable=True)
    error_message       = Column(String, nullable=True)


class DatasetReadOnly(ReadOnlyBase):
    __tablename__ = "datasets"
    __table_args__ = {"schema": "dataset_svc"}

    id         = Column(UUID(as_uuid=True), primary_key=True)
    minio_path = Column(String)
    status     = Column(String)


class AnalysisResultReadOnly(ReadOnlyBase):
    __tablename__ = "analysis_results"
    __table_args__ = {"schema": "analysis_svc"}

    id            = Column(UUID(as_uuid=True), primary_key=True)
    audit_id      = Column(UUID(as_uuid=True), index=True)
    analyzer_type = Column(String(50))
    status        = Column(String(50))
