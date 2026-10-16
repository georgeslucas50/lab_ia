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

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-${VERSION_CODENAME}}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

DEFAULT_USER="$(awk -F= '/^\[user\]/{in_user=1; next} /^\[/{in_user=0} in_user && $1=="default"{gsub(/[[:space:]]/, "", $2); print $2; exit}' /etc/wsl.conf 2>/dev/null || true)"
if [[ -n "${DEFAULT_USER}" && "${DEFAULT_USER}" != "root" ]]; then
  usermod -aG docker "${DEFAULT_USER}"
fi

if { [[ -x /usr/lib/wsl/lib/nvidia-smi ]] && /usr/lib/wsl/lib/nvidia-smi -L >/dev/null 2>&1; } \
  || { command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; }; then
  echo "GPU NVIDIA detectada no WSL; instalando somente o NVIDIA Container Toolkit."
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    > /etc/apt/sources.list.d/nvidia-container-toolkit.list
  apt-get update
  apt-get install -y nvidia-container-toolkit
  nvidia-ctk runtime configure --runtime=docker
else
  echo "GPU NVIDIA não detectada dentro do WSL; o laboratório iniciará em modo CPU."
fi

systemctl enable docker.service containerd.service
systemctl restart docker.service

docker version --format '{{.Server.Version}}' >/dev/null
docker compose version
echo "Docker Engine e Docker Compose estão prontos no Ubuntu WSL."
