Param(
  [switch]$Dev
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Resolve-Path (Join-Path $root "..")
Set-Location $repo

if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

$python = Join-Path ".venv" "Scripts\python.exe"

& $python -m pip install --upgrade pip

if ($Dev) {
  & $python -m pip install -e ".[dev]"
} else {
  & $python -m pip install -e "."
}

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
}

Write-Host "Ready."
Write-Host "Activate with: .\\.venv\\Scripts\\Activate.ps1"

