import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Ensure sys.path includes backend and root directories for seamless IDE module resolution
backend_dir = Path(__file__).resolve().parent
project_root = backend_dir.parent
for p in (str(backend_dir), str(project_root)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from backend.config import settings
except ImportError:
    from config import settings

# SQLite requires check_same_thread=False for multi-threaded FastAPI handlers
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency for providing a database session per HTTP request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes database tables defined in SQLAlchemy models."""
    try:
        from backend import models
    except ImportError:
        import models
    Base.metadata.create_all(bind=engine)


