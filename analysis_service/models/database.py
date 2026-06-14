import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER', 'modelgate')}:{os.getenv('POSTGRES_PASSWORD', 'modelgate_secret')}"
    f"@{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'modelgate')}"
    f"?options=-csearch_path%3Danalysis_svc%2Caudit_svc%2Cpublic"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class AnalysisBase(DeclarativeBase):
    """Tabel milik analysis_service. Ikut create_all()."""
    pass


class AuditWriteBase(DeclarativeBase):
    """Write access ke audit_svc. TIDAK ikut create_all()."""
    pass


def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS analysis_svc"))
        conn.commit()
    from models.orm import AnalysisResult  # noqa: F401
    AnalysisBase.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
