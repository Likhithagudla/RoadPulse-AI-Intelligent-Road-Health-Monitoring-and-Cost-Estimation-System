
import os
import sys
import random
from datetime import datetime
from sqlalchemy.orm import Session

# Add current dir to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import models
import database

def seed():
    db = database.SessionLocal()
    try:
        # 1. Clear existing data
        db.query(models.RoadDefect).delete()
        db.query(models.Road).delete()
        db.query(models.Survey).delete()
        db.commit()

        # States with rough central coordinates
        states_data = {
            "Andhra Pradesh": (15.9129, 79.7400),
            "Arunachal Pradesh": (28.2180, 94.7278),
            "Assam": (26.2006, 92.9376),
            "Bihar": (25.0961, 85.3131),
            "Chhattisgarh": (21.2787, 81.8661),
            "Goa": (15.2993, 74.1240),
            "Gujarat": (22.2587, 71.1924),
            "Haryana": (29.0588, 76.0856),
            "Himachal Pradesh": (31.1048, 77.1734),
            "Jharkhand": (23.6102, 85.2799),
            "Karnataka": (15.3173, 75.7139),
            "Kerala": (10.8505, 76.2711),
            "Madhya Pradesh": (22.9734, 78.6569),
            "Maharashtra": (19.7515, 75.7139),
            "Manipur": (24.6637, 93.9063),
            "Meghalaya": (25.4670, 91.3662),
            "Mizoram": (23.1645, 92.9376),
            "Nagaland": (26.1584, 94.5624),
            "Odisha": (20.9517, 85.0985),
            "Punjab": (31.1471, 75.3412),
            "Rajasthan": (27.0238, 74.2179),
            "Sikkim": (27.5330, 88.5122),
            "Tamil Nadu": (11.1271, 78.6569),
            "Telangana": (18.1124, 79.0193),
            "Tripura": (23.9408, 91.9882),
            "Uttar Pradesh": (26.8467, 80.9462),
            "Uttarakhand": (30.0668, 79.0193),
            "West Bengal": (22.9868, 87.8550),
            "Andaman and Nicobar Islands": (11.7401, 92.6586),
            "Chandigarh": (30.7333, 76.7794),
            "Dadra and Nagar Haveli and Daman and Diu": (20.1809, 73.0169),
            "Delhi": (28.6139, 77.2090),
            "Jammu and Kashmir": (33.7782, 76.5762),
            "Ladakh": (34.1526, 77.5771),
            "Lakshadweep": (10.5667, 72.6417),
            "Puducherry": (11.9416, 79.8083)
        }

        defect_types = ["pothole", "alligator_cracking", "edge_cracking", "rutting", "raveling", "repaired_pothole", "crack_repair"]
        severities = ["Low", "Medium", "High"]

        new_roads = []
        new_surveys = []
        new_defects = []

        road_types_list = ["NH", "SH", "VR"]
        
        for idx, (state, (lat, lng)) in enumerate(states_data.items()):
            state_tag = state.replace(" ", "").upper()[:5]
            
            for road_type in road_types_list:
                road_id = f"RD-{state_tag}-{road_type}-{idx:02d}"
                road_name = f"{state} {road_type} Road"
                
                road = models.Road(
                    road_id=road_id,
                    road_name=road_name,
                    road_type=road_type,
                    district="Main District",
                    state=state,
                    total_length_km=random.uniform(10, 100),
                    overall_condition=random.choice(["Good", "Average", "Bad"])
                )
                new_roads.append(road)
                
                # Create a survey for this road
                survey = models.Survey(
                    road_name=road_name,
                    surveyor_name="Auto Seeder",
                    status="completed"
                )
                new_surveys.append(survey)
                db.add(survey)
                db.flush() # To get the survey ID

                # Add 2-3 defects per road type per state
                count = random.randint(2, 3)
                for i in range(count):
                    # Spread markers slightly
                    dlat = random.uniform(-0.1, 0.1)
                    dlng = random.uniform(-0.1, 0.1)
                    
                    defect = models.RoadDefect(
                        road_name=road_name,
                        state=state,
                        latitude=lat + dlat,
                        longitude=lng + dlng,
                        defect_type=random.choice(defect_types),
                        severity=random.choice(severities),
                        confidence=random.uniform(0.7, 0.98),
                        repair_cost=random.uniform(500, 5000),
                        survey_id=survey.id,
                        timestamp=datetime.utcnow()
                    )
                    new_defects.append(defect)

        db.add_all(new_roads)
        db.add_all(new_defects)
        db.commit()

        print("Successfully seeded sample data!")
        print(f"Added {len(new_roads)} roads, {len(new_surveys)} surveys, and {len(new_defects)} defects.")
        print("Data added for all 36 Indian States and Union Territories.")

    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
