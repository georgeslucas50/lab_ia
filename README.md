# Laboratório de IA

Desenvolvido por **Georges Lucas Silva Queiroz de Albuquerque** · [GitHub](https://github.com/georgeslucas50) · [LinkedIn](https://www.linkedin.com/in/georges-lucas-0928123b3/)

Ambiente local de estudo para modelos, aplicações de chat, automações e serviços de apoio a RAG. O laboratório pode rodar no Ubuntu pelo WSL 2 no Windows ou diretamente em uma instalação nativa do Ubuntu. As duas opções usam os mesmos arquivos Docker Compose; cada host mantém suas próprias imagens, modelos e volumes. A GPU NVIDIA é opcional; com driver compatível, o Ollama usa a GPU, e sem ela funciona em CPU.

Para manutenção do repositório, agentes de programação devem começar por [AGENTS.md](AGENTS.md). Consulte também a [arquitetura atual](docs/ARCHITECTURE.md) e a [análise técnica e roteiro de evolução](docs/ANALISE_E_PLANO.md). O roteiro de instalação é fornecido separadamente e não faz parte deste repositório.

## Serviços e portas

O Compose define 19 serviços: 17 serviços de aprendizagem, o `system-updater` de apoio e o Portainer. Oito serviços de aprendizagem iniciam sem perfil; o perfil `full` acrescenta os outros nove. O perfil `management` acrescenta o Portainer. Consulte `docker-compose.yml` para ver a composição de cada perfil.

| Serviço | Porta local | Perfil | Uso |
| --- | ---: | --- | --- |
| Dashboard do laboratório | 9090 | sempre | Links, estado/controle dos serviços, documentação, resets, atualizações e destino da Sala de Aula |
| `system-updater` | — (rede interna) | sempre | Consulta o branch padrão do GitHub e aplica atualizações solicitadas pelo dashboard |
| Open WebUI | 3000 | sempre | Chat, upload e interface de modelos |
| n8n | 5678 | `full`, `workflows` | Workflows e automações |
| LiteLLM | 4000 | sempre | Gateway de modelos OpenAI compatível |
| Ollama | 11434 | sempre | Execução de modelos locais |
| Python MCP | 8000 | sempre | API e ferramentas MCP em `/mcp` |
| PostgreSQL | 5432 | sempre | Persistência das aplicações |
| Redis | 6379 | sempre | Cache e memória de curta duração |
| Flowise | 3001 | `full`, `visual-agents` | Fluxos visuais de agentes |
| Phoenix | 6006, OTLP 4317 | sempre | Tracing e avaliação LLM/RAG |
| Apache Tika | 9998 | `full`, `documents` | Extração de texto e OCR |
| Faster-Whisper | 8001 | `full`, `voice` | Transcrição de áudio |
| OpenEDAI Speech | 8002 | `full`, `voice` | Síntese de voz |
| Qdrant | 6333 | `full`, `vector` | Armazenamento vetorial |
| Neo4j | 7474, Bolt 7687 | `full`, `graph` | Dados em grafo |
| Browserless | 3002 | `full`, `browser` | Chromium headless |
| Portainer | 9001 | `management` | Inspeção de containers; não inicia no perfil de aprendizagem |
| JupyterLab | 8888 | `full` | Notebooks persistentes e bibliotecas para IA, dados, MCP e acesso aos serviços locais |

As portas publicadas ficam vinculadas a `127.0.0.1`, para acesso apenas nesta máquina. Aplicações em containers conversam pela rede interna `ai_network`; não use `localhost` entre containers. Volumes nomeados guardam modelos e dados no armazenamento do Docker do host: no Windows, dentro do Ubuntu WSL; no Linux nativo, no próprio Ubuntu. Esses dados não são transferidos automaticamente de uma instalação para a outra.

No dashboard, **Documentação** abre o índice de guias por container e **Configurações** permite zerar um serviço ou o laboratório inteiro. O reset individual apaga os dados persistentes ligados ao serviço; o reset do PostgreSQL afeta também os bancos de n8n, Flowise, Open WebUI, LiteLLM e Phoenix. O reset do Redis limpa o cache compartilhado; os resets do LiteLLM e do Python MCP também limpam esse cache para restaurar seus estados iniciais, afetando temporariamente o cache e a memória compartilhada com outros serviços. O reset do Jupyter apaga notebooks e arquivos salvos. O reset completo limpa todos os volumes do projeto, recria os bancos iniciais e baixa novamente `llama3.2:3b` e `nomic-embed-text`; exige digitar a confirmação mostrada no painel. Arquivos do projeto, `.env`, WSL e imagens Docker são preservados.

Em **Configurações**, informe a URL HTTP ou HTTPS da plataforma de aulas para habilitar o botão **Sala de Aula** na página inicial. Sem um destino configurado, o cartão informa que está em construção e oferece um atalho para essa configuração. O endereço é salvo no volume persistente do dashboard e permanece após atualizações do projeto e resets dos dados dos alunos; deixe o campo vazio e salve para remover o destino.

Em **Configurações**, **Verificar atualizações** consulta o branch padrão diretamente no GitHub, sem depender da branch, dos commits ou das alterações pendentes da cópia local. **Atualizar sistema** sincroniza o código com o branch padrão publicado, inclusive quando não há um commit novo para reaplicar. Antes de trocar os arquivos, o atualizador guarda alterações locais e não rastreadas em um backup do Git; elas não são mescladas automaticamente. O arquivo `.env` e os volumes nomeados são preservados. A operação exige digitar `ATUALIZAR LABORATÓRIO`, valida o Compose, atualiza imagens e recria os serviços dos perfis `full` e `management`. Os containers podem reiniciar e as imagens podem exigir vários gigabytes de download. `UPDATER_TOKEN` é local ao `.env`; `GITHUB_TOKEN` é opcional para remotos privados via HTTPS. Nunca publique `.env`.

O JupyterLab usa o volume persistente `jupyter_storage`, inclui bibliotecas Python para dados e APIs de IA e recebe endpoints internos por variáveis de ambiente (`OLLAMA_HOST`, `OPENAI_BASE_URL`, `QDRANT_URL`, `NEO4J_URI`, `REDIS_URL`, `PYTHON_MCP_URL` e outras). No Ubuntu nativo ou no Ubuntu WSL, execute `bash scripts/abrir_jupyter.sh`. As instruções e um exemplo inicial ficam em `learning\notebooks\INICIO.md`.

## Modelos locais

O laboratório baixa `llama3.2:3b` para um primeiro uso leve e `nomic-embed-text` para embeddings. Outros modelos configurados no gateway, como `llama3.1:8b`, são baixados pelo Ollama quando solicitados. Em uma GPU com 8 GB de VRAM, comece pelo modelo 3B; o 8B pode exigir quantização e reduzir espaço disponível para contexto.

O Ollama usa GPU NVIDIA quando o host e o runtime Docker estão configurados para isso; sem GPU compatível, os modelos executam em CPU com menor desempenho.

Veja a [arquitetura atual](docs/ARCHITECTURE.md), a [análise técnica e roteiro de evolução](docs/ANALISE_E_PLANO.md) e as [instruções para agentes de programação](AGENTS.md).
