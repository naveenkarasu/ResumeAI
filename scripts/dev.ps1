# Resume RAG Platform - Development Server (Windows PowerShell)
# Starts both backend and frontend in development mode

Write-Host "🚀 Starting Resume RAG Platform (Development)" -ForegroundColor Cyan

# Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host "⚠️  No .env file found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "📝 Please edit .env with your API keys" -ForegroundColor Yellow
}

# Function to start a process in a new window
function Start-DevServer {
    param($Name, $Command, $WorkDir)

    $processInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processInfo.FileName = "cmd.exe"
    $processInfo.Arguments = "/k title $Name && cd /d $WorkDir && $Command"
    $processInfo.UseShellExecute = $true

    [System.Diagnostics.Process]::Start($processInfo)
}

# Get current directory
$rootDir = Get-Location

# Start backend
Write-Host "🔧 Starting backend..." -ForegroundColor Green
Start-DevServer -Name "Backend" -Command "python -m uvicorn src.ui.api.main:app --reload --port 8000" -WorkDir $rootDir

# Wait a moment
Start-Sleep -Seconds 2

# Start frontend
Write-Host "🎨 Starting frontend..." -ForegroundColor Green
Start-DevServer -Name "Frontend" -Command "npm run dev" -WorkDir "$rootDir\frontend"

Write-Host ""
Write-Host "✅ Development servers started in new windows!" -ForegroundColor Green
Write-Host "   Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "   Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Close the terminal windows to stop the servers" -ForegroundColor Gray
