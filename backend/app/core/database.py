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
                if "is_split" not in columns:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN is_split BOOLEAN NOT NULL DEFAULT 0"))
                if "my_share_paise" not in columns:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN my_share_paise BIGINT"))
                if "reimbursable_paise" not in columns:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN reimbursable_paise BIGINT NOT NULL DEFAULT 0"))
                if "split_ratio_label" not in columns:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN split_ratio_label VARCHAR(32)"))
                if "location_lat" not in columns:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN location_lat FLOAT"))
                if "location_lng" not in columns:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN location_lng FLOAT"))
                if "location_name" not in columns:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN location_name VARCHAR(256)"))
                if "location_address" not in columns:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN location_address VARCHAR(512)"))
                conn.commit()

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(64) UNIQUE NOT NULL,
                    color VARCHAR(32) NOT NULL DEFAULT '#6366F1',
                    icon VARCHAR(32) NOT NULL DEFAULT '🏷️',
                    description VARCHAR(256),
                    start_date DATETIME,
                    end_date DATETIME,
                    auto_tag_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS transaction_tags (
                    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                    created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (transaction_id, tag_id)
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tag_exclusions (
                    transaction_id INTEGER NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
                    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
                    created_at_utc DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (transaction_id, tag_id)
                )
            """))
            conn.commit()
        except Exception:
            pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
