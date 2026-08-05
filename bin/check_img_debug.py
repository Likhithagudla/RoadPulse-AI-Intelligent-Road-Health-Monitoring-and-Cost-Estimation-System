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
    
    img_name = '25ca08a5.jpg'
    print(f"Detections for {img_name}:")
    cursor.execute("SELECT id, defect_type, severity, confidence, timestamp, image_path FROM road_defects WHERE image_path LIKE %s", (f"%{img_name}%",))
    rows = cursor.fetchall()
    for row in rows:
        print(row)
        
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error connecting to PostgreSQL: {e}")
