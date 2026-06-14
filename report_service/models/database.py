import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER', 'modelgate')}:{os.getenv('POSTGRES_PASSWORD', 'modelgate_secret')}"
    f"@{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'modelgate')}"
    f"?options=-csearch_path%3Dreport_svc%2Caudit_svc%2Canalysis_svc%2Cpublic"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS report_svc"))
        conn.commit()
    # Tidak perlu create_all() — report_service tidak punya tabel sendiri


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
