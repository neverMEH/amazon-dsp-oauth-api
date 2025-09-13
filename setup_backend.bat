@echo off
echo Setting up Amazon DSP OAuth Backend...
echo.

cd backend

echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo ✅ Setup complete!
echo.
echo To run the backend server:
echo   1. cd backend
echo   2. venv\Scripts\activate
echo   3. uvicorn app.main:app --reload --port 8000
echo.
echo The API will be available at http://localhost:8000
echo API documentation at http://localhost:8000/docs
pause