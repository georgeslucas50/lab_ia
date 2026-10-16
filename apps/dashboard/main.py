import asyncio
import json
import os
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Literal
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from urllib.parse import quote, urlsplit

app = FastAPI(title="AI Infrastructure Dashboard", version="1.0.0")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

SERVICES_DATA = [
    {
        "id": "dashboard",
        "category": "Gestão & Administração",
        "name": "Dashboard do Laboratório",
        "icon": "🎛️",
        "has_ui": True,
        "port": 9090,
        "url": "http://localhost:9090/dashboard",
        "internal_url": "http://dashboard:9090",
        "description": "Painel do laboratório com acesso aos serviços, manuais, diagrama e verificação de saúde.",
        "check_url": "http://dashboard:9090/health"
    },
    # 1. Telas & Interfaces de Usuário
    {
        "id": "open-webui",
        "category": "Telas & Interfaces de Usuário",
        "name": "Open WebUI",
        "icon": "💬",
        "has_ui": True,
        "port": 3000,
        "url": "http://localhost:3000",
        "internal_url": "http://open-webui:8080",
        "description": "Seu 'ChatGPT' privado local. Permite conversar com os modelos de linguagem do Ollama, fazer upload de documentos para RAG e interagir via voz (transcrição STT e síntese TTS).",
        "check_url": "http://open-webui:8080/health"
    },
    {
        "id": "n8n",
        "category": "Telas & Interfaces de Usuário",
        "name": "n8n Orchestrator",
        "icon": "⚡",
        "has_ui": True,
        "port": 5678,
        "url": "http://localhost:5678",
        "internal_url": "http://n8n:5678",
        "description": "Plataforma visual de automação de workflows e orquestração de agentes. Conecta modelos de IA a centenas de APIs externas, bancos de dados e webhooks.",
        "check_url": "http://n8n:5678/healthz"
    },
    {
        "id": "flowise",
        "category": "Telas & Interfaces de Usuário",
        "name": "Flowise AI",
        "icon": "🧩",
        "has_ui": True,
        "port": 3001,
        "url": "http://localhost:3001",
        "internal_url": "http://flowise:3000",
        "description": "Construtor no-code/low-code no estilo LangChain. Permite criar robôs de IA, pipelines de RAG e agentes autônomos arrastando e soltando blocos visuais.",
        "check_url": "http://flowise:3000/"
    },
    {
        "id": "portainer",
        "category": "Telas & Interfaces de Usuário",
        "name": "Portainer CE",
        "icon": "🐳",
        "has_ui": True,
        "port": 9001,
        "url": "http://localhost:9001",
        "internal_url": "http://portainer:9000",
        "description": "Gerenciador gráfico completo do Docker. Exibe métricas de uso de CPU/RAM, permite visualizar logs dos containers em tempo real e abrir terminal interativo.",
        "check_url": "http://portainer:9000/"
    },
    {
        "id": "jupyter",
        "category": "Notebooks & Desenvolvimento",
        "name": "JupyterLab",
        "icon": "📓",
        "has_ui": True,
        "port": 8888,
        "url": "http://localhost:8888/lab",
        "internal_url": "http://jupyter:8888",
        "description": "Ambiente persistente de notebooks Python com bibliotecas de ciência de dados e clientes de IA. Para abrir já autenticado, execute scripts\\abrir_jupyter.ps1; as APIs internas do laboratório estão disponíveis por variáveis de ambiente.",
        "check_type": "tcp",
        "check_host": "jupyter",
        "check_port": 8888
    },

    # 2. AI Gateway & Observabilidade
    {
        "id": "litellm",
        "category": "AI Gateway & Observabilidade",
        "name": "LiteLLM Proxy",
        "icon": "🚦",
        "has_ui": True,
        "port": 4000,
        "url": "http://localhost:4000",
        "internal_url": "http://litellm:4000",
        "description": "Gateway de IA unificado compatível com a API da OpenAI (/v1). Gerencia chaves de API, limites de consumo, cache semântico no Redis e envia traces para o Phoenix.",
        "check_url": "http://litellm:4000/health/liveliness"
    },
    {
        "id": "phoenix",
        "category": "AI Gateway & Observabilidade",
        "name": "Arize Phoenix",
        "icon": "📊",
        "has_ui": True,
        "port": 6006,
        "url": "http://localhost:6006",
        "internal_url": "http://phoenix:6006",
        "description": "Plataforma de observabilidade LLMOps e OpenTelemetry. Monitora a latência das respostas, fluxo de execução dos agentes e avaliação da precisão do RAG.",
        "check_url": "http://phoenix:6006/"
    },

    # 3. Cérebro de IA & Voz
    {
        "id": "ollama",
        "category": "Cérebro de IA & Voz",
        "name": "Ollama LLM Engine",
        "icon": "🧠",
        "has_ui": False,
        "port": 11434,
        "url": "http://localhost:11434",
        "internal_url": "http://ollama:11434",
        "description": "Motor local de modelos de linguagem e embeddings. Usa a GPU NVIDIA quando o driver e o Container Toolkit estão disponíveis; também funciona em CPU.",
        "check_url": "http://ollama:11434/"
    },
    {
        "id": "whisper-stt",
        "category": "Cérebro de IA & Voz",
        "name": "Faster-Whisper STT",
        "icon": "🎙️",
        "has_ui": False,
        "port": 8001,
        "url": "http://localhost:8001/docs",
        "internal_url": "http://whisper-stt:8000",
        "description": "Servidor de transcrição de voz (Speech-to-Text). Converte áudio e comandos de voz em texto usando CPU int8 otimizada sem consumir a VRAM da GPU.",
        "check_url": "http://whisper-stt:8000/health"
    },
    {
        "id": "openedai-tts",
        "category": "Cérebro de IA & Voz",
        "name": "OpenEDAI Speech TTS",
        "icon": "🔊",
        "has_ui": False,
        "port": 8002,
        "url": "http://localhost:8002/docs",
        "internal_url": "http://openedai-tts:8000",
        "description": "Servidor de síntese de voz neural (Text-to-Speech). Converte as respostas de texto da IA em fala natural usando vozes Piper em CPU.",
        "check_url": "http://openedai-tts:8000/health"
    },

    # 4. Ferramentas Agênticas & OCR
    {
        "id": "python-mcp",
        "category": "Ferramentas Agênticas & OCR",
        "name": "Python MCP Server",
        "icon": "🛠️",
        "has_ui": True,
        "port": 8000,
        "url": "http://localhost:8000/docs",
        "internal_url": "http://python-mcp:8000",
        "description": "Servidor customizado FastMCP + FastAPI. Expõe ferramentas de documentos, navegação e cache Redis pela API REST e MCP em /mcp.",
        "check_url": "http://python-mcp:8000/health"
    },
    {
        "id": "tika",
        "category": "Ferramentas Agênticas & OCR",
        "name": "Apache Tika OCR",
        "icon": "📄",
        "has_ui": False,
        "port": 9998,
        "url": "http://localhost:9998",
        "internal_url": "http://tika:9998",
        "description": "Servidor de extração de texto e OCR Tesseract. Extrai conteúdo limpo de PDFs pesados, escaneados e arquivos de imagem para uso no RAG.",
        "check_url": "http://tika:9998/version"
    },
    {
        "id": "browserless",
        "category": "Ferramentas Agênticas & OCR",
        "name": "Browserless Scraping",
        "icon": "🌐",
        "has_ui": False,
        "port": 3002,
        "url": "http://localhost:3002",
        "internal_url": "http://browserless:3000",
        "description": "Navegador Chromium Headless. Permite que os agentes simulem navegação humana real, cliquem em botões e extraiam dados de páginas dinâmicas com JS.",
        "check_url": "http://browserless:3000/pressure"
    },

    # 5. Bancos de Dados & Memórias
    {
        "id": "qdrant",
        "category": "Bancos de Dados & Memórias",
        "name": "Qdrant Vector DB",
        "icon": "📚",
        "has_ui": True,
        "port": 6333,
        "url": "http://localhost:6333/dashboard",
        "internal_url": "http://qdrant:6333",
        "description": "Banco de dados vetorial de alta velocidade. Armazena e pesquisa vetores de embeddings para busca semântica em arquivos e PDFs (Vector RAG).",
        "check_url": "http://qdrant:6333/readyz"
    },
    {
        "id": "neo4j",
        "category": "Bancos de Dados & Memórias",
        "name": "Neo4j Graph DB",
        "icon": "🕸️",
        "has_ui": True,
        "port": 7474,
        "url": "http://localhost:7474",
        "internal_url": "bolt://neo4j:7687",
        "description": "Banco de dados em grafo. Representa entidades, conceitos e relacionamentos complexos criando mapas mentais para raciocínio avançado (GraphRAG).",
        "check_url": "http://neo4j:7474/"
    },
    {
        "id": "redis",
        "category": "Bancos de Dados & Memórias",
        "name": "Redis Cache",
        "icon": "⚡",
        "has_ui": False,
        "port": 6379,
        "url": "http://localhost:6379",
        "internal_url": "redis:6379",
        "description": "Memória in-memory de altíssima velocidade. Armazena o cache de respostas de IA no LiteLLM e estados de curto prazo dos agentes do n8n e Flowise.",
        "check_type": "tcp",
        "check_host": "redis",
        "check_port": 6379
    },
    {
        "id": "postgres",
        "category": "Bancos de Dados & Memórias",
        "name": "PostgreSQL DB",
        "icon": "🗄️",
        "has_ui": False,
        "port": 5432,
        "url": "http://localhost:5432",
        "internal_url": "postgres:5432",
        "description": "Cofre relacional principal. Armazena os 5 bancos de dados da infraestrutura (litellm_db, n8n_db, flowise_db, openwebui_db, phoenix_db).",
        "check_type": "tcp",
        "check_host": "postgres",
        "check_port": 5432
    }
]

# A interface pode controlar apenas serviços declarados acima. O container do
# próprio dashboard é excluído para evitar que o aluno desligue o painel usado
# para religá-lo.
CONTROLLED_SERVICE_IDS = {service["id"] for service in SERVICES_DATA if service["id"] != "dashboard"}
LOCAL_ORIGINS = {"http://localhost:9090", "http://127.0.0.1:9090"}
LOCAL_HOSTS = {"localhost:9090", "127.0.0.1:9090"}
UPDATE_STATE_FILE = Path("/var/lib/lab-update/update-state.json")
UPDATE_CONFIRMATION = "ATUALIZAR LABORATÓRIO"

# Somente estes volumes nomeados e bancos de dados podem ser apagados pelo
# painel. PostgreSQL é compartilhado e, por isso, seu reset tem impacto amplo.
RESET_VOLUME_NAMES = (
    "ollama_storage",
    "open-webui_storage",
    "postgres_storage",
    "n8n_storage",
    "flowise_storage",
    "qdrant_storage",
    "neo4j_data",
    "neo4j_logs",
    "redis_storage",
    "whisper_storage",
    "tts_voices",
    "tts_config",
    "portainer_storage",
    "jupyter_storage",
)

RESET_TARGETS = {
    "open-webui": {"volumes": ["open-webui_storage"], "database": "openwebui_db"},
    "n8n": {"volumes": ["n8n_storage"], "database": "n8n_db"},
    "flowise": {"volumes": ["flowise_storage"], "database": "flowise_db"},
    "litellm": {
        "volumes": ["redis_storage"],
        "database": "litellm_db",
        "stop_services": ["redis"],
        "warning": "O LiteLLM usa o Redis compartilhado para cache; este reset também limpa a memória do MCP e outros caches.",
    },
    "phoenix": {"volumes": [], "database": "phoenix_db"},
    "ollama": {"volumes": ["ollama_storage"], "restore_models": True},
    "whisper-stt": {"volumes": ["whisper_storage"]},
    "openedai-tts": {
        "volumes": ["tts_voices", "tts_config"],
        "warning": "Vozes adicionadas e configurações personalizadas serão removidas; os arquivos padrão da imagem serão restaurados.",
    },
    "python-mcp": {
        "volumes": ["redis_storage"],
        "stop_services": ["redis"],
        "warning": "A memória do MCP usa o Redis compartilhado; este reset também apaga o cache usado por LiteLLM e outros serviços.",
    },
    "tika": {"volumes": []},
    "browserless": {"volumes": []},
    "qdrant": {"volumes": ["qdrant_storage"]},
    "neo4j": {"volumes": ["neo4j_data", "neo4j_logs"]},
    "redis": {"volumes": ["redis_storage"], "warning": "O Redis também guarda cache usado por outros serviços."},
    "postgres": {
        "volumes": ["postgres_storage"],
        "warning": "O PostgreSQL é compartilhado: este reset apaga também os bancos de n8n, Flowise, Open WebUI, LiteLLM e Phoenix.",
        "stack_reset": True,
    },
    "portainer": {"volumes": ["portainer_storage"]},
    "jupyter": {"volumes": ["jupyter_storage"], "warning": "Os notebooks e arquivos salvos no diretório de trabalho serão apagados."},
}
RESET_START_ORDER = (
    "postgres", "redis", "ollama", "phoenix", "litellm", "open-webui", "n8n", "flowise",
    "tika", "whisper-stt", "openedai-tts", "python-mcp", "qdrant", "neo4j", "browserless",
    "portainer", "jupyter",
)
DEFAULT_OLLAMA_MODELS = ("llama3.2:3b", "nomic-embed-text")
RESET_VOLUME_SEEDS = {
    "tts_voices": ("openedai-tts", "/app/voices"),
    "tts_config": ("openedai-tts", "/app/config"),
}
RESET_JOBS = {}
RESET_JOBS_LOCK = threading.Lock()
ACTIVE_RESET_JOB = None


class ServiceAction(BaseModel):
    action: Literal["start", "stop"]


class ResetRequest(BaseModel):
    confirmation: str


class UpdateRequest(BaseModel):
    confirmation: str


def get_docker_scope():
    """Return a Docker client scoped to the Compose project running this app."""
    client = httpx.Client(
        base_url="http://docker",
        transport=httpx.HTTPTransport(uds="/var/run/docker.sock"),
        timeout=5.0,
    )
    try:
        container_id = os.environ.get("HOSTNAME", "")
        response = client.get(f"/containers/{container_id}/json")
        if response.status_code == 404:
            raise HTTPException(status_code=503, detail="O dashboard não conseguiu identificar o projeto Compose.")
        response.raise_for_status()
        labels = response.json().get("Config", {}).get("Labels", {}) or {}
        project = labels.get("com.docker.compose.project")
        if not project:
            client.close()
            raise HTTPException(status_code=503, detail="O dashboard não conseguiu identificar o projeto Compose.")
        return client, project
    except HTTPException:
        client.close()
        raise
    except Exception as exc:
        client.close()
        raise HTTPException(status_code=503, detail="Docker indisponível para controlar os serviços.") from exc


def get_project_containers(client, project, service_id=None):
    labels = [f"com.docker.compose.project={project}"]
    if service_id:
        labels.append(f"com.docker.compose.service={service_id}")
    filters = json.dumps({"label": labels})
    response = client.get("/containers/json", params={"all": "true", "filters": filters})
    response.raise_for_status()
    return response.json()


def validate_local_control_request(request: Request):
    host = request.headers.get("host", "").lower()
    origin = request.headers.get("origin")
    if host not in LOCAL_HOSTS or origin not in LOCAL_ORIGINS:
        raise HTTPException(status_code=403, detail="Ações de controle aceitas somente pelo dashboard local.")
    if urlsplit(origin).netloc.lower() != host:
        raise HTTPException(status_code=403, detail="Origem da requisição inválida.")


def read_update_job():
    try:
        state = json.loads(UPDATE_STATE_FILE.read_text(encoding="utf-8"))
        return state.get("job")
    except (OSError, json.JSONDecodeError):
        return None


def update_is_active():
    job = read_update_job() or {}
    return job.get("status") in {"queued", "running"}


def call_update_service(method, path, body=None, timeout=20):
    base_url = os.environ.get("SYSTEM_UPDATER_URL", "http://system-updater:8091").rstrip("/")
    token = os.environ.get("SYSTEM_UPDATER_TOKEN", "")
    if not token:
        raise HTTPException(status_code=503, detail="O atualizador ainda não está configurado. Execute novamente o instalador do laboratório.")
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.request(
                method,
                f"{base_url}{path}",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
            )
    except Exception as exc:
        raise HTTPException(status_code=503, detail="O serviço de atualização está indisponível. Verifique o Docker e tente novamente.") from exc
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail=payload.get("detail", "O serviço de atualização não concluiu a solicitação."),
        )
    return payload


def _set_reset_job(job_id, **updates):
    with RESET_JOBS_LOCK:
        job = RESET_JOBS.get(job_id)
        if not job:
            return
        job.update(updates)
        job["updatedAt"] = time.time()


def _reset_job_snapshot(job):
    return {key: job[key] for key in ("id", "scope", "service", "status", "phase", "message", "updatedAt") if key in job}


def _project_volume(client, project, name):
    response = client.get(f"/volumes/{quote(name, safe='')}")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    volume = response.json()
    owner = (volume.get("Labels") or {}).get("com.docker.compose.project")
    if owner != project:
        raise RuntimeError(f"O volume '{name}' não pertence ao projeto Compose deste laboratório; ele foi preservado.")
    return volume


def _preflight_reset_volumes(client, project, names, project_containers):
    volumes = {}
    for name in names:
        volume = _project_volume(client, project, name)
        if volume:
            volumes[name] = volume

    if not volumes:
        return []

    project_ids = {container["Id"] for container in project_containers}
    all_containers = client.get("/containers/json", params={"all": "true"})
    all_containers.raise_for_status()
    for container in all_containers.json():
        if container["Id"] in project_ids:
            continue
        for mount in container.get("Mounts", []):
            name = mount.get("Name")
            if name in volumes:
                raise RuntimeError(f"O volume '{name}' está conectado a outro container e não será apagado.")
    return list(volumes)


def _stop_container(client, container_id):
    response = client.post(f"/containers/{container_id}/stop", params={"t": 15}, timeout=20.0)
    if response.status_code not in {204, 304, 404}:
        response.raise_for_status()


def _start_container(client, container_id):
    response = client.post(f"/containers/{container_id}/start", timeout=20.0)
    if response.status_code not in {204, 304}:
        response.raise_for_status()


def _wait_for_healthy_container(client, container_id, service_name, timeout_seconds=120):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = client.get(f"/containers/{container_id}/json")
        if response.status_code == 404:
            raise RuntimeError(f"O container {service_name} deixou de existir durante a restauração.")
        response.raise_for_status()
        state = response.json().get("State", {})
        if not state.get("Running"):
            raise RuntimeError(f"O container {service_name} parou durante a restauração.")
        health = state.get("Health", {}).get("Status")
        if health == "healthy":
            return
        if health == "unhealthy":
            raise RuntimeError(f"O container {service_name} iniciou, mas não ficou saudável.")
        time.sleep(2)
    raise RuntimeError(f"O container {service_name} não ficou saudável dentro do tempo esperado.")


def _clear_project_volumes(client, project, volume_names):
    if not volume_names:
        return

    project_containers = get_project_containers(client, project)
    dashboard = next(
        (container for container in project_containers
         if (container.get("Labels") or {}).get("com.docker.compose.service") == "dashboard"),
        None,
    )
    if not dashboard:
        raise RuntimeError("Não foi possível localizar o container do dashboard para limpar os dados.")

    detail_response = client.get(f"/containers/{dashboard['Id']}/json")
    detail_response.raise_for_status()
    image = detail_response.json().get("Image")
    if not image:
        raise RuntimeError("Não foi possível localizar a imagem local do dashboard para a limpeza segura.")

    targets = [f"/reset/volume-{index}" for index in range(len(volume_names))]
    clear_script = (
        "import os, shutil, sys\n"
        "for root in sys.argv[1:]:\n"
        "    for entry in os.scandir(root):\n"
        "        if entry.name == 'lost+found':\n"
        "            continue\n"
        "        if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):\n"
        "            os.unlink(entry.path)\n"
        "        else:\n"
        "            shutil.rmtree(entry.path)\n"
    )
    helper_name = f"laboratorio-reset-{uuid.uuid4().hex[:12]}"
    mounts = [
        {
            "Type": "volume",
            "Source": name,
            "Target": targets[index],
            "ReadOnly": False,
            "VolumeOptions": {"NoCopy": True},
        }
        for index, name in enumerate(volume_names)
    ]
    payload = {
        "Image": image,
        "Cmd": ["python", "-c", clear_script, *targets],
        "Labels": {"com.escom.dashboard.reset-helper": "true"},
        "WorkingDir": "/tmp",
        "HostConfig": {
            "AutoRemove": False,
            "NetworkMode": "none",
            "RestartPolicy": {"Name": "no"},
            "Mounts": mounts,
        },
    }

    create_response = client.post("/containers/create", params={"name": helper_name}, json=payload)
    create_response.raise_for_status()
    helper_id = create_response.json()["Id"]
    try:
        start_response = client.post(f"/containers/{helper_id}/start", timeout=20.0)
        if start_response.status_code not in {204, 304}:
            start_response.raise_for_status()
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            inspect_response = client.get(f"/containers/{helper_id}/json")
            inspect_response.raise_for_status()
            state = inspect_response.json().get("State", {})
            if state.get("Status") == "exited":
                if state.get("ExitCode") != 0:
                    raise RuntimeError("A limpeza de dados foi interrompida; revise os containers antes de repetir.")
                return
            time.sleep(0.5)
        raise RuntimeError("A limpeza de dados excedeu o tempo esperado.")
    finally:
        client.delete(f"/containers/{helper_id}", params={"force": "true", "v": "false"})


def _restore_image_seeded_volumes(client, volume_names, by_service):
    grouped = {}
    for volume_name in volume_names:
        seed = RESET_VOLUME_SEEDS.get(volume_name)
        if seed:
            service_id, target = seed
            grouped.setdefault(service_id, []).append((volume_name, target))

    for service_id, volume_targets in grouped.items():
        containers = by_service.get(service_id, [])
        if not containers:
            continue
        detail_response = client.get(f"/containers/{containers[0]['Id']}/json")
        detail_response.raise_for_status()
        image = detail_response.json().get("Image")
        if not image:
            raise RuntimeError(f"Não foi possível restaurar os arquivos padrão de {service_id}.")

        helper_name = f"laboratorio-seed-{uuid.uuid4().hex[:12]}"
        mounts = [
            {"Type": "volume", "Source": name, "Target": target, "ReadOnly": False}
            for name, target in volume_targets
        ]
        payload = {
            "Image": image,
            "Entrypoint": ["/bin/sh", "-c"],
            "Cmd": ["true"],
            "Labels": {"com.escom.dashboard.reset-helper": "true"},
            "HostConfig": {
                "AutoRemove": False,
                "NetworkMode": "none",
                "RestartPolicy": {"Name": "no"},
                "Mounts": mounts,
            },
        }
        create_response = client.post("/containers/create", params={"name": helper_name}, json=payload)
        create_response.raise_for_status()
        helper_id = create_response.json()["Id"]
        try:
            start_response = client.post(f"/containers/{helper_id}/start", timeout=20.0)
            if start_response.status_code not in {204, 304}:
                start_response.raise_for_status()
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                inspect_response = client.get(f"/containers/{helper_id}/json")
                inspect_response.raise_for_status()
                state = inspect_response.json().get("State", {})
                if state.get("Status") == "exited":
                    if state.get("ExitCode") != 0:
                        raise RuntimeError(f"Não foi possível restaurar os arquivos padrão de {service_id}.")
                    break
                time.sleep(0.5)
            else:
                raise RuntimeError(f"A restauração dos arquivos padrão de {service_id} excedeu o tempo esperado.")
        finally:
            client.delete(f"/containers/{helper_id}", params={"force": "true", "v": "false"})


def _run_container_command(client, container_id, command, environment=None, timeout_seconds=60):
    create_response = client.post(
        f"/containers/{container_id}/exec",
        json={
            "Cmd": command,
            "Env": environment or [],
            "AttachStdout": True,
            "AttachStderr": True,
        },
    )
    create_response.raise_for_status()
    exec_id = create_response.json()["Id"]
    start_response = client.post(
        f"/exec/{exec_id}/start",
        json={"Detach": False, "Tty": False},
        timeout=httpx.Timeout(timeout_seconds, connect=5.0),
    )
    start_response.raise_for_status()
    inspect_response = client.get(f"/exec/{exec_id}/json")
    inspect_response.raise_for_status()
    if inspect_response.json().get("ExitCode") != 0:
        raise RuntimeError("Um comando de restauração do serviço falhou.")


def _reset_application_database(client, postgres_id, database):
    detail_response = client.get(f"/containers/{postgres_id}/json")
    detail_response.raise_for_status()
    environment = {}
    for entry in detail_response.json().get("Config", {}).get("Env", []):
        key, separator, value = entry.partition("=")
        if separator:
            environment[key] = value
    username = environment.get("POSTGRES_USER")
    password = environment.get("POSTGRES_PASSWORD")
    if not username or not password:
        raise RuntimeError("Não foi possível identificar as credenciais internas do PostgreSQL.")

    process_environment = [f"PGPASSWORD={password}"]
    _run_container_command(
        client,
        postgres_id,
        ["dropdb", "--if-exists", "--force", "-h", "127.0.0.1", "-U", username, database],
        process_environment,
    )
    _run_container_command(
        client,
        postgres_id,
        ["createdb", "-h", "127.0.0.1", "-U", username, "--owner", username, database],
        process_environment,
    )


def _wait_for_ollama(timeout_seconds=120):
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get("http://ollama:11434/api/tags", timeout=2.0)
            if response.is_success:
                return
        except Exception:
            pass
        time.sleep(2)
    raise RuntimeError("O Ollama não respondeu para restaurar os modelos iniciais.")


def _pull_default_ollama_models(client, ollama_id, job_id):
    _set_reset_job(job_id, phase="Restaurando os modelos iniciais do Ollama", message="Isso pode levar alguns minutos, conforme a conexão e o disco.")
    _wait_for_ollama()
    for model in DEFAULT_OLLAMA_MODELS:
        _set_reset_job(job_id, phase=f"Baixando modelo inicial {model}", message="O download dos modelos base pode levar alguns minutos.")
        _run_container_command(client, ollama_id, ["ollama", "pull", model], timeout_seconds=1800)


def _run_reset_job(job_id, project, scope, service_id=None):
    mutated = False
    stopped_ids = []
    temporary_postgres_id = None
    temporary_ollama_id = None
    client = None
    try:
        _set_reset_job(job_id, status="running", phase="Preparando o ambiente", message="Verificando volumes e containers do laboratório.")
        client, detected_project = get_docker_scope()
        if detected_project != project:
            raise RuntimeError("O projeto Compose mudou durante a operação; nenhum outro projeto foi alterado.")

        project_containers = get_project_containers(client, project)
        by_service = {}
        for container in project_containers:
            service_name = (container.get("Labels") or {}).get("com.docker.compose.service")
            if service_name and service_name != "dashboard":
                by_service.setdefault(service_name, []).append(container)

        if scope == "all":
            volume_names = list(RESET_VOLUME_NAMES)
            stop_services = set(by_service)
            reset_metadata = {"restore_models": True, "stack_reset": True}
        else:
            reset_metadata = RESET_TARGETS[service_id]
            volume_names = list(reset_metadata.get("volumes", []))
            stop_services = set(by_service) if reset_metadata.get("stack_reset") else {service_id}
            stop_services.update(reset_metadata.get("stop_services", []))

        volume_names = _preflight_reset_volumes(client, project, volume_names, project_containers)
        all_metadata = client.get("/containers/json", params={"all": "true"})
        all_metadata.raise_for_status()
        stop_list = [container for container in project_containers
                     if (container.get("Labels") or {}).get("com.docker.compose.service") in stop_services]
        stop_order = {service_name: index for index, service_name in enumerate(reversed(RESET_START_ORDER))}
        stop_list.sort(key=lambda container: stop_order.get(
            (container.get("Labels") or {}).get("com.docker.compose.service"), len(stop_order)
        ))
        initially_running = {
            container["Id"] for container in stop_list
            if container.get("State") in {"running", "restarting"}
        }
        postgres_entries = by_service.get("postgres", [])
        if reset_metadata.get("database") and not postgres_entries:
            raise RuntimeError("O PostgreSQL deste laboratório não foi criado; o banco não foi alterado.")

        referenced = {mount.get("Name") for container in all_metadata.json() for mount in container.get("Mounts", [])}
        if any(name in referenced and name not in {mount.get("Name") for container in project_containers for mount in container.get("Mounts", [])} for name in volume_names):
            raise RuntimeError("Um volume selecionado está em uso fora dos containers deste laboratório.")

        _set_reset_job(job_id, phase="Parando serviços relacionados", message="Os serviços serão reiniciados após a limpeza.")
        for container in stop_list:
            if container["Id"] in initially_running:
                _stop_container(client, container["Id"])
                stopped_ids.append(container["Id"])
        if stop_list:
            mutated = True

        _set_reset_job(job_id, phase="Limpando dados persistentes", message=f"Volumes selecionados: {len(volume_names)}.")
        if volume_names:
            mutated = True
            _clear_project_volumes(client, project, volume_names)
            _set_reset_job(job_id, phase="Restaurando arquivos padrão", message="Repondo arquivos que acompanham a imagem dos serviços.")
            _restore_image_seeded_volumes(client, volume_names, by_service)

        if reset_metadata.get("database"):
            postgres = postgres_entries[0]
            postgres_id = postgres["Id"]
            postgres_state = client.get(f"/containers/{postgres_id}/json").json().get("State", {})
            if not postgres_state.get("Running"):
                _set_reset_job(job_id, phase="Preparando PostgreSQL", message="Iniciando temporariamente para restaurar o banco escolhido.")
                _start_container(client, postgres_id)
                if postgres_id not in initially_running:
                    temporary_postgres_id = postgres_id
            _wait_for_healthy_container(client, postgres_id, "PostgreSQL")
            _set_reset_job(job_id, phase="Restaurando banco de dados", message="O banco do serviço será recriado vazio.")
            mutated = True
            _reset_application_database(client, postgres_id, reset_metadata["database"])

        if reset_metadata.get("stack_reset") or scope == "all":
            postgres_entries = by_service.get("postgres", [])
            if postgres_entries:
                postgres_id = postgres_entries[0]["Id"]
                postgres_state = client.get(f"/containers/{postgres_id}/json").json().get("State", {})
                if not postgres_state.get("Running"):
                    _start_container(client, postgres_id)
                    if postgres_id not in initially_running:
                        temporary_postgres_id = postgres_id
                _set_reset_job(job_id, phase="Inicializando o PostgreSQL", message="A configuração inicial dos bancos está sendo recriada.")
                _wait_for_healthy_container(client, postgres_id, "PostgreSQL")

        if scope == "all" or reset_metadata.get("stack_reset"):
            _set_reset_job(job_id, phase="Reiniciando serviços", message="Restaurando o estado de execução anterior.")
            restart_ids = initially_running
        else:
            restart_ids = initially_running

        service_by_id = {
            container["Id"]: (container.get("Labels") or {}).get("com.docker.compose.service")
            for container in project_containers
        }
        ordered_ids = sorted(
            restart_ids,
            key=lambda container_id: RESET_START_ORDER.index(service_by_id.get(container_id))
            if service_by_id.get(container_id) in RESET_START_ORDER else len(RESET_START_ORDER),
        )
        for container_id in ordered_ids:
            if container_id == temporary_postgres_id:
                continue
            _start_container(client, container_id)
            if service_by_id.get(container_id) == "redis":
                _wait_for_healthy_container(client, container_id, "Redis", timeout_seconds=60)

        restore_models = reset_metadata.get("restore_models") and (scope == "all" or service_id == "ollama")
        if restore_models:
            ollama_entries = by_service.get("ollama", [])
            if ollama_entries:
                ollama_id = ollama_entries[0]["Id"]
                ollama_state = client.get(f"/containers/{ollama_id}/json").json().get("State", {})
                if not ollama_state.get("Running"):
                    _start_container(client, ollama_id)
                    temporary_ollama_id = ollama_id
                _pull_default_ollama_models(client, ollama_id, job_id)
            else:
                raise RuntimeError("Dados apagados, mas o container Ollama não existe para baixar os modelos iniciais.")

        if temporary_ollama_id:
            _stop_container(client, temporary_ollama_id)
        if temporary_postgres_id:
            _stop_container(client, temporary_postgres_id)

        _set_reset_job(job_id, status="complete", phase="Concluído", message="Os dados selecionados foram zerados e os serviços foram restaurados.")
    except Exception as exc:
        message = str(exc) if isinstance(exc, RuntimeError) else "Falha ao concluir o reset. Verifique os serviços e tente novamente."
        _set_reset_job(
            job_id,
            status="partial" if mutated else "error",
            phase="Operação interrompida" if mutated else "Não foi possível iniciar",
            message=message,
        )
    finally:
        if client:
            for container_id in {temporary_ollama_id, temporary_postgres_id} - {None}:
                try:
                    state_response = client.get(f"/containers/{container_id}/json")
                    if state_response.status_code == 200 and state_response.json().get("State", {}).get("Running"):
                        _stop_container(client, container_id)
                except Exception:
                    _set_reset_job(job_id, status="partial", phase="Verifique o estado dos serviços", message="O reset terminou, mas um serviço iniciado temporariamente ainda está em execução.")
            for container_id in stopped_ids:
                try:
                    state_response = client.get(f"/containers/{container_id}/json")
                    if state_response.status_code == 200 and not state_response.json().get("State", {}).get("Running"):
                        _start_container(client, container_id)
                except Exception:
                    _set_reset_job(job_id, status="partial", phase="Verifique o estado dos serviços", message="A limpeza terminou, mas algum serviço não reiniciou automaticamente.")
            client.close()
        with RESET_JOBS_LOCK:
            if ACTIVE_RESET_JOB == job_id:
                ACTIVE_RESET_JOB = None

@app.get("/", response_class=HTMLResponse)
async def welcome_home(request: Request):
    return templates.TemplateResponse(request=request, name="welcome.html", context={})

@app.get("/instrucoes/n8n", response_class=HTMLResponse)
async def instrucao_n8n(request: Request):
    return templates.TemplateResponse(request=request, name="instrucao_n8n.html", context={})

@app.get("/instrucoes/ollama", response_class=HTMLResponse)
async def instrucao_ollama(request: Request):
    return templates.TemplateResponse(request=request, name="instrucao_ollama.html", context={})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    # Agrupa os serviços por categoria preservando a ordem
    categories = {}
    for service in SERVICES_DATA:
        cat = service["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(service)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "categories": categories,
            "services": SERVICES_DATA
        }
    )


@app.get("/configuracoes", response_class=HTMLResponse)
async def dashboard_settings(request: Request):
    reset_services = []
    for service in SERVICES_DATA:
        metadata = RESET_TARGETS.get(service["id"])
        if not metadata:
            continue
        if metadata.get("warning"):
            effect = {
                "redis": "Apaga a persistência do Redis e reinicia o cache.",
                "litellm": "Apaga a configuração do LiteLLM e o cache compartilhado no Redis.",
                "postgres": "Apaga o armazenamento do PostgreSQL e recria os bancos iniciais.",
                "jupyter": "Remove notebooks e arquivos da área de trabalho persistente.",
                "python-mcp": "Apaga a memória dos agentes no Redis e reinicia o servidor MCP.",
            }.get(service["id"], "Apaga os dados persistentes deste serviço.")
        elif metadata.get("database"):
            effect = "Apaga e recria o banco de dados e os arquivos persistentes deste serviço." if metadata.get("volumes") else "Apaga e recria o banco de dados usado por este serviço."
        elif metadata.get("volumes"):
            effect = "Apaga os arquivos, modelos ou dados persistentes deste serviço."
        else:
            effect = "Reinicia o container para descartar seu estado temporário em memória."
        if metadata.get("restore_models"):
            effect = "Apaga os modelos instalados e baixa novamente os dois modelos iniciais."
        reset_services.append({
            "id": service["id"],
            "category": service["category"],
            "name": service["name"],
            "icon": service["icon"],
            "description": effect,
            "warning": metadata.get("warning", ""),
        })
    return templates.TemplateResponse(
        request=request,
        name="configuracoes.html",
        context={"reset_services": reset_services},
    )


@app.get("/documentacao", response_class=HTMLResponse)
async def dashboard_documentation(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="documentacao.html",
        context={"services": SERVICES_DATA},
    )

@app.get("/health")
def health():
    return {"status": "ok", "service": "dashboard", "port": 9090}

@app.get("/api/status")
async def check_status():
    async def probe(service, client):
        if service.get("check_type") == "tcp":
            writer = None
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(service["check_host"], service["check_port"]),
                    timeout=2.0,
                )
                return service["id"], "online"
            except Exception:
                return service["id"], "offline"
            finally:
                if writer is not None:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass

        try:
            response = await client.get(service["check_url"])
            is_online = 200 <= response.status_code < 400 or response.status_code == 401
            return service["id"], "online" if is_online else "offline"
        except Exception:
            return service["id"], "offline"

    async with httpx.AsyncClient(timeout=2.0, follow_redirects=True) as client:
        results = await asyncio.gather(*(probe(service, client) for service in SERVICES_DATA))
    return dict(results)


@app.get("/api/control/services")
def control_service_status():
    client, project = get_docker_scope()
    try:
        containers = get_project_containers(client, project)
        by_service = {}
        for container in containers:
            service_id = (container.get("Labels") or {}).get("com.docker.compose.service")
            if service_id:
                by_service.setdefault(service_id, container)
        result = {"project": project, "services": {}}
        for service_id in [service["id"] for service in SERVICES_DATA]:
            container = by_service.get(service_id)
            if not container:
                result["services"][service_id] = {"state": "not_created", "health": None}
                continue
            state = container.get("State", "")
            result["services"][service_id] = {
                "state": "running" if state == "running" else ("starting" if state in {"created", "restarting"} else ("error" if state == "dead" else "stopped")),
                "health": None,
            }
        return result
    finally:
        client.close()


@app.post("/api/control/services/{service_id}")
def control_service(service_id: str, body: ServiceAction, request: Request):
    validate_local_control_request(request)
    if service_id not in CONTROLLED_SERVICE_IDS:
        raise HTTPException(status_code=404, detail="Serviço não permitido ou inexistente.")

    client, project = get_docker_scope()
    try:
        containers = get_project_containers(client, project, service_id)
        if not containers:
            raise HTTPException(status_code=404, detail="Container ainda não foi criado. Suba o perfil correspondente pelo Compose.")
        container = containers[0]
        params = {"t": 10} if body.action == "stop" else None
        response = client.post(f"/containers/{container['Id']}/{body.action}", params=params)
        if response.status_code not in {204, 304}:
            response.raise_for_status()
        return {"service": service_id, "action": body.action, "state": "running" if body.action == "start" else "stopped"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Não foi possível {body.action} o serviço.") from exc
    finally:
        client.close()


def _queue_reset(scope, service_id, body, request):
    global ACTIVE_RESET_JOB
    validate_local_control_request(request)
    expected_confirmation = "ZERAR LABORATÓRIO" if scope == "all" else f"ZERAR {service_id.upper()}"
    if body.confirmation != expected_confirmation:
        raise HTTPException(status_code=400, detail=f"Digite exatamente: {expected_confirmation}.")

    client, project = get_docker_scope()
    client.close()
    with RESET_JOBS_LOCK:
        if ACTIVE_RESET_JOB:
            raise HTTPException(status_code=409, detail="Já existe uma operação de reset em andamento.")
        if update_is_active():
            raise HTTPException(status_code=409, detail="Aguarde a atualização do laboratório terminar antes de zerar os dados.")
        job_id = uuid.uuid4().hex
        service = next((entry["name"] for entry in SERVICES_DATA if entry["id"] == service_id), "")
        RESET_JOBS[job_id] = {
            "id": job_id,
            "scope": scope,
            "service": service or "Laboratório completo",
            "status": "queued",
            "phase": "Na fila",
            "message": "O reset será iniciado em instantes.",
            "updatedAt": time.time(),
        }
        ACTIVE_RESET_JOB = job_id

    try:
        worker = threading.Thread(
            target=_run_reset_job,
            args=(job_id, project, scope, service_id),
            name=f"laboratorio-reset-{job_id[:8]}",
            daemon=True,
        )
        worker.start()
    except Exception as exc:
        _set_reset_job(job_id, status="error", phase="Não foi possível iniciar", message="O reset não foi iniciado.")
        with RESET_JOBS_LOCK:
            if ACTIVE_RESET_JOB == job_id:
                ACTIVE_RESET_JOB = None
        raise HTTPException(status_code=500, detail="Não foi possível iniciar o reset.") from exc
    return {"jobId": job_id, "status": "queued"}


@app.post("/api/control/reset/all", status_code=202)
def reset_all(body: ResetRequest, request: Request):
    return _queue_reset("all", None, body, request)


@app.post("/api/control/reset/service/{service_id}", status_code=202)
def reset_service(service_id: str, body: ResetRequest, request: Request):
    if service_id not in RESET_TARGETS:
        raise HTTPException(status_code=404, detail="Serviço não permitido ou inexistente.")
    return _queue_reset("service", service_id, body, request)


@app.get("/api/control/reset/current")
def current_reset_job(request: Request):
    if request.headers.get("host", "").lower() not in LOCAL_HOSTS:
        raise HTTPException(status_code=403, detail="Operações de reset estão disponíveis somente no dashboard local.")
    with RESET_JOBS_LOCK:
        job = RESET_JOBS.get(ACTIVE_RESET_JOB) if ACTIVE_RESET_JOB else None
        return {"job": _reset_job_snapshot(job) if job else None}


@app.get("/api/control/reset/jobs/{job_id}")
def reset_job_status(job_id: str, request: Request):
    if request.headers.get("host", "").lower() not in LOCAL_HOSTS:
        raise HTTPException(status_code=403, detail="Operações de reset estão disponíveis somente no dashboard local.")
    with RESET_JOBS_LOCK:
        job = RESET_JOBS.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Operação de reset não encontrada.")
        return _reset_job_snapshot(job)


@app.get("/api/control/updates/status")
def system_update_status(request: Request, refresh: bool = False):
    if request.headers.get("host", "").lower() not in LOCAL_HOSTS:
        raise HTTPException(status_code=403, detail="A consulta de atualizações está disponível somente no dashboard local.")
    return call_update_service("GET", f"/api/status{'?refresh=1' if refresh else ''}", timeout=330 if refresh else 20)


@app.post("/api/control/updates/apply", status_code=202)
def apply_system_update(body: UpdateRequest, request: Request):
    validate_local_control_request(request)
    if body.confirmation != UPDATE_CONFIRMATION:
        raise HTTPException(status_code=400, detail=f"Digite exatamente: {UPDATE_CONFIRMATION}.")
    with RESET_JOBS_LOCK:
        if ACTIVE_RESET_JOB:
            raise HTTPException(status_code=409, detail="Aguarde o reset em andamento antes de atualizar o laboratório.")
        if update_is_active():
            raise HTTPException(status_code=409, detail="Já existe uma atualização em andamento.")
        return call_update_service(
            "POST",
            "/api/apply",
            body={"confirmation": body.confirmation},
            timeout=30,
        )


@app.get("/api/control/updates/jobs/{job_id}")
def system_update_job(job_id: str, request: Request):
    if request.headers.get("host", "").lower() not in LOCAL_HOSTS:
        raise HTTPException(status_code=403, detail="O acompanhamento está disponível somente no dashboard local.")
    if not re.fullmatch(r"[a-f0-9]{32}", job_id):
        raise HTTPException(status_code=404, detail="Operação de atualização não encontrada.")
    return call_update_service("GET", f"/api/jobs/{job_id}", timeout=10)

@app.get("/diagrama", response_class=HTMLResponse)
async def diagrama_view(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="diagrama.html",
        context={
            "services": SERVICES_DATA
        }
    )
