param(
    [switch]$Resume
)

$ErrorActionPreference = 'Stop'
$Distro = 'Ubuntu-24.04'
$TaskName = 'LaboratorioIA-ContinuarInstalacao'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Register-ResumeTask {
    $powerShellExe = (Get-Process -Id $PID).Path
    $scriptPath = $PSCommandPath
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -Resume"
    $action = New-ScheduledTaskAction -Execute $powerShellExe -Argument $arguments
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
    $principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Highest
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Force | Out-Null
}

function Request-RestartAndResume([string]$Reason) {
    Register-ResumeTask
    Write-Warning $Reason
    Write-Host "O Windows precisa reiniciar para continuar. O script retomará a instalação no próximo login."
    Write-Host "Salve seu trabalho e reinicie o computador quando puder."
    exit 0
}

function Invoke-NvidiaDriverSetup {
    $nvidiaDevices = @(Get-CimInstance Win32_VideoController | Where-Object { $_.Name -match 'NVIDIA' })
    if ($nvidiaDevices.Count -eq 0) {
        Write-Host 'Nenhuma GPU NVIDIA encontrada. A instalação seguirá em modo CPU.'
        return $false
    }

    $nvidiaSmi = Join-Path $env:ProgramFiles 'NVIDIA Corporation\NVSMI\nvidia-smi.exe'
    if ((Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue) -or (Test-Path $nvidiaSmi)) {
        try {
            if (Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue) {
                & nvidia-smi.exe -L *> $null
            } else {
                & $nvidiaSmi -L *> $null
            }
            if ($LASTEXITCODE -eq 0) {
                Write-Host 'Driver NVIDIA do Windows já está funcional; será mantido.'
                return $true
            }
        } catch { }
    }

    $deviceName = ($nvidiaDevices | Select-Object -First 1).Name -replace '^NVIDIA\s+', ''
    Write-Step "Buscando o driver oficial da NVIDIA para $deviceName"
    $lookupUrl = 'https://www.nvidia.com/Download/API/lookupValueSearch.aspx?TypeID=3'
    [xml]$lookup = (Invoke-WebRequest -Uri $lookupUrl -UseBasicParsing -TimeoutSec 60).Content
    $gpu = @($lookup.LookupValueSearch.LookupValues.LookupValue | Where-Object {
        [string]::Equals($_.Name, $deviceName, [StringComparison]::OrdinalIgnoreCase)
    } | Select-Object -First 1)
    if ($gpu.Count -eq 0) {
        throw "A NVIDIA não retornou uma correspondência para '$deviceName'. Instale o driver para este modelo pelo site oficial da NVIDIA e execute o script novamente."
    }

    $osId = if ([Environment]::OSVersion.Version.Build -ge 22000) { 135 } else { 57 }
    $driverQuery = "https://www.nvidia.com/Download/processDriver.aspx?psid=$($gpu[0].ParentID)&pfid=$($gpu[0].Value)&osid=$osId&dtcid=1&dtid=1"
    $driverPage = (Invoke-WebRequest -Uri $driverQuery -UseBasicParsing -TimeoutSec 60).Content.Trim()
    if ($driverPage -notmatch 'driverResults\.aspx/(\d+)/') {
        throw 'A NVIDIA não retornou um driver compatível para esta versão do Windows.'
    }
    $downloadId = $Matches[1]
    $detailsUrl = "https://gfwsl.geforce.com/services_toolkit/services/com/nvidia/services/AjaxDriverService.php?func=GetDownloadDetails&downloadID=$downloadId"
    $details = Invoke-RestMethod -Uri $detailsUrl -TimeoutSec 60
    $downloadUrl = [string]$details.IDS[0].downloadInfo.DownloadURL
    $parsedUrl = [Uri]$downloadUrl
    if ($parsedUrl.Scheme -ne 'https' -or $parsedUrl.Host -notlike '*.nvidia.com') {
        throw 'O endereço de download retornado não pertence a um domínio oficial da NVIDIA.'
    }

    $installer = Join-Path $env:TEMP "nvidia-driver-$downloadId.exe"
    Invoke-WebRequest -Uri $downloadUrl -OutFile $installer -UseBasicParsing -TimeoutSec 1800
    $signature = Get-AuthenticodeSignature -FilePath $installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'NVIDIA') {
        Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
        throw 'O instalador baixado não passou na validação da assinatura digital da NVIDIA.'
    }

    Write-Host 'Instalando o driver de vídeo NVIDIA (instalador assinado, sem aplicativos adicionais)...'
    $process = Start-Process -FilePath $installer -ArgumentList '-s -n Display.Driver' -Wait -PassThru
    Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
    if ($process.ExitCode -eq 1) {
        Request-RestartAndResume 'O instalador NVIDIA concluiu e solicitou uma reinicialização.'
    }
    if ($process.ExitCode -ne 0) {
        throw "O instalador do driver NVIDIA falhou com código $($process.ExitCode)."
    }

    $driverReady = $false
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        if ((Test-Path $nvidiaSmi) -or (Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue)) {
            try {
                if (Test-Path $nvidiaSmi) { & $nvidiaSmi -L *> $null } else { & nvidia-smi.exe -L *> $null }
                if ($LASTEXITCODE -eq 0) { $driverReady = $true; break }
            } catch { }
        }
        Start-Sleep -Seconds 2
    }
    if (-not $driverReady) {
        Request-RestartAndResume 'O driver NVIDIA foi instalado, mas ainda não está ativo.'
    }

    Write-Host 'Driver NVIDIA instalado e funcional.'
    return $true
}

function New-Secret([int]$Bytes = 32) {
    $buffer = New-Object byte[] $Bytes
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) } finally { $rng.Dispose() }
    return ([BitConverter]::ToString($buffer) -replace '-', '').ToLowerInvariant()
}

function Ensure-EnvironmentFile {
    $envPath = Join-Path $ProjectRoot '.env'
    $assignments = @{}
    if (Test-Path $envPath) {
        foreach ($line in (Get-Content -LiteralPath $envPath)) {
            if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$') {
                $assignments[$Matches[1]] = $Matches[2].Trim()
            }
        }
    }

    $defaults = [ordered]@{
        POSTGRES_USER = 'aluno'
        POSTGRES_PASSWORD = (New-Secret)
        LITELLM_MASTER_KEY = "sk-local-$(New-Secret)"
        LITELLM_SALT_KEY = (New-Secret)
        NEO4J_AUTH = "neo4j/$(New-Secret)"
        N8N_ENCRYPTION_KEY = (New-Secret)
        FLOWISE_SECRET_KEY = (New-Secret)
        BROWSERLESS_TOKEN = (New-Secret)
        JUPYTER_TOKEN = (New-Secret)
        UPDATER_TOKEN = (New-Secret)
        WHISPER_MODEL = 'Systran/faster-whisper-small'
    }
    $missing = @($defaults.Keys | Where-Object { -not $assignments.ContainsKey($_) -or [string]::IsNullOrWhiteSpace($assignments[$_]) })
    if ($missing.Count -gt 0) {
        $generated = foreach ($key in $missing) { "$key=$($defaults[$key])" }
        Add-Content -LiteralPath $envPath -Value $generated -Encoding ASCII
        Write-Host "Chaves ausentes adicionadas ao .env: $($missing -join ', '). Os segredos não são exibidos."
    }
}

function Invoke-Wsl([string[]]$Arguments) {
    & wsl.exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Comando WSL falhou (código $LASTEXITCODE): wsl.exe $($Arguments -join ' ')"
    }
}

function Start-WslKeepAlive {
    $wslProcesses = @(Get-CimInstance Win32_Process -Filter "Name = 'wsl.exe'" -ErrorAction SilentlyContinue)
    $keepAliveRunning = @($wslProcesses | Where-Object {
        $_.CommandLine -match [regex]::Escape($Distro) -and $_.CommandLine -match '--exec sleep infinity'
    }).Count -gt 0
    if ($keepAliveRunning) { return }

    $arguments = @('--distribution', $Distro, '--user', 'root', '--exec', 'sleep', 'infinity') -join ' '
    $process = Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\wsl.exe') `
        -ArgumentList $arguments -WindowStyle Hidden -PassThru
    Start-Sleep -Seconds 2
    $process.Refresh()
    if ($process.HasExited) {
        throw "Não foi possível manter a distribuição $Distro ativa para os containers."
    }
}

if (-not (Test-Administrator)) {
    $currentPowerShell = (Get-Process -Id $PID).Path
    $quotedScript = '"' + $PSCommandPath + '"'
    $argumentString = "-NoProfile -ExecutionPolicy Bypass -File $quotedScript"
    if ($Resume) { $argumentString += ' -Resume' }
    Start-Process -FilePath $currentPowerShell -Verb RunAs -ArgumentList $argumentString
    exit 0
}

$osBuild = [Environment]::OSVersion.Version.Build
if ($osBuild -lt 19044) {
    throw 'É necessário Windows 10 21H2 (build 19044) ou superior, ou Windows 11, com virtualização habilitada na BIOS/UEFI.'
}

Write-Host 'Laboratório de IA: configuração do Windows, WSL 2, Ubuntu 24.04 e Docker.' -ForegroundColor Green
Write-Host 'A instalação pode baixar vários gigabytes de imagens e modelos.'

$wslFeature = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
$vmFeature = Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
$featuresChanged = $false
foreach ($feature in @($wslFeature, $vmFeature)) {
    if ($feature.State -ne 'Enabled') {
        Enable-WindowsOptionalFeature -Online -FeatureName $feature.FeatureName -All -NoRestart | Out-Null
        $featuresChanged = $true
    }
}
if ($featuresChanged) {
    Request-RestartAndResume 'Os componentes opcionais do WSL 2 foram habilitados.'
}

try {
    & wsl.exe --version *> $null
    $wslVersionAvailable = ($LASTEXITCODE -eq 0)
} catch { $wslVersionAvailable = $false }
if (-not $wslVersionAvailable) {
    & wsl.exe --install --no-distribution --web-download
    if ($LASTEXITCODE -ne 0) {
        Request-RestartAndResume 'O Windows solicitou reinicialização para concluir a instalação do WSL.'
    }
}
& wsl.exe --update
if ($LASTEXITCODE -ne 0) {
    Write-Warning 'A atualização automática do WSL não foi concluída; a instalação continuará e validará o WSL ao iniciar o Ubuntu.'
}
& wsl.exe --set-default-version 2
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível definir o WSL 2 como padrão. Atualize o WSL e tente novamente.' }

try {
    $gpuAvailable = Invoke-NvidiaDriverSetup
} catch {
    Write-Warning "Não foi possível preparar automaticamente o driver NVIDIA: $($_.Exception.Message)"
    Write-Warning 'O laboratório seguirá em modo CPU. Instale o driver correspondente no Windows e execute este script novamente para habilitar a GPU.'
    $gpuAvailable = $false
}

$installedDistros = @(& wsl.exe --list --quiet 2>$null | ForEach-Object { ($_ -replace "`0", '').Trim() } | Where-Object { $_ })
if ($Distro -notin $installedDistros) {
    $cloudInitDir = Join-Path $env:USERPROFILE '.cloud-init'
    $cloudInitFile = Join-Path $cloudInitDir "$Distro.user-data"
    if (Test-Path $cloudInitFile) {
        throw "Já existe configuração cloud-init em $cloudInitFile. Revise-a para não substituir dados de outro projeto."
    }
    New-Item -ItemType Directory -Path $cloudInitDir -Force | Out-Null
    @'
#cloud-config
users:
  - name: aluno
    gecos: Aluno do Laboratorio de IA
    shell: /bin/bash
    groups: [adm, dialout, cdrom, sudo, audio, video, plugdev, users]
    sudo: ALL=(ALL) NOPASSWD:ALL
    lock_passwd: true
write_files:
  - path: /etc/wsl.conf
    owner: root:root
    permissions: '0644'
    content: |
      [boot]
      systemd=true

      [user]
      default=aluno
'@ | Set-Content -LiteralPath $cloudInitFile -Encoding ASCII

    Write-Step "Instalando $Distro com usuário Linux automático"
    & wsl.exe --install --distribution $Distro --no-launch --web-download
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível instalar $Distro. Verifique a conexão e execute novamente; nenhuma distribuição WSL existente foi removida."
    }
}

Write-Step 'Inicializando Ubuntu e verificando systemd'
& wsl.exe -d $Distro -u root -- bash -lc 'test "$(cat /proc/1/comm)" = systemd'
if ($LASTEXITCODE -ne 0) {
    Invoke-Wsl @('--terminate', $Distro)
    & wsl.exe -d $Distro -u root -- bash -lc 'grep -q "^systemd=true$" /etc/wsl.conf || printf "\n[boot]\nsystemd=true\n" >> /etc/wsl.conf'
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível habilitar systemd em /etc/wsl.conf.' }
    Invoke-Wsl @('--terminate', $Distro)
    & wsl.exe -d $Distro -u root -- bash -lc 'test "$(cat /proc/1/comm)" = systemd'
    if ($LASTEXITCODE -ne 0) { throw 'O systemd não iniciou no Ubuntu WSL. Atualize o WSL e reinicie a distribuição.' }
}

Write-Step 'Instalando Docker Engine, Compose e NVIDIA Container Toolkit (se disponível)'
$linuxInstaller = ((& wsl.exe -d $Distro -u root -- wslpath -a (Join-Path $PSScriptRoot 'install_docker.sh')) -join "`n").Replace("`0", '').Trim()
if ($LASTEXITCODE -ne 0 -or -not $linuxInstaller) { throw 'Não foi possível converter o caminho do instalador para o Ubuntu.' }
& wsl.exe -d $Distro -u root -- bash $linuxInstaller
if ($LASTEXITCODE -eq 42) {
    Invoke-Wsl @('--terminate', $Distro)
    & wsl.exe -d $Distro -u root -- bash $linuxInstaller
}
if ($LASTEXITCODE -ne 0) { throw "A instalação do Docker no Ubuntu falhou (código $LASTEXITCODE)." }

Ensure-EnvironmentFile

$linuxProject = ((& wsl.exe -d $Distro -u root -- wslpath -a $ProjectRoot) -join "`n").Replace("`0", '').Trim()
if ($LASTEXITCODE -ne 0 -or -not $linuxProject) { throw 'Não foi possível converter o caminho do projeto para o Ubuntu.' }

Write-Step 'Mantendo o Ubuntu WSL ativo enquanto o laboratório está ligado'
Start-WslKeepAlive

$gpuInWsl = $false
& wsl.exe -d $Distro -u root -- bash -lc 'if [[ -x /usr/lib/wsl/lib/nvidia-smi ]]; then /usr/lib/wsl/lib/nvidia-smi -L >/dev/null 2>&1; else command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; fi'
if ($LASTEXITCODE -eq 0) { $gpuInWsl = $true }
if ($gpuAvailable -and -not $gpuInWsl) {
    if (-not $Resume) {
        Request-RestartAndResume 'O driver NVIDIA está ativo no Windows, mas ainda não apareceu no WSL.'
    }
    Write-Warning 'A GPU não apareceu no WSL após a reinicialização. O laboratório seguirá em modo CPU; você pode corrigir o WSL e executar novamente.'
    $gpuAvailable = $false
}

Write-Step 'Validando e iniciando os serviços do laboratório'
$composeArgs = @('--distribution', $Distro, '--user', 'root', '--cd', $linuxProject, '--', 'docker', 'compose')
if ($gpuInWsl) {
    Invoke-Wsl ($composeArgs + @('-f', 'docker-compose.yml', '-f', 'docker-compose.gpu.yml', '--profile', 'full', '--profile', 'management', 'config', '--quiet'))
    Invoke-Wsl ($composeArgs + @('-f', 'docker-compose.yml', '-f', 'docker-compose.gpu.yml', '--profile', 'full', '--profile', 'management', 'up', '-d', '--build'))
} else {
    Invoke-Wsl ($composeArgs + @('--profile', 'full', '--profile', 'management', 'config', '--quiet'))
    Invoke-Wsl ($composeArgs + @('--profile', 'full', '--profile', 'management', 'up', '-d', '--build'))
}

Write-Step 'Baixando os modelos base para chat e embeddings'
Invoke-Wsl ($composeArgs + @('exec', '-T', 'ollama', 'ollama', 'pull', 'llama3.2:3b'))
Invoke-Wsl ($composeArgs + @('exec', '-T', 'ollama', 'ollama', 'pull', 'nomic-embed-text'))

Write-Step 'Aguardando o dashboard ficar disponível'
$dashboardReady = $false
for ($attempt = 0; $attempt -lt 40; $attempt++) {
    try {
        $response = Invoke-WebRequest -Uri 'http://localhost:9090/health' -UseBasicParsing -TimeoutSec 3
        if ($response.StatusCode -eq 200) { $dashboardReady = $true; break }
    } catch { }
    Start-Sleep -Seconds 3
}
if (-not $dashboardReady) {
    throw 'Os containers foram iniciados, mas o dashboard não respondeu em http://localhost:9090. Consulte os logs com docker compose logs no Ubuntu.'
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $env:USERPROFILE ".cloud-init\$Distro.user-data") -Force -ErrorAction SilentlyContinue
Write-Host "`nLaboratório iniciado. Dashboard: http://localhost:9090/dashboard" -ForegroundColor Green
Write-Host 'Chat: http://localhost:3000 | n8n: http://localhost:5678 | LiteLLM: http://localhost:4000'
Write-Host 'JupyterLab: execute .\scripts\abrir_jupyter.ps1 para abrir com autenticação.'
Write-Host 'Portainer: http://localhost:9001'
if ($gpuInWsl) { Write-Host 'Ollama configurado para NVIDIA GPU.' } else { Write-Host 'Ollama configurado em modo CPU.' }
Start-Process 'http://localhost:9090/dashboard'
$jupyterHelper = Join-Path $PSScriptRoot 'abrir_jupyter.ps1'
Start-Process -FilePath 'powershell.exe' -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$jupyterHelper`"" -WindowStyle Hidden
