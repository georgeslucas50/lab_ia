#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Execute este script como root dentro do Ubuntu WSL." >&2
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  echo "Não foi possível identificar a distribuição Linux." >&2
  exit 1
fi

# O WSL usa o driver NVIDIA instalado no Windows. Não instale nvidia-driver
# nem CUDA driver dentro desta distribuição.
. /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
  echo "Este laboratório foi validado para Ubuntu 24.04 LTS no WSL (encontrado: ${PRETTY_NAME:-desconhecido})." >&2
  exit 1
fi

if [[ "$(cat /proc/1/comm)" != "systemd" ]]; then
  echo "O systemd ainda não está ativo no Ubuntu WSL. Feche e reinicie somente a distribuição Ubuntu-24.04." >&2
  exit 42
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl git gnupg

docker_engine_ready() {
  command -v docker >/dev/null 2>&1 \
    && docker compose version >/dev/null 2>&1 \
    && systemctl list-unit-files docker.service --no-legend 2>/dev/null | grep -q '^docker\.service'
}

install_docker_engine() {
  local package
  local conflicts=()
  for package in docker.io docker-compose docker-compose-v2 docker-doc docker-buildx podman-docker containerd runc; do
    if dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null | grep -qx installed; then
      conflicts+=("$package")
    fi
  done
  if ((${#conflicts[@]} > 0)); then
    printf 'Foram encontrados pacotes Docker potencialmente conflitantes: %s\n' "${conflicts[*]}" >&2
    printf 'Revise a instalação existente antes de instalar o Docker Engine oficial. Os dados em /var/lib/docker não serão removidos.\n' >&2
    return 1
  fi

  cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-${VERSION_CODENAME}}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
  apt-get update || return 1
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || return 1
}

printf '\n==> Verificando Docker Engine e Docker Compose\n'
if docker_engine_ready; then
  printf 'Docker Engine e Compose já estão instalados; os pacotes existentes serão mantidos.\n'
else
  printf 'Instalando Docker Engine e Docker Compose oficiais para Ubuntu.\n'
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  install_docker_engine || {
    echo 'Não foi possível instalar o Docker Engine sem revisar a instalação existente.' >&2
    exit 1
  }
fi

if ! systemctl list-unit-files docker.service --no-legend 2>/dev/null | grep -q '^docker\.service'; then
  echo 'O serviço docker.service não foi encontrado. O laboratório requer Docker Engine no Ubuntu WSL.' >&2
  exit 1
fi

DEFAULT_USER="$(awk -F= '/^\[user\]/{in_user=1; next} /^\[/{in_user=0} in_user && $1=="default"{gsub(/[[:space:]]/, "", $2); print $2; exit}' /etc/wsl.conf 2>/dev/null || true)"
if [[ -n "$DEFAULT_USER" && "$DEFAULT_USER" != root ]] && id "$DEFAULT_USER" >/dev/null 2>&1; then
  usermod -aG docker "$DEFAULT_USER"
fi

gpu_detected=false
if { [[ -x /usr/lib/wsl/lib/nvidia-smi ]] && /usr/lib/wsl/lib/nvidia-smi -L >/dev/null 2>&1; } \
  || { command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; }; then
  gpu_detected=true
fi

configure_nvidia_runtime() {
  apt-get install -y --no-install-recommends ca-certificates curl gnupg || return 1
  install -m 0755 -d /usr/share/keyrings || return 1
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
    || return 1
  curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    | tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null \
    || return 1
  apt-get update || return 1
  apt-get install -y nvidia-container-toolkit || return 1
  nvidia-ctk runtime configure --runtime=docker || return 1
}

docker_needs_restart=false
if [[ "$gpu_detected" == true ]]; then
  printf '\n==> Configurando NVIDIA Container Toolkit para o driver do Windows\n'
  if dpkg-query -W -f='${db:Status-Status}' nvidia-container-toolkit 2>/dev/null | grep -qx installed \
    && docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -q 'nvidia'; then
    printf 'NVIDIA Container Toolkit e runtime já estão configurados.\n'
  elif configure_nvidia_runtime; then
    docker_needs_restart=true
    printf 'NVIDIA Container Toolkit configurado. O instalador principal validará o acesso à GPU pelo Docker.\n'
  else
    printf 'Não foi possível configurar o NVIDIA Container Toolkit; a instalação continuará e usará CPU.\n' >&2
  fi
else
  printf 'GPU NVIDIA não detectada dentro do WSL; o laboratório usará CPU.\n'
fi

systemctl enable containerd.service docker.service
if [[ "$docker_needs_restart" == true ]]; then
  systemctl restart docker.service
else
  systemctl start containerd.service docker.service
fi

docker version --format '{{.Server.Version}}' >/dev/null \
  || { echo 'O Docker Engine não respondeu depois de iniciado.' >&2; exit 1; }
docker compose version
echo "Docker Engine e Docker Compose estão prontos no Ubuntu WSL."
