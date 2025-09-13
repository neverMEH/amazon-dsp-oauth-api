Write-Host "Starting Amazon DSP OAuth Backend..." -ForegroundColor Green
Write-Host ""

Set-Location backend

Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

Write-Host "Starting FastAPI server..." -ForegroundColor Cyan
Write-Host "Server will be available at: http://localhost:8000" -ForegroundColor White
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""

uvicorn app.main:app --reload --port 8000