"""
RoadPulse AI - Database Reset Utility
Drops and recreates all database tables. For development and testing environments only.
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import engine, Base


def reset_db() -> None:
    """Drops and regenerates all database schema tables."""
    print("[WARN] Resetting database...")
    Base.metadata.drop_all(bind=engine)
    print("[INFO] Dropped all existing tables.")
    Base.metadata.create_all(bind=engine)
    print("[SUCCESS] Successfully recreated all database tables.")


if __name__ == "__main__":
    reset_db()
