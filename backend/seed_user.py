"""
RoadPulse AI - Admin Seeding Script
Safely provisions the default administrator account using enterprise bcrypt password hashing.
"""

import sys
from pathlib import Path

# Add backend directory to path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.database import SessionLocal
from app.core.security import SecurityService
from app.models.user import User


def seed_admin(username: str = "admin", password: str = "AdminPassword123!") -> None:
    """Provisions or updates default administrator user account with bcrypt hash."""
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == username).first()
        hashed = SecurityService.get_password_hash(password)

        if admin:
            print(f"[INFO] Admin user '{username}' already exists. Updating credentials...")
            admin.password_hash = hashed
            admin.role = "admin"
            admin.is_active = True
        else:
            print(f"[INFO] Creating administrative user '{username}'...")
            admin = User(
                username=username,
                password_hash=hashed,
                role="admin",
                is_active=True,
            )
            db.add(admin)

        db.commit()
        print(f"[SUCCESS] Successfully seeded admin user (Username: {username})")
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Failed seeding admin account: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin()
