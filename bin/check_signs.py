import psycopg2

try:
    conn = psycopg2.connect(
        dbname="road_ai_db",
        user="postgres",
        password="Bisag@123",
        host="localhost",
        port="5433"
    )
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM road_defects WHERE defect_type = 'Traffic_Sign'")
    count = cursor.fetchone()[0]
    print(f"Total Traffic_Sign detections: {count}")
    
    if count > 0:
        print("\nSome examples:")
        cursor.execute("SELECT id, road_name, confidence, image_path FROM road_defects WHERE defect_type = 'Traffic_Sign' LIMIT 5")
        for row in cursor.fetchall():
            print(row)
            
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Error: {e}")
