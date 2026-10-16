#!/bin/sh
set -eu

if [ -z "${JUPYTER_TOKEN:-}" ]; then
    echo "JUPYTER_TOKEN não foi definido; configure-o no arquivo .env do projeto." >&2
    exit 1
fi

if [ ! -e "/home/jovyan/work/INICIO.md" ]; then
    cp -R -n /opt/course-materials/. /home/jovyan/work/
fi

exec jupyter lab --config=/etc/jupyter/jupyter_server_config.py "$@"
