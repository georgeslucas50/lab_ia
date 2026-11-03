#!/usr/bin/env bash
set -Eeuo pipefail

if [[ -z "${1:-}" ]]; then
  echo "Informe o caminho do projeto clonado." >&2
  exit 2
fi
PROJECT_ROOT="$(cd -- "$1" && pwd)"
TIMEOUT_SECONDS="${LAB_SERVICE_START_TIMEOUT:-1800}"
POLL_SECONDS=5

cd "$PROJECT_ROOT"
compose=(docker compose --profile full --profile management)
services="$("${compose[@]}" config --services)"
deadline=$((SECONDS + TIMEOUT_SECONDS))

printf 'Aguardando %s serviços (até %s minutos)...\n' \
  "$(wc -w <<< "$services" | tr -d ' ')" "$((TIMEOUT_SECONDS / 60))"

while (( SECONDS < deadline )); do
  ids="$("${compose[@]}" ps --all --quiet)"
  declare -A service_state=()
  declare -A service_health=()

  if [[ -n "$ids" ]]; then
    # Compose labels each container with its service name. Inspect all containers
    # in one Docker call to keep polling inexpensive.
    while IFS='|' read -r service state health; do
      [[ -n "$service" ]] || continue
      service_state["$service"]="$state"
      service_health["$service"]="$health"
    done < <(
      # shellcheck disable=SC2086
      docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}|{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' $ids
    )
  fi

  pending=()
  unhealthy=()
  for service in $services; do
    state="${service_state[$service]:-missing}"
    health="${service_health[$service]:-missing}"
    if [[ "$state" != running || ( "$health" != healthy && "$health" != none ) ]]; then
      pending+=("$service ($state/$health)")
      [[ "$health" != unhealthy ]] || unhealthy+=("$service")
    fi
  done

  if ((${#pending[@]} == 0)); then
    printf 'Todos os serviços estão em execução; healthchecks configurados estão saudáveis.\n'
    exit 0
  fi

  if ((${#unhealthy[@]} > 0)); then
    printf 'Healthcheck falhou em: %s\n' "${unhealthy[*]}" >&2
    break
  fi

  sleep "$POLL_SECONDS"
done

printf '\nAlguns serviços não ficaram prontos:\n' >&2
for item in "${pending[@]}"; do
  printf '  - %s\n' "$item" >&2
done
printf '\nEstado atual dos containers:\n' >&2
"${compose[@]}" ps --all >&2 || true
printf '\nConsulte os logs com: docker compose --profile full --profile management logs --tail 100 NOME_DO_SERVICO\n' >&2
exit 1
