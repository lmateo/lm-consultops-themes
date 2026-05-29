param(
  [string]$AppUrl = "http://localhost:8010",
  [string]$Slug = "cloudcare-it",
  [string]$ArtifactDir = ".\artifacts\smoke",
  [switch]$SkipCli,
  [switch]$SkipE2e,
  [switch]$SyncDockerWebhookSecret,
  [switch]$HeadedE2e
)

$ErrorActionPreference = "Stop"

$argsList = @(
  "tests/smoke/run_all_stripe_smokes.py",
  "--base-url", $AppUrl,
  "--template-slug", $Slug,
  "--artifact-dir", $ArtifactDir
)

if ($SkipCli) { $argsList += "--skip-cli" }
if ($SkipE2e) { $argsList += "--skip-e2e" }
if ($SyncDockerWebhookSecret) { $argsList += "--sync-docker-webhook-secret" }
if ($HeadedE2e) { $argsList += "--headed-e2e" }

$env:Path = "$env:LOCALAPPDATA\stripe;$env:Path"
Set-Location $PSScriptRoot\..

py @argsList
exit $LASTEXITCODE
