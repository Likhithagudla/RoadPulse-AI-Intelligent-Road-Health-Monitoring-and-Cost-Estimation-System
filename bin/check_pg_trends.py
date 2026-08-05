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
        total_defects = db.query(models.RoadDefect).filter(models.RoadDefect.is_defect == True).count()
        print(f"Total defects (is_defect=True): {total_defects}")

        if total_defects == 0:
            print("NO defects found with is_defect=True!")
            return

        # Check timestamp range
        earliest = db.query(func.min(models.RoadDefect.timestamp)).filter(models.RoadDefect.is_defect == True).scalar()
        latest = db.query(func.max(models.RoadDefect.timestamp)).filter(models.RoadDefect.is_defect == True).scalar()
        print(f"Earliest defect timestamp: {earliest}")
        print(f"Latest defect timestamp: {latest}")

        # Current time
        now = datetime.utcnow()
        print(f"Current UTC time: {now}")

        # Check last 30 days
        thirty_days_ago = now - timedelta(days=30)
        print(f"30 days ago filter: {thirty_days_ago}")

        recent = db.query(models.RoadDefect).filter(
            models.RoadDefect.is_defect == True,
            models.RoadDefect.timestamp >= thirty_days_ago
        ).count()
        print(f"Defects in last 30 days: {recent}")

        # Show actual distribution of timestamps
        # Use simple counts by date
        # Note: func.date() works in PostgreSQL/SQLite
        all_dates = db.query(
            func.date(models.RoadDefect.timestamp).label('date'),
            func.count(models.RoadDefect.id).label('count')
        ).filter(models.RoadDefect.is_defect == True).group_by('date').order_by('date').all()
        
        print("\nAll defect dates with counts:")
        for date, count in all_dates:
            print(f"  {date}: {count} defects")

    finally:
        db.close()

if __name__ == "__main__":
    check()
