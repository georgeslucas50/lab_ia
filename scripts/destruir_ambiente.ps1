$ErrorActionPreference = 'Stop'
$Distro = 'Ubuntu-24.04'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

Write-Host 'Este procedimento remove os containers, a rede e os volumes deste laboratório.' -ForegroundColor Yellow
Write-Host 'Os dados locais do PostgreSQL, Ollama, n8n, Qdrant e Neo4j serão apagados.'
$confirmation = Read-Host 'Digite APAGAR para confirmar'
if ($confirmation -cne 'APAGAR') {
    Write-Host 'Operação cancelada.'
    exit 0
}

$installed = @(& wsl.exe --list --quiet 2>$null | ForEach-Object { ($_ -replace "`0", '').Trim() } | Where-Object { $_ })
if ($Distro -notin $installed) { throw "A distribuição $Distro não está instalada." }
$linuxProject = ((& wsl.exe -d $Distro -u root -- wslpath -a $ProjectRoot) -join "`n").Replace("`0", '').Trim()
if ($LASTEXITCODE -ne 0 -or -not $linuxProject) { throw 'Não foi possível converter o caminho do projeto para o Ubuntu.' }

$composePrefix = @('--distribution', $Distro, '--user', 'root', '--cd', $linuxProject, '--', 'docker', 'compose')
$gpuOverlay = Join-Path $ProjectRoot 'docker-compose.gpu.yml'
$images = @()
if (Test-Path $gpuOverlay) {
    $configArgs = $composePrefix + @('-f', 'docker-compose.yml', '-f', 'docker-compose.gpu.yml', '--profile', 'full', '--profile', 'management', 'config', '--format', 'json')
    $imageArgs = $composePrefix + @('-f', 'docker-compose.yml', '-f', 'docker-compose.gpu.yml', '--profile', 'full', '--profile', 'management', 'images', '-q')
    $downArgs = $composePrefix + @('-f', 'docker-compose.yml', '-f', 'docker-compose.gpu.yml', '--profile', 'full', '--profile', 'management', 'down', '--remove-orphans')
} else {
    $configArgs = $composePrefix + @('--profile', 'full', '--profile', 'management', 'config', '--format', 'json')
    $imageArgs = $composePrefix + @('--profile', 'full', '--profile', 'management', 'images', '-q')
    $downArgs = $composePrefix + @('--profile', 'full', '--profile', 'management', 'down', '--remove-orphans')
}
$configOutput = @(& wsl.exe @configArgs)
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível identificar o projeto Docker; nenhum dado foi removido.' }
$projectLabel = (($configOutput -join "`n") | ConvertFrom-Json).name
if (-not $projectLabel) { throw 'O Compose não informou o nome deste projeto; nenhum dado foi removido.' }
$images = @(& wsl.exe @imageArgs | Where-Object { $_ })
if ($LASTEXITCODE -ne 0) { throw 'Não foi possível listar as imagens do projeto; nenhum dado foi removido.' }

& wsl.exe @downArgs
if ($LASTEXITCODE -ne 0) { throw 'O Docker Compose não conseguiu remover o laboratório.' }

$volumeNames = @(
    'ollama_storage', 'open-webui_storage', 'postgres_storage', 'n8n_storage', 'flowise_storage',
    'qdrant_storage', 'neo4j_data', 'neo4j_logs', 'redis_storage', 'whisper_storage',
    'tts_voices', 'tts_config', 'portainer_storage', 'jupyter_storage'
)
foreach ($volumeName in $volumeNames) {
    $volumeOwner = (& wsl.exe -d $Distro -u root -- docker volume inspect -f '{{ index .Labels "com.docker.compose.project" }}' $volumeName 2>$null | Select-Object -First 1)
    if ($LASTEXITCODE -eq 0 -and $volumeOwner -eq $projectLabel) {
        & wsl.exe -d $Distro -u root -- docker volume rm $volumeName | Out-Null
        if ($LASTEXITCODE -ne 0) { Write-Warning "Não foi possível remover o volume $volumeName (ele pode estar em uso)." }
    } elseif ($LASTEXITCODE -eq 0 -and $volumeOwner) {
        Write-Warning "O volume $volumeName pertence ao projeto '$volumeOwner' e foi preservado."
    }
}

$cleanImages = Read-Host 'Deseja remover também somente as imagens usadas por este laboratório? (S/N)'
if ($cleanImages -match '^[Ss]$' -and $images.Count -gt 0) {
    & wsl.exe -d $Distro -u root -- docker image rm @images
    if ($LASTEXITCODE -ne 0) {
        Write-Warning 'Algumas imagens não puderam ser removidas porque ainda são usadas por outro container.'
    }
}

Write-Host 'Laboratório removido. O Ubuntu WSL e os demais projetos Docker foram preservados.' -ForegroundColor Green
