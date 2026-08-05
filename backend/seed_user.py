
import os
import sys
import hashlib
from sqlalchemy.orm import Session

# Add current dir to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import models
import database

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def seed_admin():
    db = database.SessionLocal()
    try:
        # Check if admin already exists
        admin = db.query(models.User).filter(models.User.username == "admin").first()
        if admin:
            print("Admin user already exists. Updating password...")
            admin.password_hash = hash_password("admin123")
        else:
            print("Creating admin user...")
            new_admin = models.User(
                username="admin",
                password_hash=hash_password("admin123")
            )
            db.add(new_admin)
        
        db.commit()
        print("Successfully seeded admin user (Username: admin, Password: admin123)")
    except Exception as e:
        print(f"Error seeding user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
