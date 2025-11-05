# Cleanup script - Keep only YOLO detection related files
$separator = "=" * 70
Write-Host $separator -ForegroundColor Cyan
Write-Host "Cleaning up workspace - Keeping only YOLO detection files" -ForegroundColor Yellow
Write-Host $separator -ForegroundColor Cyan

# Files to KEEP
$filesToKeep = @(
    "test_yolo_detection.py",
    "test_voice_only.py",
    "yolov8n.pt",
    "cleanup_workspace.ps1",
    ".gitignore",
    ".git"
)

Write-Host "`nFiles that will be KEPT:" -ForegroundColor Green
$filesToKeep | ForEach-Object { Write-Host "  + $_" -ForegroundColor Green }

Write-Host "`nStarting cleanup in 3 seconds..." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to cancel" -ForegroundColor Red
Start-Sleep -Seconds 3

# Get all items in current directory
$allItems = Get-ChildItem -Path "." -Force

$deletedCount = 0
$keptCount = 0

foreach ($item in $allItems) {
    $shouldKeep = $false

    foreach ($keepFile in $filesToKeep) {
        if ($item.Name -eq $keepFile) {
            $shouldKeep = $true
            break
        }
    }

    if ($shouldKeep) {
        Write-Host "  Keeping: $($item.Name)" -ForegroundColor Green
        $keptCount++
    }
    else {
        try {
            if ($item.PSIsContainer) {
                Write-Host "  Deleting folder: $($item.Name)" -ForegroundColor Red
                Remove-Item -Path $item.FullName -Recurse -Force -ErrorAction Stop
            }
            else {
                Write-Host "  Deleting file: $($item.Name)" -ForegroundColor Red
                Remove-Item -Path $item.FullName -Force -ErrorAction Stop
            }
            $deletedCount++
        }
        catch {
            Write-Host "  ⚠ Could not delete: $($item.Name) - $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

$separator = "=" * 70
Write-Host "`n$separator" -ForegroundColor Cyan
Write-Host "Cleanup Complete!" -ForegroundColor Green
Write-Host "  Kept: $keptCount items" -ForegroundColor Green
Write-Host "  Deleted: $deletedCount items" -ForegroundColor Red
Write-Host $separator -ForegroundColor Cyan
