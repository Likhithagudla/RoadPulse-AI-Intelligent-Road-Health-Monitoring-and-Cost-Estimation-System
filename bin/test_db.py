
import psycopg2
from urllib.parse import urlparse

db_url = "postgresql://postgres:Bisag%40123@localhost:5433/road_ai_db"
result = urlparse(db_url)
username = result.username
password = result.password or ""
database = result.path[1:]
hostname = result.hostname
port = result.port

try:
    conn = psycopg2.connect(
        database=database,
        user=username,
        password=password,
        host=hostname,
        port=port
    )
    print("Successfully connected to the database!")
    cur = conn.cursor()
    cur.execute("SELECT 1")
    print("Query executed successfully!")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Failed to connect: {e}")
