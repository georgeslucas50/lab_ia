import json
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import urlsplit


PROJECT_DIR = Path(os.environ["UPDATE_PROJECT_DIR"])
PROJECT = os.environ["UPDATE_PROJECT"]
JOB_ID = os.environ["UPDATE_JOB_ID"]
STATE_FILE = Path("/state/update-state.json")
GPU_ENABLED = os.environ.get("UPDATE_USE_GPU") == "1"


def load_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def update_job(**updates):
    state = load_state()
    job = state.get("job", {})
    if job.get("id") != JOB_ID:
        job = {"id": JOB_ID}
    job.update(updates)
    job["updatedAt"] = time.time()
    state["job"] = job
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    temporary.replace(STATE_FILE)


def git(*args, check=True):
    remote = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"], cwd=PROJECT_DIR,
        text=True, capture_output=True, check=False,
    )
    remote_url = (remote.stdout or "").strip()
    is_github = remote_url.startswith("git@github.com:")
    if remote_url:
        is_github = is_github or urlsplit(remote_url).hostname == "github.com"
    environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    if is_github:
        environment["GIT_ASKPASS"] = "/opt/updater/git-askpass"
    result = subprocess.run(
        ["git", *args], cwd=PROJECT_DIR, text=True, capture_output=True,
        env=environment,
        timeout=600, check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError("Não foi possível sincronizar o repositório Git. Verifique conexão, autenticação e estado da branch.")
    return (result.stdout or "").strip()


def compose_prefix():
    files = [PROJECT_DIR / "docker-compose.yml"]
    if GPU_ENABLED:
        gpu_file = PROJECT_DIR / "docker-compose.gpu.yml"
        if gpu_file.is_file():
            files.append(gpu_file)
    prefix = ["docker", "compose", "--project-directory", str(PROJECT_DIR), "-p", PROJECT]
    for compose_file in files:
        prefix.extend(["-f", str(compose_file)])
    prefix.extend(["--profile", "full", "--profile", "management"])
    return prefix


def run_compose(prefix, *args, phase, message, timeout=3600):
    update_job(status="running", phase=phase, message=message)
    result = subprocess.run(
        [*prefix, *args], cwd=PROJECT_DIR, text=True, capture_output=True,
        env=os.environ.copy(), timeout=timeout, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(message)


def wait_dashboard(prefix):
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["docker", "ps", "-q", "--filter", f"label=com.docker.compose.project={PROJECT}", "--filter", "label=com.docker.compose.service=dashboard"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        container_id = (result.stdout or "").strip().splitlines()
        if container_id:
            health = subprocess.run(
                ["docker", "inspect", "--format", "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}", container_id[0]],
                capture_output=True, text=True, timeout=15, check=False,
            )
            if (health.stdout or "").strip() == "healthy":
                return
        time.sleep(5)
    raise RuntimeError("Os containers foram recriados, mas o dashboard não ficou saudável dentro do prazo.")


def main():
    update_job(status="running", phase="Verificando alterações locais", message="Confirmando que não há arquivos locais pendentes.")
    if git("status", "--porcelain", "--untracked-files=normal"):
        raise RuntimeError("A atualização foi cancelada porque há alterações locais no repositório. Salve-as antes de tentar novamente.")

    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", check=False)
    old_commit = git("rev-parse", "HEAD")
    if not upstream:
        raise RuntimeError("A branch atual não acompanha um remoto Git; configure o repositório antes de atualizar.")

    update_job(status="running", phase="Sincronizando Git", message="Buscando a versão mais recente do branch configurado.")
    git("fetch", "--prune", "origin")
    counts = git("rev-list", "--left-right", "--count", f"HEAD...{upstream}").split()
    if len(counts) != 2:
        raise RuntimeError("Não foi possível comparar os commits locais e remotos.")
    ahead, behind = int(counts[0]), int(counts[1])
    if ahead != 0:
        raise RuntimeError("A branch local tem commits próprios ou divergiu do remoto. Sincronize o Git manualmente antes de atualizar.")
    if behind:
        git("merge", "--ff-only", upstream)

    prefix = compose_prefix()
    run_compose(prefix, "config", "--quiet", phase="Validando configuração", message="Validando os arquivos do Compose antes de alterar os containers.", timeout=120)
    run_compose(prefix, "pull", "--ignore-buildable", phase="Baixando imagens", message="Baixando as imagens atualizadas dos serviços. Isso pode levar alguns minutos.")
    run_compose(prefix, "up", "-d", "--build", "--remove-orphans", phase="Aplicando atualização", message="Reconstruindo e recriando os serviços. Os volumes persistentes serão preservados.")
    update_job(status="running", phase="Aguardando dashboard", message="A atualização foi aplicada; verificando a saúde do painel.")
    wait_dashboard(prefix)

    current_commit = git("rev-parse", "HEAD")
    state = load_state()
    state["appliedCommit"] = current_commit
    state["appliedAt"] = time.time()
    job = state.get("job", {})
    job.update(status="complete", phase="Atualização concluída", message="O laboratório foi atualizado e o dashboard voltou a responder.", updatedAt=time.time())
    state["job"] = job
    temporary = STATE_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    temporary.replace(STATE_FILE)


if __name__ == "__main__":
    try:
        main()
    except subprocess.TimeoutExpired:
        update_job(status="error", phase="Tempo esgotado", message="A atualização demorou além do esperado. Verifique o estado dos containers e tente novamente.")
    except Exception as error:
        message = str(error)
        update_job(status="error", phase="Atualização interrompida", message=message or "Não foi possível aplicar a atualização.")
