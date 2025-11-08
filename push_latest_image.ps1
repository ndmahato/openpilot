<#
.SYNOPSIS
  Build and push Docker images (latest + date/git tag) to Docker Hub.

.DESCRIPTION
  Builds the image defined by Dockerfile, tags with 'latest' and a date-based version
  optionally suffixed by short git SHA (if in a git repo), and pushes to Docker Hub.

.PARAMETER NoCache
  Perform a no-cache build.

.PARAMETER DryRun
  Show planned actions without performing build/push.

.PARAMETER Platform
  Target platform for buildx (e.g. linux/amd64 or linux/amd64,linux/arm64).

.PARAMETER ExtraTag
  Additional custom tag to apply and push.

.EXAMPLES
  .\push_latest_image.ps1
  .\push_latest_image.ps1 -NoCache -ExtraTag staging
  .\push_latest_image.ps1 -Platform linux/amd64
  .\push_latest_image.ps1 -DryRun
#>
param(
  [switch]$NoCache,
  [switch]$DryRun,
  [string]$Platform,
  [string]$ExtraTag
)

$ErrorActionPreference = 'Stop'

function Require-Command($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Command not found: $name. Ensure Docker Desktop is installed and running."
  }
}

try { Require-Command docker } catch { Write-Error $_.Exception.Message; exit 1 }

if (-not (Test-Path -Path 'Dockerfile')) {
  Write-Error "Dockerfile not found in $(Get-Location)"; exit 2
}

$ImageBase = 'kainosit/openpilot'
$DateTag = (Get-Date -Format 'yyyy-MM-dd')
$GitSha = ''
if (Get-Command git -ErrorAction SilentlyContinue) {
  try { if ((git rev-parse --is-inside-work-tree 2>$null) -eq 'true') { $GitSha = (git rev-parse --short HEAD).Trim() } } catch {}
}
$VersionTag = if ($GitSha) { "$DateTag-$GitSha" } else { $DateTag }

Write-Host "[INFO] Building image tags: latest, $VersionTag"
if ($ExtraTag) { Write-Host "[INFO] Extra tag: $ExtraTag" }

$buildArgs = @()

if ($Platform) {
  # buildx path
  if (-not (docker buildx version 2>$null)) {
    Write-Error "docker buildx not available; create a builder (docker buildx create --use)."; exit 3
  }
  $buildArgs = @('buildx','build','--platform', $Platform,'-t',"$($ImageBase):latest",'-t',"$($ImageBase):$VersionTag",'.')
  if ($NoCache) { $buildArgs += '--no-cache' }
  # For multi-platform implicit push needed; we prefer explicit push after single-platform build.
  # If multiple platforms specified (comma), we must push during build.
  if ($Platform -match ',') {
    Write-Host "[INFO] Multi-platform build requires inline push"
    $buildArgs += '--push'
  }
} else {
  $buildArgs = @('build','-t',"$($ImageBase):latest",'-t',"$($ImageBase):$VersionTag",'.')
  if ($NoCache) { $buildArgs += '--no-cache' }
}

if ($DryRun) {
  Write-Host "[DRY-RUN] docker $($buildArgs -join ' ')"
} else {
  docker @buildArgs
}

if ($ExtraTag) {
  if ($DryRun) {
    Write-Host "[DRY-RUN] docker tag $($ImageBase):latest $($ImageBase):$ExtraTag"
  } else {
    docker tag "$($ImageBase):latest" "$($ImageBase):$ExtraTag"
  }
}

if ($DryRun) {
  $tags = @('latest', $VersionTag)
  if ($ExtraTag) { $tags += $ExtraTag }
  $tagList = $tags -join ', '
  Write-Host "[DRY-RUN] Would push: $($ImageBase): $tagList"
  exit 0
}

# If multi-platform buildx with --push already executed, skip re-push for those tags (can't detect easily—still attempt push; Docker will reuse).
foreach ($tag in @('latest', $VersionTag, $ExtraTag)) {
  if (-not [string]::IsNullOrEmpty($tag)) {
    Write-Host "[INFO] Pushing $($ImageBase):$tag"
    docker push "$($ImageBase):$tag"
  }
}

$finalTags = @('latest', $VersionTag)
if ($ExtraTag) { $finalTags += $ExtraTag }
Write-Host "[SUCCESS] Image pushed: $($ImageBase): $($finalTags -join ', ')"
exit 0
