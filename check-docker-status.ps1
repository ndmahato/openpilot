# Docker Status Check Script
# Run this script to diagnose Docker container issues

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Docker Status Check" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. Check Docker installation
Write-Host "1. Checking Docker installation..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "   ✓ Docker installed: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Docker not installed or not running!" -ForegroundColor Red
    Write-Host "   Please install Docker Desktop from https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
    exit
}

# 2. Check Docker Compose
Write-Host "`n2. Checking Docker Compose..." -ForegroundColor Yellow
try {
    $composeVersion = docker-compose --version
    Write-Host "   ✓ Docker Compose available: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Docker Compose not available!" -ForegroundColor Red
}

# 3. Check Docker images
Write-Host "`n3. Checking Docker images..." -ForegroundColor Yellow
$images = docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | Select-String "openpilot"
if ($images) {
    Write-Host "   ✓ Image found:" -ForegroundColor Green
    Write-Host "   $images" -ForegroundColor White
} else {
    Write-Host "   ✗ No openpilot-detection image found!" -ForegroundColor Red
    Write-Host "   Run: docker-compose up --build -d" -ForegroundColor Yellow
}

# 4. Check running containers
Write-Host "`n4. Checking running containers..." -ForegroundColor Yellow
$containers = docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
$openpilotContainer = docker ps --filter "name=openpilot" --format "{{.Names}}"

if ($openpilotContainer) {
    Write-Host "   ✓ Container running: $openpilotContainer" -ForegroundColor Green
    
    # Get detailed status
    $status = docker inspect $openpilotContainer --format='{{.State.Status}}'
    $health = docker inspect $openpilotContainer --format='{{.State.Health.Status}}' 2>$null
    
    Write-Host "   Status: $status" -ForegroundColor White
    if ($health) {
        if ($health -eq "healthy") {
            Write-Host "   Health: $health" -ForegroundColor Green
        } else {
            Write-Host "   Health: $health" -ForegroundColor Yellow
        }
    }
    
    # Check ports
    $ports = docker port $openpilotContainer
    Write-Host "   Ports: $ports" -ForegroundColor White
    
} else {
    Write-Host "   ✗ No openpilot container running!" -ForegroundColor Red
    
    # Check if container exists but is stopped
    $stoppedContainer = docker ps -a --filter "name=openpilot" --format "{{.Names}}"
    if ($stoppedContainer) {
        Write-Host "   Container exists but is stopped: $stoppedContainer" -ForegroundColor Yellow
        Write-Host "   Run: docker start $stoppedContainer" -ForegroundColor Yellow
    } else {
        Write-Host "   Run: docker-compose up -d" -ForegroundColor Yellow
    }
}

# 5. Test localhost connectivity
Write-Host "`n5. Testing localhost connectivity..." -ForegroundColor Yellow
$response = $null
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000/status" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "   ✓ Server is accessible at http://localhost:5000" -ForegroundColor Green
    Write-Host "   Response: $($response.StatusCode) $($response.StatusDescription)" -ForegroundColor White
} catch {
    Write-Host "   ✗ Cannot access http://localhost:5000" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
}

# 6. Get local IP addresses
Write-Host "`n6. Network information..." -ForegroundColor Yellow
Write-Host "   Local IP addresses:" -ForegroundColor White
$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -eq "Dhcp" }
foreach ($ip in $ips) {
    Write-Host "   - http://$($ip.IPAddress):5000" -ForegroundColor Cyan
}

# 7. View recent logs
Write-Host "`n7. Recent container logs (last 20 lines)..." -ForegroundColor Yellow
if ($openpilotContainer) {
    Write-Host "   Logs from ${openpilotContainer}:" -ForegroundColor White
    docker logs --tail 20 $openpilotContainer 2>&1
} else {
    Write-Host "   No container running to show logs" -ForegroundColor Red
}

# 8. Summary and recommendations
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($openpilotContainer -and $response) {
    Write-Host "✓ Everything looks good! Access the system at:" -ForegroundColor Green
    Write-Host "  - From this PC: http://localhost:5000" -ForegroundColor Cyan
    if ($ips) {
        Write-Host "  - From mobile: http://$($ips[0].IPAddress):5000" -ForegroundColor Cyan
    }
} else {
    Write-Host "✗ Issues detected:" -ForegroundColor Red
    if (-not $images) {
        Write-Host "  1. Build the Docker image: docker-compose up --build -d" -ForegroundColor Yellow
    }
    if (-not $openpilotContainer) {
        Write-Host "  2. Start the container: docker-compose up -d" -ForegroundColor Yellow
    }
    if ($openpilotContainer -and -not $response) {
        Write-Host "  3. Check container logs: docker logs openpilot-detection" -ForegroundColor Yellow
        Write-Host "  4. Wait 30-40 seconds for startup, then test again" -ForegroundColor Yellow
    }
}

Write-Host "`nFor more help, see LOCAL_DOCKER_TESTING.md" -ForegroundColor Gray
