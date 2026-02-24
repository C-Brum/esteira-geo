# =====================================================
# Docker Development Helper Script for Windows PowerShell
# =====================================================

param(
    [Parameter(Position = 0)]
    [ValidateSet('up', 'down', 'logs', 'pipeline', 'shell', 'test', 'clean', 'status', 'db', 'minio')]
    [string]$Command = 'status'
)

function Write-Header {
    param([string]$Text)
    Write-Host "`n" -NoNewline
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host $Text -ForegroundColor Cyan
    Write-Host "=" * 60 -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Text)
    Write-Host "✓ $Text" -ForegroundColor Green
}

function Write-Info {
    param([string]$Text)
    Write-Host "ℹ $Text" -ForegroundColor Blue
}

function Write-Error-Custom {
    param([string]$Text)
    Write-Host "✗ $Text" -ForegroundColor Red
}

function Show-Status {
    Write-Header "Docker Containers Status"
    docker-compose ps
    Write-Info "Endpoints:"
    Write-Info "  Flask Dashboard: http://localhost:5000"
    Write-Info "  MinIO Console: http://localhost:9001 (user: minioadmin)"
    Write-Info "  PostgreSQL: localhost:5432"
}

function Start-Environment {
    Write-Header "Starting Esteira Geo Docker Environment"
    
    # Check if Docker is running
    if (-not (docker ps -q 2>$null)) {
        Write-Error-Custom "Docker daemon is not running!"
        Write-Info "Please start Docker Desktop or Docker daemon."
        exit 1
    }
    
    Write-Info "Building images..."
    docker-compose build
    
    Write-Info "Starting containers..."
    docker-compose up -d
    
    Write-Info "Waiting for services to be healthy..."
    Start-Sleep -Seconds 10
    
    Show-Status
    Write-Success "Environment started! Waiting for PostGIS and MinIO to initialize..."
    Write-Info "This may take another 10-20 seconds. Check status: .\docker.ps1 status"
}

function Stop-Environment {
    Write-Header "Stopping Esteira Geo Docker Environment"
    docker-compose down
    Write-Success "Environment stopped"
}

function Show-Logs {
    param([string]$Service = $null)
    
    if ($Service) {
        Write-Header "Logs for $Service"
        docker-compose logs -f --tail=50 $Service
    }
    else {
        Write-Info "Available services: postgis, minio, pipeline, web"
        Write-Info "Usage: .\docker.ps1 logs postgis"
        docker-compose logs --tail=20
    }
}

function Run-Pipeline {
    Write-Header "Running Full Pipeline ETL"
    Write-Info "Executing: Bronze -> Silver -> Gold -> PostGIS"
    
    docker-compose exec -T pipeline python /app/pipeline/main.py
    
    Write-Success "Pipeline completed!"
}

function Access-Shell {
    Write-Header "Accessing Pipeline Container Shell"
    docker-compose exec pipeline bash
}

function Run-Tests {
    Write-Header "Running Pipeline Tests"
    
    Write-Info "1. Creating Bronze data..."
    docker-compose exec -T pipeline python -c "from pipeline.etl.bronze_loader import load_sample_data; load_sample_data()"
    
    Write-Info "2. Processing Silver layer..."
    docker-compose exec -T pipeline python -c "from pipeline.etl.silver_processor import process_silver; process_silver()"
    
    Write-Info "3. Processing Gold layer (spatial join)..."
    docker-compose exec -T pipeline python -c "from pipeline.etl.gold_processor import process_gold; process_gold()"
    
    Write-Info "4. Loading to PostGIS..."
    docker-compose exec -T pipeline python -c "from pipeline.etl.postgis_loader import load_to_postgis; load_to_postgis()"
    
    Write-Success "All tests completed!"
}

function Clean-Environment {
    Write-Header "Cleaning Docker Environment"
    
    $response = Read-Host "This will remove all containers and volumes. Continue? (y/N)"
    if ($response -ne 'y') {
        Write-Info "Cancelled."
        return
    }
    
    Write-Info "Removing containers and volumes..."
    docker-compose down -v
    
    Write-Info "Removing logs..."
    Remove-Item -Recurse -Force logs -ErrorAction SilentlyContinue
    
    Write-Success "Environment cleaned"
}

function Access-Database {
    Write-Header "Accessing PostgreSQL Database"
    
    Write-Info "Connecting to esteira_geo database..."
    docker-compose exec postgis psql -U esteira_user -d esteira_geo
}

function Access-MinIO {
    Write-Header "MinIO Console"
    
    Write-Info "Opening MinIO Console..."
    Write-Info "URL: http://localhost:9001"
    Write-Info "User: minioadmin"
    Write-Info "Pass: minioadmin123"
    
    # Try to open in browser (Windows)
    Start-Process "http://localhost:9001" -ErrorAction SilentlyContinue
    Write-Info "Opening browser if available..."
}

# Main command dispatcher
switch ($Command) {
    'up' { Start-Environment }
    'down' { Stop-Environment }
    'status' { Show-Status }
    'logs' { Show-Logs @args }
    'pipeline' { Run-Pipeline }
    'shell' { Access-Shell }
    'test' { Run-Tests }
    'clean' { Clean-Environment }
    'db' { Access-Database }
    'minio' { Access-MinIO }
    default {
        Write-Host "`nEsteira Geo Docker Helper`n" -ForegroundColor Cyan
        Write-Host "Usage: .\docker.ps1 [command]`n" -ForegroundColor White
        Write-Host "Commands:" -ForegroundColor White
        Write-Host "  up        - Start Docker environment" -ForegroundColor Gray
        Write-Host "  down      - Stop Docker environment" -ForegroundColor Gray
        Write-Host "  status    - Show container status" -ForegroundColor Gray
        Write-Host "  logs      - Show logs (optionally: logs [service])" -ForegroundColor Gray
        Write-Host "  pipeline  - Run full ETL pipeline" -ForegroundColor Gray
        Write-Host "  shell     - Access pipeline container shell" -ForegroundColor Gray
        Write-Host "  test      - Run all tests" -ForegroundColor Gray
        Write-Host "  db        - Access PostgreSQL database" -ForegroundColor Gray
        Write-Host "  minio     - Open MinIO Console" -ForegroundColor Gray
        Write-Host "  clean     - Clean all containers and volumes" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Examples:" -ForegroundColor White
        Write-Host "  .\docker.ps1 up" -ForegroundColor Gray
        Write-Host "  .\docker.ps1 logs pipeline" -ForegroundColor Gray
        Write-Host "  .\docker.ps1 pipeline" -ForegroundColor Gray
        Write-Host ""
    }
}
