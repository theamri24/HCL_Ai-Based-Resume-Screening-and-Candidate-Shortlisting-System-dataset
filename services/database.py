"""
services/database.py
SQLAlchemy engine + session + helpers.
Auto-detects: local (.env exists) → MySQL; cloud (.env missing) → SQLite.
"""

import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
SQLITE_DB = BASE_DIR / "resume_screening.db"

# ------------------------------------------------------------
# Detect environment
# ------------------------------------------------------------
if ENV_FILE.exists():
    # Local development → MySQL
    load_dotenv(ENV_FILE)
    DATABASE_URL = os.getenv("DATABASE_URL")
    DB_TYPE = "mysql"
    if not DATABASE_URL:
        # fallback
        DATABASE_URL = f"sqlite:///{SQLITE_DB}"
        DB_TYPE = "sqlite"
else:
    # Cloud (Streamlit Cloud) → SQLite
    DATABASE_URL = f"sqlite:///{SQLITE_DB}"
    DB_TYPE = "sqlite"


# ------------------------------------------------------------
# SQLAlchemy engine
# ------------------------------------------------------------
if DB_TYPE == "sqlite":
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
        future=True,
    )
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
        future=True,
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False,
                            autocommit=False, expire_on_commit=False)
Base = declarative_base()


# ------------------------------------------------------------
# Session
# ------------------------------------------------------------
@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def test_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as e:
        raise RuntimeError(f"Database connection failed: {e}")


def fetch_all(sql: str, params: dict | None = None):
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        return [dict(r._mapping) for r in result]


def fetch_one(sql: str, params: dict | None = None):
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        row = result.fetchone()
        return dict(row._mapping) if row else None


def execute(sql: str, params: dict | None = None):
    with engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        return result.lastrowid


# ------------------------------------------------------------
# SQLite schema (auto-created on cloud)
# ------------------------------------------------------------
SQLITE_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'hr',
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        required_skills TEXT NOT NULL,
        minimum_experience INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
    )""",
    """CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT,
        education TEXT,
        experience REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,
        original_filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_type TEXT,
        extracted_text TEXT,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES candidates(id),
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    )""",
    """CREATE TABLE IF NOT EXISTS skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill_name TEXT NOT NULL UNIQUE,
        category TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS candidate_skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_id INTEGER NOT NULL,
        skill_id INTEGER NOT NULL,
        resume_id INTEGER,
        FOREIGN KEY (candidate_id) REFERENCES candidates(id),
        FOREIGN KEY (skill_id) REFERENCES skills(id),
        UNIQUE (candidate_id, skill_id)
    )""",
    """CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resume_id INTEGER NOT NULL,
        job_id INTEGER NOT NULL,
        candidate_id INTEGER NOT NULL,
        resume_score REAL NOT NULL,
        skill_match_percentage REAL DEFAULT 0,
        similarity_score REAL DEFAULT 0,
        matched_skills TEXT,
        missing_skills TEXT,
        decision TEXT DEFAULT 'Review',
        model_version TEXT DEFAULT 'v1',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (resume_id) REFERENCES resumes(id),
        FOREIGN KEY (job_id) REFERENCES jobs(id),
        FOREIGN KEY (candidate_id) REFERENCES candidates(id)
    )""",
]

DEFAULT_SKILLS = [
    ("Python", "Programming"), ("Java", "Programming"), ("C++", "Programming"),
    ("JavaScript", "Programming"), ("SQL", "Database"), ("MySQL", "Database"),
    ("MongoDB", "Database"), ("Machine Learning", "AI/ML"), ("Deep Learning", "AI/ML"),
    ("NLP", "AI/ML"), ("TensorFlow", "AI/ML"), ("PyTorch", "AI/ML"),
    ("Scikit-learn", "AI/ML"), ("Pandas", "Data"), ("NumPy", "Data"),
    ("OpenCV", "AI/ML"), ("Docker", "DevOps"), ("Git", "DevOps"),
    ("AWS", "Cloud"), ("React", "Frontend"), ("Node.js", "Backend"),
    ("Django", "Backend"), ("Flask", "Backend"), ("Streamlit", "Frontend"),
]


def init_sqlite_db():
    """Create tables and seed defaults — only for SQLite."""
    if DB_TYPE != "sqlite":
        return

    with engine.begin() as conn:
        for stmt in SQLITE_SCHEMA:
            conn.execute(text(stmt))

    # Seed skills if empty
    count = fetch_one("SELECT COUNT(*) AS c FROM skills")
    if count and count["c"] == 0:
        for name, cat in DEFAULT_SKILLS:
            try:
                execute(
                    "INSERT INTO skills (skill_name, category) VALUES (:n, :c)",
                    {"n": name, "c": cat},
                )
            except Exception:
                pass


# ------------------------------------------------------------
# Auto-init on import (safe, idempotent)
# ------------------------------------------------------------
try:
    init_sqlite_db()
except Exception as e:
    print(f"[db init warning] {e}")


# ------------------------------------------------------------
# CLI test
# ------------------------------------------------------------
if __name__ == "__main__":
    print(f"DB_TYPE: {DB_TYPE}")
    print(f"DATABASE_URL: {DATABASE_URL}")
    try:
        test_connection()
        print("Database connection OK")
        tables = fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table'"
            if DB_TYPE == "sqlite" else "SHOW TABLES"
        )
        print("Tables:")
        for t in tables:
            print("  -", list(t.values())[0])
    except Exception as e:
        print("FAIL:", e)