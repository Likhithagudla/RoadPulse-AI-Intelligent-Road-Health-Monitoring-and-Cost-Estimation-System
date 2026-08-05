
import os
import sys

# Add current dir to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import models
import database

def reset_db():
    print("Resetting database...")
    # Drop all tables
    models.Base.metadata.drop_all(bind=database.engine)
    print("Dropped all tables.")
    # Create all tables
    models.Base.metadata.create_all(bind=database.engine)
    print("Created all tables.")

if __name__ == "__main__":
    reset_db()
