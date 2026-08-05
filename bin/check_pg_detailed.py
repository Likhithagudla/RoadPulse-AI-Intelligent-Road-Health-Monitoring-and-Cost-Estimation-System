import psycopg2
from datetime import datetime

try:
    conn = psycopg2.connect(
        dbname="road_ai_db",
        user="postgres",
        password="Bisag@123",
        host="localhost",
        port="5433"
    )
    cursor = conn.cursor()
    
    print("Most Recent Detections with Image Paths:")
    cursor.execute("SELECT id, road_name, defect_type, severity, confidence, timestamp, is_defect, image_path FROM road_defects ORDER BY timestamp DESC LIMIT 50")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
        
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error connecting to PostgreSQL: {e}")
