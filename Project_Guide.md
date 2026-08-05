# 🛣️ RoadPulse AI — Project Guide

This guide explains the **RoadPulse AI** project in simple English, covering the **Why, What, How, Where, and When**.

---

## 1. WHY was this project built? (The Purpose)
Roads are the veins of a country. When roads have potholes or cracks, two bad things happen:
1.  **Accidents**: People get hurt.
2.  **Money Loss**: Small cracks turn into big holes, which are very expensive to fix later.

**The Problem**: Usually, humans have to drive around and look for potholes. This is slow, boring, and humans miss things.
**The Solution**: RoadPulse AI uses a computer "Brain" to find these problems automatically and instantly.

---

## 2. WHAT is it? (The Product)
RoadPulse AI is an **Intelligent Road Assessment System**. 
- It is a website (Dashboard) that shows a map of the city.
- It is an AI tool that can look at a video of a road and say: *"There is a pothole at this exact GPS location, and it will cost ₹500 to fix."*

### Key Features:
- **Automatic Detection**: Finds 14 types of road issues (Potholes, Cracks, Manholes, etc.).
- **Cost Calculation**: It uses a "Schedule of Rates" (SOR) to tell you the price of the repair.
- **GPS Mapping**: Every defect is put on a map so you can see where the road is "sick."
- **Condition Grading**: It tells you if a road is **Good**, **Average**, or **Bad**.

---

## 3. HOW does it work? (The Technology)
Think of the project as a human body:

| Part | Technical Name | Simple Role |
| :--- | :--- | :--- |
| **The Brain** | AI Model (YOLOv8) | It "sees" the video and recognizes the shapes of potholes. |
| **The Heart** | Backend (FastAPI) | It takes the information from the Brain and sends it to the Database. |
| **The Memory** | Database (SQLite) | It remembers every pothole, its location, and its cost forever. |
| **The Face** | Dashboard (HTML/JS) | It shows all the memory and brain-work to the user on a pretty screen. |

### The Workflow Example:
1.  **Input**: You upload a video of a road.
2.  **Analysis**: The AI looks at 30 frames every second.
3.  **Connection**: The Backend calculates the repair cost based on the size of the hole.
4.  **Display**: You see a red dot on the map in the Dashboard.

---

## 5. WHERE is it used? (The Use Cases)
- **City Governments**: To plan which roads to fix first this month.
- **Contractors**: To prove they fixed the road (they can show a "Before" and "After" survey).
- **Insurance Companies**: To check if a road was dangerous before an accident.
- **Smart Cities**: To keep the city looking premium and well-maintained.

---

## 6. WHEN does it happen? (The Timing)
- **Pre-Monsoon**: Checking roads before the rain starts to seal small cracks.
- **Post-Repair**: Checking if the repair was done correctly.
- **Daily Monitoring**: Garbage trucks or buses can have a camera mounted on them to check roads every single day.

---

## 🏗️ Technical Summary for Developers
- **Language**: Python (Backend) & JavaScript (Frontend).
- **AI Model**: YOLOv8 (State-of-the-art for fast detection).
- **Database**: SQLite (Simple and fast).
- **Map Engine**: Leaflet.js with Dark Mode tiles.
