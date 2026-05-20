#Requires -Version 5.1
<#
.SYNOPSIS
  Mateo ConsultOps Themes — Docker Compose helpers.

.EXAMPLE
  .\scripts\docker.ps1 up
  .\scripts\docker.ps1 down
  .\scripts\docker.ps1 restart
  .\scripts\docker.ps1 rebuild
  .\scripts\docker.ps1 logs
  .\scripts\docker.ps1 clean
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet("up", "down", "restart", "rebuild", "logs", "ps", "shell", "clean", "help")]
    [string] $Action = "help",

    [switch] $Build,
    [switch] $NoDetach
)

$ErrorActionPreference = "Stop"
$HostPort = 8010
$AppUrl = "http://localhost:$HostPort"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

function Get-ComposeInvocation {
    docker compose version 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        return @{ Executable = "docker"; Args = @("compose") }
    }

    $legacy = Get-Command docker-compose -ErrorAction SilentlyContinue
    if ($legacy) {
        return @{ Executable = "docker-compose"; Args = @() }
    }

    throw "Docker Compose not found. Install Docker Desktop or the compose plugin."
}

function Ensure-EnvFile {
    $envPath = Join-Path $ProjectRoot ".env"
    $examplePath = Join-Path $ProjectRoot ".env.example"

    if (Test-Path $envPath) {
        return
    }

    if (-not (Test-Path $examplePath)) {
        throw ".env is missing and .env.example was not found. Create .env manually before running Docker."
    }

    Copy-Item $examplePath $envPath
    (Get-Content $envPath) | ForEach-Object {
        if ($_ -match '^BASE_URL=') { "BASE_URL=$AppUrl" } else { $_ }
    } | Set-Content $envPath
    Write-Host "Created .env from .env.example (BASE_URL set to $AppUrl)." -ForegroundColor Yellow
}

function Invoke-Compose {
    param([string[]] $ComposeArgs)

    $inv = Get-ComposeInvocation
    Push-Location $ProjectRoot
    try {
        & $inv.Executable @($inv.Args + $ComposeArgs)
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
    finally {
        Pop-Location
    }
}

function Show-Help {
    @"
Docker Compose shortcuts (run from anywhere):

  .\scripts\docker.ps1 up        Start stack in background (-Build to rebuild image)
  .\scripts\docker.ps1 down      Stop and remove containers
  .\scripts\docker.ps1 restart   down, then up
  .\scripts\docker.ps1 rebuild   Force image rebuild, then start
  .\scripts\docker.ps1 logs      Follow web service logs
  .\scripts\docker.ps1 ps        Show container status
  .\scripts\docker.ps1 shell     Open a shell in the web container
  .\scripts\docker.ps1 clean     down + remove volumes and orphans

From repo root you can also use:  .\docker.ps1 up

Local URL: $AppUrl (host port $HostPort -> container 8000)
"@
}

switch ($Action) {
    "help" {
        Show-Help
    }
    "up" {
        Ensure-EnvFile
        $args = @("up")
        if (-not $NoDetach) { $args += "-d" }
        if ($Build) { $args += "--build" }
        Invoke-Compose $args
        Write-Host "`nApp: $AppUrl" -ForegroundColor Green
    }
    "down" {
        Invoke-Compose @("down")
    }
    "restart" {
        Ensure-EnvFile
        Invoke-Compose @("down")
        $args = @("up")
        if (-not $NoDetach) { $args += "-d" }
        if ($Build) { $args += "--build" }
        Invoke-Compose $args
        Write-Host "`nApp: $AppUrl" -ForegroundColor Green
    }
    "rebuild" {
        Ensure-EnvFile
        Invoke-Compose @("build", "--no-cache")
        $args = @("up", "-d")
        Invoke-Compose $args
        Write-Host "`nApp: $AppUrl" -ForegroundColor Green
    }
    "logs" {
        Invoke-Compose @("logs", "-f", "web")
    }
    "ps" {
        Invoke-Compose @("ps")
    }
    "shell" {
        Invoke-Compose @("exec", "web", "sh")
    }
    "clean" {
        Invoke-Compose @("down", "-v", "--remove-orphans")
    }
}
