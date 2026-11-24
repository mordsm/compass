param(
    [int]$Port = 8010,
    [switch]$Restart
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$StartCompass = Join-Path $PSScriptRoot "start-compass.ps1"

if (-not (Test-Path $StartCompass)) {
    throw "start-compass.ps1 was not found."
}

Push-Location $Root
try {
    $args = @("-ExecutionPolicy", "Bypass", "-File", $StartCompass, "-Port", "$Port", "-SkipSelfTrainer")
    if ($Restart) {
        $args += "-Restart"
    }
    powershell.exe @args
    Write-Host ""
    Write-Host "FamilyBiz remote URL is the printed Cloudflare URL plus /familybiz/"
    Write-Host "Example: https://example.trycloudflare.com/familybiz/"
    Write-Host "On Android, open that URL in Chrome and choose Add to Home screen."
}
finally {
    Pop-Location
}
