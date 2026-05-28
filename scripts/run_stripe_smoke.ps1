param(
  [string]$AppUrl = "http://localhost:8000",
  [string]$Slug = "cloudcare-it",
  [string]$LogFile = ".\artifacts\stripe-listen.log",
  [int]$TailLines = 200
)

$ErrorActionPreference = "Stop"

function Test-CommandExists {
  param([string]$Name)
  try {
    Get-Command $Name -ErrorAction Stop | Out-Null
    return $true
  } catch {
    return $false
  }
}

Write-Host "== Stripe Combined Smoke Test ==" -ForegroundColor Cyan
Write-Host "App URL: $AppUrl"
Write-Host "Template slug: $Slug"
Write-Host "Log file: $LogFile"
Write-Host ""

if (-not (Test-CommandExists "stripe")) {
  Write-Host "Stripe CLI is not installed or not on PATH." -ForegroundColor Red
  Write-Host "Install from https://docs.stripe.com/stripe-cli"
  exit 1
}

try {
  $health = Invoke-RestMethod -Uri "$AppUrl/health" -Method GET
  Write-Host "Health check OK: $($health.status)" -ForegroundColor Green
} catch {
  Write-Host "App is not reachable at $AppUrl." -ForegroundColor Red
  Write-Host "Start app first: py -m uvicorn app.main:app --reload"
  exit 1
}

$logParent = Split-Path -Parent $LogFile
if (-not [string]::IsNullOrWhiteSpace($logParent)) {
  New-Item -ItemType Directory -Path $logParent -Force | Out-Null
}

if (Test-Path $LogFile) {
  Remove-Item $LogFile -Force
}

$forwardUrl = "$($AppUrl.TrimEnd('/'))/webhooks/stripe"
$listenCommand = "stripe listen --forward-to $forwardUrl *> `"$LogFile`""

Write-Host ""
Write-Host "Starting Stripe listener..." -ForegroundColor Cyan
$listener = Start-Process -FilePath "powershell" -ArgumentList "-NoProfile", "-Command", $listenCommand -PassThru
Start-Sleep -Seconds 3

if ($listener.HasExited) {
  Write-Host "Stripe listener exited immediately. Check Stripe CLI auth/config." -ForegroundColor Red
  exit 1
}

Write-Host "Stripe listener started (PID: $($listener.Id))." -ForegroundColor Green
Write-Host "Tip: if this is first run, Stripe CLI may require 'stripe login' in a terminal." -ForegroundColor Yellow

$purchaseUrl = "$($AppUrl.TrimEnd('/'))/purchase/$Slug"
Write-Host ""
Write-Host "Opening purchase page: $purchaseUrl" -ForegroundColor Cyan
Start-Process $purchaseUrl | Out-Null

Write-Host ""
Write-Host "Complete a test payment with card 4242 4242 4242 4242, then press Enter..." -ForegroundColor Yellow
[void](Read-Host)

if (-not (Test-Path $LogFile)) {
  Write-Host "No Stripe log file found at $LogFile." -ForegroundColor Red
  try { Stop-Process -Id $listener.Id -Force } catch {}
  exit 2
}

$content = Get-Content $LogFile -Tail $TailLines
$joined = ($content -join "`n")

$hasCompleted = $joined -match "checkout\.session\.completed"
$hasWebhookPath = $joined -match "/webhooks/stripe"
$hasSuccess = $joined -match "(HTTP/1\.1|HTTP/2)\s+2\d\d|status=\s*2\d\d|succeeded|success"
$hasFailure = $joined -match "(HTTP/1\.1|HTTP/2)\s+[45]\d\d|status=\s*[45]\d\d|error|failed|signature|verification"

Write-Host ""
Write-Host "== Delivery Summary ==" -ForegroundColor Cyan
Write-Host "checkout.session.completed seen: $hasCompleted"
Write-Host "Webhook path seen: $hasWebhookPath"
Write-Host "Success indicators seen: $hasSuccess"
Write-Host "Failure indicators seen: $hasFailure"

if ($hasCompleted -and $hasWebhookPath -and $hasSuccess -and -not $hasFailure) {
  Write-Host ""
  Write-Host "PASS: Stripe webhook delivery looks healthy." -ForegroundColor Green
  $exitCode = 0
} elseif ($hasFailure) {
  Write-Host ""
  Write-Host "WARN: Failure indicators detected. Inspect full log for details." -ForegroundColor Yellow
  $exitCode = 2
} else {
  Write-Host ""
  Write-Host "INFO: Not enough evidence yet. Retry checkout and run again." -ForegroundColor Yellow
  $exitCode = 3
}

Write-Host ""
$stop = Read-Host "Stop Stripe listener now? (Y/n)"
if ($stop -eq "" -or $stop.ToLower() -eq "y" -or $stop.ToLower() -eq "yes") {
  try {
    Stop-Process -Id $listener.Id -Force
    Write-Host "Stripe listener stopped." -ForegroundColor Green
  } catch {
    Write-Host "Listener already exited." -ForegroundColor Yellow
  }
} else {
  Write-Host "Listener left running (PID: $($listener.Id))." -ForegroundColor Yellow
}

exit $exitCode
