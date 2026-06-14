from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from models.database import Base


class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = {"schema": "dataset_svc"}

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name         = Column(String, nullable=False)
    status       = Column(String, default="active")
    class_count  = Column(Integer)
    total_images = Column(Integer)
    file_size_mb = Column(Float)
    minio_path   = Column(String)
    created_at   = Column(DateTime, default=datetime.utcnow)

    classes      = relationship("DatasetClass", back_populates="dataset")


class DatasetClass(Base):
    __tablename__ = "dataset_classes"
    __table_args__ = {"schema": "dataset_svc"}

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    dataset_id  = Column(UUID(as_uuid=True), ForeignKey("dataset_svc.datasets.id"))
    class_name  = Column(String)
    image_count = Column(Integer)

    dataset     = relationship("Dataset", back_populates="classes")
