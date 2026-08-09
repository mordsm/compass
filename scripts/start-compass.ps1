param(
    [int]$Port = 8000,
    [switch]$Restart,
    [switch]$SkipSelfTrainer,
    [switch]$NoTunnel
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Logs = Join-Path $Root "logs"
$CompassOutLog = Join-Path $Logs "compass.out.log"
$CompassErrLog = Join-Path $Logs "compass.err.log"
$SelfTrainerOutLog = Join-Path $Logs "self-trainer.out.log"
$SelfTrainerErrLog = Join-Path $Logs "self-trainer.err.log"
$LocalBaseUrl = "http://127.0.0.1:$Port"
$HealthUrl = "$LocalBaseUrl/api/health"
$SelfTrainerPort = 8008
$SelfTrainerBaseUrl = "http://127.0.0.1:$SelfTrainerPort"
$SelfTrainerUrl = "$SelfTrainerBaseUrl/training/context?user_id=moshe"

New-Item -ItemType Directory -Force -Path $Logs | Out-Null

function Test-UrlOk {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300)
    }
    catch {
        return $false
    }
}

function Wait-UrlOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 20
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-UrlOk -Url $Url) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Set-CompassPublicUrl {
    param([string]$PublicUrl)

    $envPath = Join-Path $Root ".env"
    $openApiPaths = @(
        (Join-Path $Root "openapi.yaml"),
        (Join-Path $Root "openapi.gpt.yaml"),
        (Join-Path $Root "openapi.actions.yaml")
    )

    if (Test-Path $envPath) {
        $envText = Get-Content -Raw $envPath
        if ($envText -match "(?m)^COMPASS_PUBLIC_BASE_URL=") {
            $envText = $envText -replace "(?m)^COMPASS_PUBLIC_BASE_URL=.*$", "COMPASS_PUBLIC_BASE_URL=$PublicUrl"
        }
        else {
            $envText = $envText.TrimEnd() + "`r`nCOMPASS_PUBLIC_BASE_URL=$PublicUrl`r`n"
        }
        Set-Content -Path $envPath -Value $envText -NoNewline
    }

    foreach ($openApiPath in $openApiPaths) {
        if (Test-Path $openApiPath) {
            $openApiText = Get-Content -Raw $openApiPath
            $openApiText = $openApiText -replace "(?m)^(\s*-\s*url:\s*)https://[^\s]+", "`${1}$PublicUrl"
            Set-Content -Path $openApiPath -Value $openApiText -NoNewline
        }
    }
}

function Stop-ListenersOnPort {
    param([int]$TargetPort)

    $processIds = Get-NetTCPConnection -LocalPort $TargetPort -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($processId in $processIds) {
        if ($processId -and $processId -ne $PID) {
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
}

Push-Location $Root
try {
    if ($Restart) {
        Stop-ListenersOnPort -TargetPort $Port
        Stop-ListenersOnPort -TargetPort $SelfTrainerPort
        Start-Sleep -Seconds 1
    }

    if (-not (Test-UrlOk -Url $HealthUrl)) {
        Start-Process `
            -FilePath "uv" `
            -ArgumentList @("run", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port") `
            -WorkingDirectory $Root `
            -RedirectStandardOutput $CompassOutLog `
            -RedirectStandardError $CompassErrLog `
            -WindowStyle Hidden

        if (-not (Wait-UrlOk -Url $HealthUrl -TimeoutSeconds 30)) {
            throw "Compass did not become healthy at $HealthUrl. Check $CompassOutLog and $CompassErrLog."
        }
    }

    Write-Host "Compass is running at $LocalBaseUrl"

    if (-not $SkipSelfTrainer -and -not (Test-UrlOk -Url $SelfTrainerUrl)) {
        $selfTrainerRoot = Resolve-Path (Join-Path $Root "..\self_trainer") -ErrorAction SilentlyContinue
        $pythonPath = Join-Path $Root ".venv\Scripts\python.exe"
        if ($selfTrainerRoot -and (Test-Path $pythonPath)) {
            Start-Process `
                -FilePath $pythonPath `
                -ArgumentList @("-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "$SelfTrainerPort") `
                -WorkingDirectory $selfTrainerRoot.Path `
                -RedirectStandardOutput $SelfTrainerOutLog `
                -RedirectStandardError $SelfTrainerErrLog `
                -WindowStyle Hidden

            if (Wait-UrlOk -Url $SelfTrainerUrl -TimeoutSeconds 20) {
                Write-Host "Self Trainer is running at $SelfTrainerBaseUrl"
            }
            else {
                Write-Host "Self Trainer did not become healthy. Check $SelfTrainerOutLog and $SelfTrainerErrLog."
            }
        }
        else {
            Write-Host "Self Trainer was not started because ../self_trainer or Compass Python was not found."
        }
    }
    elseif (-not $SkipSelfTrainer) {
        Write-Host "Self Trainer is running at $SelfTrainerBaseUrl"
    }

    if ($NoTunnel) {
        exit 0
    }

    $cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
    if (-not $cloudflared) {
        $defaultCloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
        if (Test-Path $defaultCloudflared) {
            $cloudflaredPath = $defaultCloudflared
        }
        else {
            throw "cloudflared was not found. Install it or run with -NoTunnel."
        }
    }
    else {
        $cloudflaredPath = $cloudflared.Source
    }

    $TunnelLog = Join-Path $Logs ("cloudflared-quick-{0}.log" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

    Start-Process `
        -FilePath $cloudflaredPath `
        -ArgumentList @("tunnel", "--url", $LocalBaseUrl, "--logfile", $TunnelLog, "--loglevel", "info") `
        -WorkingDirectory $Root `
        -WindowStyle Hidden

    $publicUrl = $null
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline -and -not $publicUrl) {
        if (Test-Path $TunnelLog) {
            $logText = Get-Content -Raw $TunnelLog
            $match = [regex]::Match($logText, "https://[a-z0-9-]+\.trycloudflare\.com")
            if ($match.Success) {
                $publicUrl = $match.Value
            }
        }
        Start-Sleep -Milliseconds 500
    }

    if (-not $publicUrl) {
        throw "Cloudflare tunnel started, but no public URL appeared in $TunnelLog."
    }

    Set-CompassPublicUrl -PublicUrl $publicUrl
    Write-Host "Cloudflare tunnel is running at $publicUrl"
    Write-Host "Re-import openapi.yaml in your Custom GPT Action if the URL changed."
}
finally {
    Pop-Location
}
