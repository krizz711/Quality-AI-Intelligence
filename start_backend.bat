@echo off
cd /d "c:\Users\Asus\OneDrive\Desktop\Projects\Quality_Control_&_GR&R_Analysis_Agent"
poetry run uvicorn api.main:app --host 0.0.0.0 --port 8000
