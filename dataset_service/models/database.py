import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "modelgate")
POSTGRES_USER = os.getenv("POSTGRES_USER", "modelgate")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "modelgate_secret")

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    f"?options=-csearch_path%3Ddataset_svc%2Cpublic"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS dataset_svc"))
        conn.execute(text(
            "ALTER TABLE IF EXISTS dataset_svc.datasets "
            "ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64)"
        ))
        conn.execute(text(
            "ALTER TABLE IF EXISTS dataset_svc.datasets "
            "ADD COLUMN IF NOT EXISTS user_id UUID"
        ))
        conn.commit()
    from models.orm import Dataset, DatasetClass  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
