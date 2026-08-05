
import sys
import os
from datetime import datetime
import random

# Add backend to path
sys.path.append(r'd:\Road_AI_Project\backend')

try:
    import models
    import database
    from sqlalchemy.orm import Session
except ImportError:
    print("Error: Could not import backend modules. Ensure you are in the project root.")
    sys.exit(1)

def add_repairs():
    db = database.SessionLocal()
    try:
        # Get some existing roads to attach repairs to
        roads = db.query(models.Road).limit(3).all()
        if not roads:
            print("No roads found in database. Please run seed_data.py first.")
            return

        repair_types = ["Repaired_Pothole", "Crack_Repair", "Surface_Repair"]
        
        print(f"Adding repair records to {len(roads)} roads...")
        
        for road in roads:
            # Add 2-4 repairs per road
            for _ in range(random.randint(2, 4)):
                repair = models.RoadDefect(
                    road_name=road.road_name,
                    road_id=road.road_id,
                    state=road.state,
                    latitude=road.start_latitude if road.start_latitude else 23.0,
                    longitude=road.start_longitude if road.start_longitude else 72.0,
                    defect_type=random.choice(repair_types),
                    severity="Low", # Repairs are usually low severity/safe
                    confidence=0.99,
                    estimated_area_sqm=random.uniform(0.5, 2.5),
                    repair_cost=random.uniform(2000, 8000), # This is the "cost spent"
                    repair_description="Verified repair work",
                    is_defect=True, # We keep it true so it shows in stats
                    timestamp=datetime.utcnow()
                )
                db.add(repair)
        
        db.commit()
        print("Successfully added repair records! Refresh your dashboard to see the 'Repaired Roads' section populated.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_repairs()
