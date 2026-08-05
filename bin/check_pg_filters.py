import sys
import os
from datetime import datetime, timedelta

# Add the backend to sys.path
sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

import database
import models
from sqlalchemy import func

def check():
    db = next(database.get_db())
    try:
        # Check overall stats
        res = db.query(
            models.RoadDefect.state, 
            models.RoadDefect.road_name,
            func.count(models.RoadDefect.id)
        ).filter(models.RoadDefect.is_defect == True).group_by(models.RoadDefect.state, models.RoadDefect.road_name).all()
        
        print("\nDefects by State and Road Name:")
        for state, road, count in res:
            print(f"  State: {state}, Road: {road}, Count: {count}")

        # Check filter behavior
        # Example filters (Common ones in script)
        # Maybe "Gujarat" was the seed?
    finally:
        db.close()

if __name__ == "__main__":
    check()
