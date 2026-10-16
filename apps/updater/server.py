import hmac
import json
import os
import re
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


WORKSPACE = Path("/workspace")
GIT_SAFE_DIRECTORY = f"safe.directory={WORKSPACE}"
STATE_FILE = Path("/state/update-state.json")
TOKEN = os.environ.get("UPDATER_TOKEN", "")
CONFIRMATION = "ATUALIZAR LABORATÓRIO"
PORT = int(os.environ.get("UPDATER_PORT", "8091"))
STATE_LOCK = threading.Lock()


def read_state():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def is_github_origin():
    remote = subprocess.run(
        ["git", "-c", GIT_SAFE_DIRECTORY, "config", "--get", "remote.origin.url"],
        cwd=WORKSPACE,
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    remote_url = (remote.stdout or "").strip()
    if remote_url.startswith("git@github.com:"):
        return True
    return bool(remote_url and urlsplit(remote_url).hostname == "github.com")


def write_state(**updates):
    with STATE_LOCK:
        state = read_state()
        state.update(updates)
        state["updatedAt"] = time.time()
        temporary = STATE_FILE.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        temporary.replace(STATE_FILE)
        return state


def git_env():
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    if is_github_origin():
        environment["GIT_ASKPASS"] = "/opt/updater/git-askpass"
    return environment


def run_git(*arguments, timeout=90):
    return subprocess.run(
        ["git", "-c", GIT_SAFE_DIRECTORY, *arguments],
        cwd=WORKSPACE,
        env=git_env(),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def clean_output(result):
    return (result.stdout or "").strip()


def update_status(refresh=False):
    repository = run_git("rev-parse", "--is-inside-work-tree", timeout=10)
    if repository.returncode != 0:
        return {
            "configured": False,
            "canUpdate": False,
            "message": "Este projeto ainda não está configurado como repositório Git.",
        }

    if not is_github_origin():
        return {
            "configured": True,
            "remoteConfigured": False,
            "canUpdate": False,
            "message": "Configure o remoto origin para apontar a um repositório do GitHub.",
        }

    head = clean_output(run_git("rev-parse", "--short=12", "HEAD", timeout=10))
    full_head = clean_output(run_git("rev-parse", "HEAD", timeout=10))
    branch = clean_output(run_git("branch", "--show-current", timeout=10))
    upstream_result = run_git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", timeout=10)
    dirty_result = run_git("status", "--porcelain", "--untracked-files=normal", timeout=20)
    dirty = dirty_result.returncode != 0 or bool(clean_output(dirty_result))
    state = read_state()

    if not state.get("appliedCommit") and full_head:
        state = write_state(appliedCommit=full_head)

    if upstream_result.returncode != 0:
        return {
            "configured": True,
            "remoteConfigured": False,
            "branch": branch or None,
            "currentCommit": head or None,
            "dirty": dirty,
            "canUpdate": False,
            "message": "A branch atual ainda não acompanha uma branch remota.",
        }

    upstream = clean_output(upstream_result)
    fetch_message = None
    if refresh:
        fetched = run_git("fetch", "--prune", "origin", timeout=300)
        if fetched.returncode != 0:
            fetch_message = "Não foi possível consultar o GitHub. Verifique a conexão e, se o repositório for privado, a autenticação local."

    remote_result = run_git("rev-parse", "--short=12", upstream, timeout=10)
    count_result = run_git("rev-list", "--left-right", "--count", f"HEAD...{upstream}", timeout=30)
    if remote_result.returncode != 0 or count_result.returncode != 0:
        return {
            "configured": True,
            "remoteConfigured": True,
            "branch": branch or None,
            "upstream": upstream,
            "currentCommit": head or None,
            "dirty": dirty,
            "canUpdate": False,
            "message": fetch_message or "Não foi possível comparar esta branch com o remoto.",
        }

    counts = clean_output(count_result).split()
    ahead, behind = (int(counts[0]), int(counts[1])) if len(counts) == 2 else (0, 0)
    applied = state.get("appliedCommit", "")
    pending_apply = bool(applied and full_head and full_head != applied and not dirty and ahead == 0)
    can_update = not dirty and ((behind > 0 and ahead == 0) or pending_apply)
    if dirty:
        message = "Há alterações locais. Salve e publique essas alterações antes de aplicar uma atualização."
    elif fetch_message:
        message = fetch_message
        can_update = pending_apply
    elif pending_apply and behind == 0:
        message = "Há uma versão baixada que ainda não foi aplicada aos containers."
    elif behind > 0 and ahead == 0:
        message = f"{behind} atualização(ões) disponível(is) no remoto."
    elif ahead > 0 and behind > 0:
        message = "A branch local e a remota divergiram; sincronize o Git manualmente antes de atualizar."
        can_update = False
    elif ahead > 0:
        message = "Há commits locais ainda não publicados no remoto."
        can_update = pending_apply
    else:
        message = "O laboratório já está na versão mais recente."

    return {
        "configured": True,
        "remoteConfigured": True,
        "branch": branch or None,
        "upstream": upstream,
        "currentCommit": head or None,
        "remoteCommit": clean_output(remote_result) or None,
        "ahead": ahead,
        "behind": behind,
        "dirty": dirty,
        "pendingApply": pending_apply,
        "canUpdate": can_update,
        "upToDate": not dirty and ahead == 0 and behind == 0 and not pending_apply,
        "message": message,
        "checkedAt": time.time() if refresh else state.get("checkedAt"),
    }


def inspect_updater():
    container_id = os.environ.get("HOSTNAME", "")
    if not container_id:
        raise RuntimeError("Não foi possível identificar o container do atualizador.")
    labels_json = subprocess.check_output(
        ["docker", "inspect", "--format", "{{json .Config.Labels}}", container_id],
        text=True,
        timeout=15,
    )
    image = subprocess.check_output(
        ["docker", "inspect", "--format", "{{.Image}}", container_id],
        text=True,
        timeout=15,
    ).strip()
    labels = json.loads(labels_json)
    project_dir = labels.get("com.docker.compose.project.working_dir")
    project = labels.get("com.docker.compose.project")
    if not project_dir or not project or not image:
        raise RuntimeError("Não foi possível identificar a pasta ou o projeto Compose do laboratório.")
    listed_files = labels.get("com.docker.compose.project.config_files", "")
    use_gpu = any(Path(item.strip()).name == "docker-compose.gpu.yml" for item in listed_files.split(","))
    return project_dir, project, image, use_gpu


def start_worker(job_id):
    project_dir, project, image, use_gpu = inspect_updater()
    command = [
        "docker", "run", "--detach", "--rm",
        "--name", f"laboratorio-atualizacao-{job_id[:12]}",
        "--label", f"laboratorio.update.job={job_id}",
        "--volumes-from", os.environ.get("HOSTNAME", ""),
        "--mount", f"type=bind,source={project_dir},target={project_dir}",
        "--mount", "type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock",
        "--workdir", project_dir,
        "--env", f"UPDATE_JOB_ID={job_id}",
        "--env", f"UPDATE_PROJECT={project}",
        "--env", f"UPDATE_PROJECT_DIR={project_dir}",
        "--env", f"UPDATE_USE_GPU={'1' if use_gpu else '0'}",
    ]
    if os.environ.get("GITHUB_TOKEN"):
        command.extend(["--env", "GITHUB_TOKEN"])
    command.extend([image, "python3", "/opt/updater/worker.py"])
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)


def reconcile_job(state):
    job = state.get("job") or {}
    if job.get("status") not in {"queued", "running"} or not job.get("id"):
        return state
    if time.time() - float(job.get("updatedAt", time.time())) < 20:
        return state
    worker = subprocess.run(
        ["docker", "ps", "-aq", "--filter", f"label=laboratorio.update.job={job['id']}"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if worker.returncode != 0 or (worker.stdout or "").strip():
        return state
    latest = read_state()
    latest_job = latest.get("job") or {}
    if latest_job.get("id") == job.get("id") and latest_job.get("status") in {"queued", "running"}:
        latest_job.update(
            status="error",
            phase="Atualização interrompida",
            message="O processo de atualização foi encerrado antes de informar o resultado. Verifique os containers e consulte novamente.",
            updatedAt=time.time(),
        )
        return write_state(job=latest_job)
    return latest


class Handler(BaseHTTPRequestHandler):
    server_version = "LaboratorioUpdater/1.0"

    def log_message(self, _format, *_args):
        return

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        if not TOKEN:
            self.send_json(503, {"detail": "O atualizador ainda não foi configurado. Execute novamente o instalador do laboratório."})
            return False
        supplied = self.headers.get("Authorization", "")
        expected = f"Bearer {TOKEN}"
        if not hmac.compare_digest(supplied, expected):
            self.send_json(403, {"detail": "Requisição interna não autorizada."})
            return False
        return True

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/health":
            self.send_json(200, {"status": "ok"})
            return
        if not self.authorized():
            return
        if parsed.path == "/api/status":
            refresh = parse_qs(parsed.query).get("refresh", ["0"])[0] == "1"
            try:
                status = update_status(refresh=refresh)
                state = reconcile_job(read_state())
                job = state.get("job")
                status["job"] = job
                self.send_json(200, status)
            except subprocess.TimeoutExpired:
                self.send_json(504, {"detail": "A consulta ao Git demorou demais. Tente novamente."})
            except Exception:
                self.send_json(502, {"detail": "Não foi possível consultar o estado do repositório."})
            return
        match = re.fullmatch(r"/api/jobs/([a-f0-9]{32})", parsed.path)
        if match:
            job = read_state().get("job")
            if not job or job.get("id") != match.group(1):
                self.send_json(404, {"detail": "Operação de atualização não encontrada."})
            else:
                self.send_json(200, job)
            return
        self.send_json(404, {"detail": "Rota não encontrada."})

    def do_POST(self):
        parsed = urlsplit(self.path)
        if parsed.path != "/api/apply":
            self.send_json(404, {"detail": "Rota não encontrada."})
            return
        if not self.authorized():
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 8192:
                self.send_json(413, {"detail": "Requisição muito grande."})
                return
            body = json.loads(self.rfile.read(size) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self.send_json(400, {"detail": "Requisição inválida."})
            return
        if body.get("confirmation") != CONFIRMATION:
            self.send_json(400, {"detail": f"Digite exatamente: {CONFIRMATION}."})
            return

        state = read_state()
        active = state.get("job") or {}
        if active.get("status") in {"queued", "running"}:
            self.send_json(409, {"detail": "Já existe uma atualização em andamento."})
            return
        try:
            status = update_status(refresh=True)
        except subprocess.TimeoutExpired:
            self.send_json(504, {"detail": "A consulta ao Git demorou demais. Tente novamente."})
            return
        if not status.get("canUpdate"):
            self.send_json(409, {"detail": status.get("message", "Não há uma atualização pronta para aplicar."), "status": status})
            return

        job_id = uuid.uuid4().hex
        job = {
            "id": job_id,
            "status": "queued",
            "phase": "Preparando atualização",
            "message": "O sistema será atualizado em segundo plano.",
            "updatedAt": time.time(),
        }
        write_state(job=job)
        try:
            start_worker(job_id)
        except Exception:
            job.update(status="error", phase="Não foi possível iniciar", message="Verifique se o Docker e o atualizador estão ativos; nenhuma atualização foi aplicada.", updatedAt=time.time())
            write_state(job=job)
            self.send_json(502, {"detail": job["message"]})
            return
        self.send_json(202, {"jobId": job_id, "status": job["status"]})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
