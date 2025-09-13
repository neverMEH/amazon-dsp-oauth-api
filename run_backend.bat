@echo off
echo Starting Amazon DSP OAuth Backend...
echo.

cd backend

echo Activating virtual environment...
call venv\Scripts\activate

echo Starting FastAPI server...
uvicorn app.main:app --reload --port 8000