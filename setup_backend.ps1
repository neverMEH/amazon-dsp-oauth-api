Write-Host "Setting up Amazon DSP OAuth Backend..." -ForegroundColor Green
Write-Host ""

Set-Location backend

Write-Host "Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To run the backend server:" -ForegroundColor Cyan
Write-Host "  1. cd backend"
Write-Host "  2. .\venv\Scripts\Activate.ps1"
Write-Host "  3. uvicorn app.main:app --reload --port 8000"
Write-Host ""
Write-Host "The API will be available at http://localhost:8000" -ForegroundColor White
Write-Host "API documentation at http://localhost:8000/docs" -ForegroundColor White