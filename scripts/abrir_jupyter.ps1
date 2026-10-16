$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$envPath = Join-Path $ProjectRoot '.env'

if (-not (Test-Path -LiteralPath $envPath)) {
    throw 'Arquivo .env não encontrado. Execute scripts\preparar_ambiente.ps1 primeiro.'
}

$tokenLine = Get-Content -LiteralPath $envPath | Where-Object { $_ -match '^\s*JUPYTER_TOKEN\s*=' } | Select-Object -Last 1
if ($tokenLine -notmatch '^\s*JUPYTER_TOKEN\s*=(.*)$' -or [string]::IsNullOrWhiteSpace($Matches[1])) {
    throw 'JUPYTER_TOKEN ausente no .env. Execute novamente scripts\preparar_ambiente.ps1.'
}
$token = $Matches[1].Trim()

$ready = $false
for ($attempt = 0; $attempt -lt 20; $attempt++) {
    try {
        $null = Invoke-WebRequest -Uri 'http://localhost:8888/api/status' `
            -Headers @{ Authorization = "token $token" } -UseBasicParsing -TimeoutSec 3
        $ready = $true
        break
    } catch {
        Start-Sleep -Seconds 2
    }
}

if (-not $ready) {
    throw 'JupyterLab não respondeu em http://localhost:8888. Confira se o serviço está ligado no dashboard.'
}

$encodedToken = [Uri]::EscapeDataString($token)
Start-Process "http://localhost:8888/lab?token=$encodedToken"
