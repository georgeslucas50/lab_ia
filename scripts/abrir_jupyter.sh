#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

if [[ ! -r "$ENV_FILE" ]]; then
  printf 'Arquivo .env não encontrado. Execute scripts/preparar_ambiente_linux.sh primeiro.\n' >&2
  exit 1
fi

# Leia somente a chave necessária; não execute o conteúdo do arquivo como shell.
TOKEN="$(awk -F= '$1 == "JUPYTER_TOKEN" { value=substr($0, index($0, "=") + 1) } END { print value }' "$ENV_FILE")"
if [[ -z "$TOKEN" ]]; then
  printf 'JUPYTER_TOKEN está vazio. Execute novamente o instalador do laboratório.\n' >&2
  exit 1
fi

ready=false
for attempt in $(seq 1 20); do
  if curl -fsS -H "Authorization: token $TOKEN" http://127.0.0.1:8888/api/status >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 2
done
if [[ "$ready" != true ]]; then
  printf 'JupyterLab não respondeu em http://localhost:8888. Confira se o serviço está ativo no dashboard.\n' >&2
  exit 1
fi

URL="$(python3 -c 'import sys, urllib.parse; print("http://localhost:8888/lab?token=" + urllib.parse.quote(sys.argv[1], safe=""))' "$TOKEN")"
printf 'JupyterLab: %s\n' "$URL"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
fi
