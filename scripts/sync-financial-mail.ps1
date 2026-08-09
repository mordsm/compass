param(
    [string]$CompassBaseUrl = "http://127.0.0.1:8000",
    [string]$UserId = "moshe",
    [string]$HouseholdId = "moshe_household",
    [int]$Limit = 50,
    [string]$Status = "",
    [switch]$IngestMail,
    [string]$MailQuery = "",
    [int]$MailMaxResults = 50
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$EnvPath = Join-Path $Root ".env"

function Read-EnvValue {
    param([string]$Name)
    if (-not (Test-Path $EnvPath)) {
        return $null
    }
    $line = Get-Content $EnvPath | Where-Object { $_ -match "^$Name=" } | Select-Object -First 1
    if (-not $line) {
        return $null
    }
    return ($line -replace "^$Name=", "").Trim()
}

$apiKey = $env:COMPASS_ACTIONS_API_KEY
if (-not $apiKey) {
    $apiKey = Read-EnvValue -Name "COMPASS_ACTIONS_API_KEY"
}

$headers = @{}
if ($apiKey) {
    $headers["Authorization"] = "Bearer $apiKey"
}

$context = @{
    household_id = $HouseholdId
    limit = $Limit
}
if ($Status) {
    $context["status"] = $Status
}
if ($IngestMail) {
    $context["ingest_mail"] = $true
    if ($MailQuery) {
        $context["mail_query"] = $MailQuery
    }
    if ($MailMaxResults) {
        $context["mail_max_results"] = $MailMaxResults
    }
}

$body = @{
    agent_id = "economic_manager"
    task = "sync_mail_financial_items"
    user_id = $UserId
    context = $context
    expected_output = "Import current financial mail items into economic_manager."
    risk_level = "low"
} | ConvertTo-Json -Depth 8

Invoke-RestMethod `
    -Method Post `
    -Uri "$CompassBaseUrl/api/agents/invoke" `
    -Headers $headers `
    -ContentType "application/json" `
    -Body $body
