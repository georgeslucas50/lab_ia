import asyncio
import os
import httpx
import redis
from bs4 import BeautifulSoup
from fastapi import FastAPI
from pydantic import BaseModel
from fastmcp import FastMCP

# 1. Inicialização do Servidor FastMCP e FastAPI
mcp = FastMCP("GenAI-MCP-Server")
mcp_app = mcp.http_app(path="/")
app = FastAPI(
    title="Python MCP & Agents Tools API",
    description="Servidor híbrido FastAPI + FastMCP para servir ferramentas a agentes (n8n, Flowise, Open WebUI)",
    version="3.0.0",
    lifespan=mcp_app.lifespan,
)

# Conexão Redis para Cache de Memória
def get_redis_client():
    return redis.Redis(
        host="redis",
        port=6379,
        db=0,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )

# 2. Ferramentas MCP (@mcp.tool)

@mcp.tool()
async def extract_document_via_tika(file_url_or_content: str) -> str:
    """Extrai texto e realiza OCR em documentos ou imagens enviadas para o Apache Tika."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if file_url_or_content.startswith("http://") or file_url_or_content.startswith("https://"):
                file_resp = await client.get(file_url_or_content)
                file_bytes = file_resp.content
            else:
                file_bytes = file_url_or_content.encode("utf-8")

            resp = await client.put("http://tika:9998/tika", content=file_bytes, headers={"Accept": "text/plain"})
            if resp.status_code == 200:
                return resp.text.strip()
            return f"Erro no Tika OCR (HTTP {resp.status_code}): {resp.text}"
    except Exception as e:
        return f"Erro ao processar documento no Tika: {str(e)}"

@mcp.tool()
async def scrape_webpage_headless(url: str) -> str:
    """Realiza web scraping de páginas com JavaScript usando o Browserless Chromium e retorna o texto limpo."""
    try:
        token = os.getenv("BROWSERLESS_TOKEN")
        if not token:
            return "Erro: BROWSERLESS_TOKEN não foi configurado."
        browserless_url = f"http://browserless:3000/content?token={token}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(browserless_url, json={"url": url})
            if resp.status_code != 200:
                return f"Erro no Browserless (HTTP {resp.status_code}): {resp.text}"
            
            # Limpeza do HTML com BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.extract()
            text = soup.get_text(separator="\n")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return "\n".join(lines[:100])
    except Exception as e:
        return f"Erro ao raspar página web: {str(e)}"

@mcp.tool()
def agent_memory_cache(action: str, key: str, value: str = "", ttl: int = 3600) -> str:
    """Gerencia a memória de curto prazo de agentes no Redis (ações: get, set, delete)."""
    try:
        r = get_redis_client()
        action = action.lower()
        if action == "get":
            val = r.get(key)
            return val if val else f"Chave '{key}' não encontrada ou expirada."
        elif action == "set":
            r.set(key, value, ex=ttl)
            return f"Sucesso: Chave '{key}' salva por {ttl}s."
        elif action == "delete":
            r.delete(key)
            return f"Sucesso: Chave '{key}' removida."
        return "Ação inválida. Use 'get', 'set' ou 'delete'."
    except Exception as e:
        return f"Erro na operação de memória Redis: {str(e)}"

async def _probe_http(client: httpx.AsyncClient, name: str, url: str) -> str:
    try:
        response = await client.get(url)
        if 200 <= response.status_code < 400 or response.status_code == 401:
            return f"• {name}: ONLINE"
        return f"• {name}: ERRO HTTP {response.status_code}"
    except Exception as exc:
        return f"• {name}: OFFLINE ({type(exc).__name__})"


async def _probe_tcp(name: str, host: str, port: int) -> str:
    writer = None
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=3.0)
        return f"• {name}: ONLINE"
    except Exception as exc:
        return f"• {name}: OFFLINE ({type(exc).__name__})"
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass


@mcp.tool()
async def check_ai_infrastructure_health() -> str:
    """Verifica os 17 serviços do laboratório sem bloquear a consulta em sequência."""
    token = os.getenv("BROWSERLESS_TOKEN", "")
    http_services = {
        "Open WebUI": "http://open-webui:8080/health",
        "n8n": "http://n8n:5678/healthz",
        "Flowise": "http://flowise:3000/",
        "LiteLLM": "http://litellm:4000/health/liveliness",
        "Arize Phoenix": "http://phoenix:6006/",
        "Ollama": "http://ollama:11434/",
        "Faster-Whisper": "http://whisper-stt:8000/health",
        "OpenEDAI TTS": "http://openedai-tts:8000/health",
        "Python MCP": "http://python-mcp:8000/health",
        "Apache Tika": "http://tika:9998/version",
        "Browserless": f"http://browserless:3000/pressure?token={token}",
        "Qdrant": "http://qdrant:6333/readyz",
        "Neo4j": "http://neo4j:7474/",
        "Portainer": "http://portainer:9000/api/status",
        "Dashboard": "http://dashboard:9090/health",
    }

    async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as client:
        checks = [
            _probe_http(client, name, url)
            for name, url in http_services.items()
        ]
        checks.extend(
            [
                _probe_tcp("Redis", "redis", 6379),
                _probe_tcp("PostgreSQL", "postgres", 5432),
            ]
        )
        results = await asyncio.gather(*checks)

    online = sum("ONLINE" in result for result in results)
    return f"📊 Saúde do laboratório: {online}/{len(results)} serviços online.\n" + "\n".join(results)

# 3. Modelos Pydantic para a API REST
class TaskRequest(BaseModel):
    task_type: str
    url: str | None = None
    expression: str | None = None
    key: str | None = None
    value: str | None = None
    cache_action: str = "get"
    ttl: int = 3600

# 4. Endpoints REST da FastAPI

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "python-mcp",
        "version": "3.0.0",
        "mcp_server": "GenAI-MCP-Server"
    }

@app.post("/run-task")
async def run_task(payload: TaskRequest):
    if payload.task_type == "status":
        report = await check_ai_infrastructure_health()
        return {"status": "success", "result": report}
    elif payload.task_type == "scrape" and payload.url:
        result = await scrape_webpage_headless(payload.url)
        return {"status": "success", "result": result}
    elif payload.task_type == "cache" and payload.key:
        result = agent_memory_cache(payload.cache_action, payload.key, payload.value or "", payload.ttl)
        return {"status": "success", "result": result}
    
    return {"status": "error", "message": "Tarefa inválida ou parâmetros ausentes."}

# MCP via Streamable HTTP. O lifespan do FastMCP foi integrado ao FastAPI acima.
app.mount("/mcp", mcp_app, name="mcp")
