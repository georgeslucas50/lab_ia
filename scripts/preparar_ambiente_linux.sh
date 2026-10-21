#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GPU_COMPOSE=false

fail() {
  printf 'Erro: %s\n' "$1" >&2
  exit 1
}

if [[ ${EUID} -eq 0 ]]; then
  fail 'Execute como seu usuário normal, sem sudo antes do nome do script. Ele solicitará sudo quando necessário.'
fi

if [[ ! -r /etc/os-release ]]; then
  fail 'Não foi possível identificar a distribuição Linux.'
fi

# O instalador automatizado usa os repositórios oficiais do Docker para Ubuntu.
. /etc/os-release
case "${ID:-}" in
  ubuntu) ;;
  *) fail "Este instalador automatizado requer Ubuntu LTS 22.04, 24.04 ou 26.04 (encontrado: ${PRETTY_NAME:-desconhecido})." ;;
esac
case "${VERSION_ID:-}" in
  22.04|24.04|26.04) ;;
  *) fail "Versão Ubuntu não validada. Use Ubuntu LTS 22.04, 24.04 ou 26.04 (encontrado: ${VERSION_ID:-desconhecida})." ;;
esac
if [[ "$(dpkg --print-architecture)" != amd64 ]]; then
  fail 'O laboratório foi preparado para Linux x86_64/amd64.'
fi
if [[ "$(cat /proc/1/comm)" != systemd ]]; then
  fail 'O Ubuntu precisa iniciar com systemd para gerenciar o Docker Engine. Execute este script em uma instalação Linux nativa, não no WSL.'
fi

# O atualizador do dashboard baixa as versões publicadas no origin do GitHub.
if ! git -C "$PROJECT_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  fail "Esta pasta não tem histórico Git. Clone o projeto com git clone (não use Download ZIP); veja as instruções do README."
fi
REMOTE_URL="$(git -C "$PROJECT_ROOT" remote get-url origin 2>/dev/null || true)"
if [[ -z "$REMOTE_URL" ]]; then
  fail 'O repositório não tem o remoto origin. Clone o laboratório pelo GitHub para habilitar a atualização no dashboard.'
fi
case "$REMOTE_URL" in
  https://github.com/*|git@github.com:*|ssh://git@github.com/*) ;;
  *) fail "O remoto origin não aponta para github.com ($REMOTE_URL). Configure o repositório correto antes de instalar." ;;
esac

printf '\nLaboratório de IA: instalação nativa no Ubuntu.\n'
printf 'Os arquivos Compose e os serviços são os mesmos da versão Windows/WSL.\n'
printf 'A instalação pode baixar vários gigabytes de imagens e modelos.\n\n'

sudo -v
sudo apt-get update
sudo apt-get install -y --no-install-recommends ca-certificates curl git gnupg openssl python3

install_docker_engine() {
  local package
  local conflicts=()
  for package in docker.io docker-compose docker-compose-v2 docker-doc docker-buildx podman-docker containerd runc; do
    if dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null | grep -qx installed; then
      conflicts+=("$package")
    fi
  done
  if ((${#conflicts[@]} > 0)); then
    printf 'Foram encontrados pacotes Docker conflitantes: %s\n' "${conflicts[*]}" >&2
    printf 'Revise a instalação existente antes de instalar o Docker Engine oficial. Os dados em /var/lib/docker não são removidos automaticamente.\n' >&2
    return 1
  fi

  . /etc/os-release
  sudo install -m 0755 -d /etc/apt/keyrings || return 1
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc || return 1
  sudo chmod a+r /etc/apt/keyrings/docker.asc || return 1
  sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF || return 1
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-${VERSION_CODENAME}}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
  sudo apt-get update || return 1
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || return 1
}

printf '==> Verificando Docker Engine e Docker Compose\n'
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  install_docker_engine || fail 'Não foi possível instalar o Docker sem revisar a instalação existente.'
fi
if ! systemctl list-unit-files docker.service --no-legend 2>/dev/null | grep -q '^docker\.service'; then
  fail 'O serviço docker.service não foi encontrado. O laboratório requer Docker Engine nativo, não apenas Docker Desktop.'
fi
sudo systemctl enable --now docker.service containerd.service
sudo docker version --format '{{.Server.Version}}' >/dev/null \
  || fail 'O Docker Engine não respondeu. Confira: sudo systemctl status docker'
sudo docker compose version

configure_nvidia() {
  if ! command -v nvidia-smi >/dev/null 2>&1 || ! nvidia-smi -L >/dev/null 2>&1; then
    printf 'GPU NVIDIA/driver funcional não detectado no host; o Ollama usará CPU.\n'
    return 1
  fi

  printf '\n==> Instalando NVIDIA Container Toolkit para o driver NVIDIA já existente no Ubuntu\n'
  # Em Linux nativo, o driver pertence ao host. O instalador não instala nem troca drivers.
  sudo apt-get install -y --no-install-recommends ca-certificates curl gnupg || return 1
  sudo install -m 0755 -d /usr/share/keyrings || return 1
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | sudo gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
    || return 1
  curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null \
    || return 1
  sudo apt-get update || return 1
  sudo apt-get install -y nvidia-container-toolkit || return 1
  sudo nvidia-ctk runtime configure --runtime=docker || return 1
  printf 'A configuração da GPU reiniciará o Docker Engine; containers de outros projetos podem reiniciar brevemente.\n'
  sudo systemctl restart docker.service || return 1

  # O teste confirma que o daemon de containers recebeu a GPU antes de ativar o overlay.
  sudo docker run --rm --runtime=nvidia --gpus all ubuntu:24.04 nvidia-smi >/dev/null 2>&1
}

if configure_nvidia; then
  GPU_COMPOSE=true
  printf 'Toolkit NVIDIA pronto; o Ollama usará a GPU.\n'
else
  printf 'O laboratório seguirá em CPU. Para GPU, instale primeiro o driver NVIDIA oficial do Ubuntu e execute novamente este script.\n'
fi

printf '\n==> Criando ou completando o arquivo local .env\n'
if [[ ! -e "$PROJECT_ROOT/.env" ]]; then
  cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
fi
chmod 600 "$PROJECT_ROOT/.env"

# Preserve configurações existentes e substitua somente valores vazios ou os marcadores do exemplo.
python3 - "$PROJECT_ROOT/.env" <<'PY'
import re
import secrets
import sys
from pathlib import Path

path = Path(sys.argv[1])
defaults = {
    "POSTGRES_USER": "aluno",
    "POSTGRES_PASSWORD": secrets.token_hex(32),
    "LITELLM_MASTER_KEY": "sk-local-" + secrets.token_hex(32),
    "LITELLM_SALT_KEY": secrets.token_hex(32),
    "NEO4J_AUTH": "neo4j/" + secrets.token_hex(32),
    "N8N_ENCRYPTION_KEY": secrets.token_hex(32),
    "FLOWISE_SECRET_KEY": secrets.token_hex(32),
    "BROWSERLESS_TOKEN": secrets.token_hex(32),
    "JUPYTER_TOKEN": secrets.token_hex(32),
    "UPDATER_TOKEN": secrets.token_hex(32),
    "WHISPER_MODEL": "Systran/faster-whisper-small",
}
lines = path.read_text(encoding="utf-8").splitlines()
seen = set()
output = []
for line in lines:
    match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$", line)
    if not match or match.group(1) not in defaults:
        output.append(line)
        continue
    key = match.group(1)
    if key in seen:
        continue
    seen.add(key)
    value = match.group(2).strip()
    if not value or "SUBSTITUA_POR_SEGREDO_ALEATORIO" in value:
        value = defaults[key]
    output.append(f"{key}={value}")
for key, value in defaults.items():
    if key not in seen:
        output.append(f"{key}={value}")
path.write_text("\n".join(output) + "\n", encoding="utf-8")
PY

cd "$PROJECT_ROOT"
COMPOSE_FILES=(-f docker-compose.yml)
if [[ "$GPU_COMPOSE" == true ]]; then
  COMPOSE_FILES+=(-f docker-compose.gpu.yml)
fi
PROFILES=(--profile full --profile management)

printf '\n==> Validando e iniciando os serviços do laboratório\n'
sudo docker compose "${COMPOSE_FILES[@]}" "${PROFILES[@]}" config --quiet
sudo docker compose "${COMPOSE_FILES[@]}" "${PROFILES[@]}" up -d --build

printf '\n==> Aguardando o Ollama\n'
ollama_ready=false
for attempt in $(seq 1 120); do
  if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    ollama_ready=true
    break
  fi
  sleep 3
done
if [[ "$ollama_ready" != true ]]; then
  fail 'Os containers foram iniciados, mas o Ollama não respondeu. Consulte: sudo docker compose logs ollama'
fi

printf '\n==> Baixando os modelos iniciais para chat e embeddings\n'
sudo docker compose "${COMPOSE_FILES[@]}" exec -T ollama ollama pull llama3.2:3b
sudo docker compose "${COMPOSE_FILES[@]}" exec -T ollama ollama pull nomic-embed-text

printf '\n==> Aguardando o dashboard\n'
dashboard_ready=false
for attempt in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:9090/health >/dev/null 2>&1; then
    dashboard_ready=true
    break
  fi
  sleep 3
done
if [[ "$dashboard_ready" != true ]]; then
  fail 'Os containers foram iniciados, mas o dashboard não respondeu em http://localhost:9090. Consulte: sudo docker compose logs dashboard'
fi

if ! id -nG "${USER}" | tr ' ' '\n' | grep -qx docker; then
  sudo usermod -aG docker "$USER"
  printf '\nSeu usuário foi adicionado ao grupo docker. Encerre e reabra a sessão do Linux para executar docker sem sudo.\n'
  printf 'O grupo docker concede privilégios equivalentes a root; use essa conta somente com pessoas de confiança.\n'
fi

printf '\nLaboratório iniciado. Dashboard: http://localhost:9090/dashboard\n'
printf 'Página inicial: http://localhost:9090\n'
printf 'JupyterLab: execute ./scripts/abrir_jupyter.sh para abrir com autenticação.\n'
printf 'Portainer: http://localhost:9001\n'
if [[ "$GPU_COMPOSE" == true ]]; then
  printf 'Ollama configurado para NVIDIA GPU.\n'
else
  printf 'Ollama configurado em modo CPU.\n'
fi

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open http://localhost:9090/dashboard >/dev/null 2>&1 || true
fi
