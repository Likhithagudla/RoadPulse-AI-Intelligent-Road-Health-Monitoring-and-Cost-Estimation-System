import sqlite3
import os
from datetime import datetime, timedelta

db_path = 'D:/Road_AI_Project/backend/road_ai.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check table existence
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='road_defects'")
if not cur.fetchone():
    print("Table 'road_defects' does not exist!")
    conn.close()
    exit(1)

# Check total defects
cur.execute("SELECT COUNT(*) FROM road_defects")
total = cur.fetchone()[0]
print(f"Total rows in road_defects: {total}")

cur.execute("SELECT COUNT(*) FROM road_defects WHERE is_defect=1")
defects = cur.fetchone()[0]
print(f"Total defects (is_defect=1): {defects}")

# Timestamp range
cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM road_defects WHERE is_defect=1")
row = cur.fetchone()
print(f"Earliest defect timestamp: {row[0]}")
print(f"Latest defect timestamp: {row[1]}")

# Current time
now = datetime.utcnow()
print(f"Current UTC time: {now}")

# Check last 30 days
thirty_days_ago = now - timedelta(days=30)
print(f"30 days ago filter: {thirty_days_ago.strftime('%Y-%m-%d %H:%M:%S')}")

cur.execute("SELECT COUNT(*) FROM road_defects WHERE is_defect=1 AND timestamp >= ?", (thirty_days_ago.strftime('%Y-%m-%d %H:%M:%S'),))
recent = cur.fetchone()[0]
print(f"Defects in last 30 days (according to SQL filter): {recent}")

# Show some actual timestamps to see format
cur.execute("SELECT timestamp FROM road_defects WHERE is_defect=1 ORDER BY timestamp DESC LIMIT 5")
rows = cur.fetchall()
print("Top 5 latest timestamps in DB:")
for r in rows:
    print(f"  {r[0]}")

conn.close()
