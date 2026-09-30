from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.engine import Engine
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

# SQLite optimization pragmas: WAL mode, foreign keys, synchronous=NORMAL
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def migrate_sqlite_schema(bind_engine: Engine):
    """
    Safely adds missing columns to existing SQLite tables without wiping data.
    """
    if not str(bind_engine.url).startswith("sqlite"):
        return
    with bind_engine.connect() as conn:
        try:
            result = conn.execute(text("PRAGMA table_info(transactions)"))
            columns = [row[1] for row in result.fetchall()]
            if columns:
                if "needs_review" not in columns:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN needs_review BOOLEAN NOT NULL DEFAULT 0"))
                if "review_source" not in columns:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN review_source VARCHAR(32) NOT NULL DEFAULT 'auto'"))
                if "reviewed_at_utc" not in columns:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN reviewed_at_utc DATETIME"))
                conn.commit()
        except Exception:
            pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
