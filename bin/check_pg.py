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
    
    print("Recent detections in PostgreSQL:")
    cursor.execute("SELECT id, road_name, defect_type, severity, confidence, timestamp, is_defect FROM road_defects ORDER BY timestamp DESC LIMIT 20")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
        
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error connecting to PostgreSQL: {e}")
