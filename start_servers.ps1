$projectPath = "c:\Users\Asus\OneDrive\Desktop\Projects\Quality_Control_&_GR&R_Analysis_Agent"
$frontendPath = Join-Path $projectPath "dashboard"

Write-Host "Starting FastAPI backend on port 8000..."
$backendJob = Start-Job -ScriptBlock {
    param($path)
    Set-Location $path
    & poetry run uvicorn api.main:app --host 0.0.0.0 --port 8000
} -ArgumentList $projectPath

Write-Host "Starting Next.js frontend on port 3000..."
$frontendJob = Start-Job -ScriptBlock {
    param($path)
    Set-Location $path
    & npm run dev
} -ArgumentList $frontendPath

Write-Host "Waiting 30 seconds for servers to start..."
Start-Sleep -Seconds 30

Write-Host "`n--- Backend Job Output ---"
Receive-Job $backendJob -Keep | Select-Object -Last 20

Write-Host "`n--- Frontend Job Output ---"
Receive-Job $frontendJob -Keep | Select-Object -Last 20

Write-Host "`n--- Port Check ---"
netstat -ano | Select-String ":8000|:3000"

Write-Host "`nBoth server jobs running. Backend Job ID: $($backendJob.Id), Frontend Job ID: $($frontendJob.Id)"
Write-Host "Press Ctrl+C to stop monitoring (jobs continue in background)"

# Keep running to show live output
while ($true) {
    Start-Sleep -Seconds 10
    $be = Receive-Job $backendJob -Keep | Select-Object -Last 5
    $fe = Receive-Job $frontendJob -Keep | Select-Object -Last 5
    if ($be) { Write-Host "[BACKEND] $($be -join "`n[BACKEND] ")"}
    if ($fe) { Write-Host "[FRONTEND] $($fe -join "`n[FRONTEND] ")"}
}
