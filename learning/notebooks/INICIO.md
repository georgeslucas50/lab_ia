# Comece pelo JupyterLab

Este diretório é persistente entre reinicializações do laboratório. Os serviços
podem ser acessados pelos nomes DNS internos do Compose; dentro de um notebook,
`localhost` aponta para o próprio container Jupyter.

## Teste o Ollama

```python
import os
import requests

response = requests.get(f"{os.environ['OLLAMA_HOST']}/api/tags", timeout=10)
response.raise_for_status()
[model["name"] for model in response.json()["models"]]
```

## Faça uma chamada pelo LiteLLM

O pacote `openai` já está instalado e as variáveis `OPENAI_BASE_URL` e
`OPENAI_API_KEY` são preparadas pelo Compose. Use um nome de modelo disponível
em `config/litellm/config.yaml`.

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.environ["OPENAI_BASE_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
)
response = client.chat.completions.create(
    model="llama3.2:3b",
    messages=[{"role": "user", "content": "Resuma o que é um embedding."}],
)
print(response.choices[0].message.content)
```

## Endereços internos disponíveis

| Serviço | Variável | Endereço |
| --- | --- | --- |
| Ollama | `OLLAMA_HOST` | `http://ollama:11434` |
| LiteLLM | `OPENAI_BASE_URL` | `http://litellm:4000/v1` |
| Python MCP | `MCP_URL` | `http://python-mcp:8000/mcp` |
| Qdrant | `QDRANT_URL` | `http://qdrant:6333` |
| Neo4j | `NEO4J_URI` | `bolt://neo4j:7687` |
| Redis | `REDIS_URL` | `redis://redis:6379/0` |
| PostgreSQL | `POSTGRES_HOST` | `postgres:5432` |
| Apache Tika | `TIKA_URL` | `http://tika:9998` |

Alguns serviços só ficam disponíveis quando o perfil `full` está ativo. Use o
dashboard para iniciá-los ou pará-los durante a aula.
