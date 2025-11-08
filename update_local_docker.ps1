<#
.SYNOPSIS
  Update and restart local Docker Desktop deployment of openpilot multi-device detection.

.DESCRIPTION
  Pulls the latest image (or rebuilds), recreates the container with Docker Compose,
  and optionally waits for a healthy status.

.PARAMETER Build
  Build the image locally instead of pulling.

.PARAMETER NoHealth
  Skip the health check wait.

.PARAMETER Prune
  Run docker system prune -f before updating (CAUTION).

.PARAMETER Logs
  Attach logs after starting.

.PARAMETER Override
  Use docker-compose.override.yml if present (Compose will auto-detect; this flag is informational).

.EXAMPLES
  .\update_local_docker.ps1
  .\update_local_docker.ps1 -Build -Logs
  .\update_local_docker.ps1 -NoHealth
  .\update_local_docker.ps1 -Prune

.NOTES
  Requires Docker Desktop and docker compose v2.
#>
param(
  [switch]$Build,
  [switch]$NoHealth,
  [switch]$Prune,
  [switch]$Logs,
  [switch]$Override,
  [switch]$Prod
)

$ErrorActionPreference = 'Stop'

function Require-Command($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Command not found: $name. Ensure Docker Desktop is installed and running."
  }
}

try {
  Require-Command docker
} catch {
  Write-Error $_.Exception.Message
  exit 1
}

if (-not (Test-Path -Path 'docker-compose.yml')) {
  Write-Error "docker-compose.yml not found in $(Get-Location)"
  exit 2
}

$ServiceName = 'multi-device-detection'
$ContainerName = 'openpilot-detection'
$ImageRef = 'kainosit/openpilot:latest'

if ($Prune) {
  Write-Host "[INFO] Pruning unused Docker resources (CAUTION)"
  docker system prune -f | Out-Null
}

if ($Prod -and $Build) {
  Write-Warning "-Prod overrides -Build; production mode will not perform a local build."
}

$composeArgs = @('compose')
if ($Prod) {
  if (-not (Test-Path 'docker-compose.prod.yml')) { Write-Error "docker-compose.prod.yml not found."; exit 2 }
  $composeArgs += @('-f','docker-compose.yml','-f','docker-compose.prod.yml')
  Write-Host "[INFO] Using production compose files (pull-only, pull_policy=always)."
} else {
  if (Test-Path 'docker-compose.override.yml') { Write-Host "[INFO] Override file detected; local build may occur unless -Prod used." }
}

if (-not $Prod -and $Build) {
  Write-Host "[INFO] Building local image from Dockerfile"
  try { & docker @($composeArgs + @('build','--pull')) } catch { & docker @($composeArgs + @('build')) }
} else {
  Write-Host "[INFO] Pulling latest remote image $ImageRef"
  try { & docker @($composeArgs + @('pull',$ServiceName)) } catch { Write-Warning "Pull failed; you may need to login or build locally." }
}

Write-Host "[INFO] Recreating container"
try { & docker @($composeArgs + @('down','--remove-orphans')) | Out-Null } catch { Write-Host "[INFO] No running stack to remove" }

if (-not $Prod -and $Build) {
  & docker @($composeArgs + @('up','-d','--build')) | Out-Null
} else {
  & docker @($composeArgs + @('up','-d')) | Out-Null
}

Write-Host "[INFO] Waiting for container start (5s)"
Start-Sleep -Seconds 5

if (-not $NoHealth) {
  Write-Host "[INFO] Checking health status (timeout 60s)"
  $attempts = 0
  $status = 'unknown'
  while ($attempts -lt 12) {
    try {
      $status = docker inspect $ContainerName --format='{{.State.Health.Status}}'
    } catch {
      $status = 'starting'
    }
    if ($status -eq 'healthy') {
      Write-Host "[INFO] Health: healthy"
      break
    } else {
      Write-Host "[INFO] Health: $status (attempt $($attempts+1)/12)"
      Start-Sleep -Seconds 5
      $attempts++
    }
  }
  if ($status -ne 'healthy') {
    Write-Error "Container did not become healthy in expected time."
    exit 3
  }
} else {
  Write-Host "[INFO] Skipping health check by user request"
}

Write-Host "[INFO] Deployed image version:"
try { docker inspect $ContainerName --format='Image={{.Config.Image}}' } catch {}

Write-Host "[INFO] Running containers matching openpilot:"
try { docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | Select-String -Pattern 'openpilot|NAME' } catch {}

if ($Logs) {
  Write-Host "[INFO] Attaching logs (Ctrl+C to detach)"
  & docker @($composeArgs + @('logs','-f','--no-color',$ServiceName))
}

Write-Host "[SUCCESS] Local update complete."
exit 0
