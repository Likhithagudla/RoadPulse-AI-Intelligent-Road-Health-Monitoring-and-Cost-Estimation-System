from pathlib import Path
import sqlite3
import os

db_path = str(Path(__file__).resolve().parent.parent / "backend/road_ai.db")
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Tables:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print(cursor.fetchall())
    
    print("\nRecent Defect Detections:")
    try:
        cursor.execute("SELECT id, road_name, defect_type, severity, confidence, timestamp, is_defect FROM road_defects ORDER BY timestamp DESC LIMIT 20")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
    except Exception as e:
        print(f"Error querying road_defects: {e}")
        
    conn.close()
