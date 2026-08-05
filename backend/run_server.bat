@echo off
echo Starting Road AI API Engine...
d:
cd \Road_AI_Project\backend
"C:\Users\BISAGN\AppData\Local\Programs\Python\Python311\python.exe" -m uvicorn main:app --reload --host 0.0.0.0
pause
