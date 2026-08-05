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
    
    print("Recent actual defects with image paths:")
    cursor.execute("SELECT id, defect_type, severity, confidence, timestamp, image_path FROM road_defects WHERE is_defect = True AND image_path IS NOT NULL ORDER BY timestamp DESC LIMIT 20")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
        
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error connecting to PostgreSQL: {e}")
