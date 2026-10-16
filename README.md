# Laboratório de IA

Ambiente local de estudo para modelos, aplicações de chat, automações e serviços de apoio a RAG. O projeto usa Docker Compose dentro do Ubuntu no WSL 2. A GPU NVIDIA é opcional; com driver compatível, o Ollama usa a GPU, e sem ela funciona em CPU.

## Instalação no Windows

Requisitos recomendados: Windows 11 (ou Windows 10 21H2/build 19044+), Git para Windows, virtualização habilitada na BIOS/UEFI, 16 GB de RAM (32 GB recomendado), 8 GB de VRAM para modelos locais maiores e pelo menos 40 GB livres em disco. A instalação baixa imagens Docker e modelos de IA.

> **Importante:** clone o repositório com Git. Não use **Code → Download ZIP** no GitHub: o arquivo ZIP não inclui o histórico Git necessário para verificar e aplicar atualizações pelo dashboard.

Se o Git ainda não estiver instalado, instale o [Git para Windows](https://git-scm.com/download/win), feche e reabra o PowerShell. Depois execute:

```powershell
git -c core.autocrlf=input clone https://github.com/georgeslucas50/lab_ia.git "$HOME\lab_ia"
git -C "$HOME\lab_ia" config core.autocrlf input
Set-Location "$HOME\lab_ia"
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\preparar_ambiente.ps1
```

Essa configuração mantém os finais de linha compatíveis com os scripts Linux do WSL. O instalador solicita elevação pelo UAC quando necessário. Aceite para habilitar os componentes do Windows e configurar o WSL 2. Execute os comandos na pasta clonada; mantenha essa pasta no mesmo local para futuras atualizações.

O instalador habilita WSL 2, instala Ubuntu 24.04, configura o usuário Linux `aluno` automaticamente na distribuição nova, habilita systemd e instala Docker Compose. Uma distribuição `Ubuntu-24.04` já existente é preservada. Se detectar uma GPU NVIDIA sem driver funcional, busca o driver assinado no site da NVIDIA e instala apenas o driver de vídeo no Windows. Se o catálogo não reconhecer a GPU ou a assinatura falhar, a stack continua em CPU e informa como habilitar a GPU depois. No Ubuntu WSL, instala o NVIDIA Container Toolkit, nunca o driver Linux. Se o Windows pedir reinicialização, o instalador retoma a configuração no próximo login.

O script cria `.env` com segredos aleatórios quando o arquivo não existe e acrescenta somente chaves ausentes ou vazias quando ele já existe. Os valores preenchidos são preservados. Não compartilhe esse arquivo.

Após a instalação, os modelos iniciais `llama3.2:3b` e `nomic-embed-text` são baixados. O dashboard abre em [http://localhost:9090/dashboard](http://localhost:9090/dashboard); a página inicial fica em [http://localhost:9090](http://localhost:9090).

## Serviços e portas

O Compose define 18 serviços. O perfil `full` inicia os 17 serviços de aprendizagem; Portainer fica separado no perfil de administração `management`. Oito serviços essenciais iniciam sem perfil. O instalador Windows ativa os dois perfis e sobe os 18 serviços; numa execução manual, use só `full` para deixar Portainer parado.

| Serviço | Porta local | Perfil | Uso |
| --- | ---: | --- | --- |
| Dashboard do laboratório | 9090 | sempre | Links e estado dos serviços |
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

As portas publicadas ficam vinculadas a `127.0.0.1`, para acesso apenas nesta máquina. Aplicações em containers conversam pela rede interna `ai_network`; não use `localhost` entre containers. Volumes nomeados guardam modelos e dados no disco Linux do WSL.

No dashboard, **Documentação** abre o índice de guias por container e **Configurações** permite zerar um serviço ou o laboratório inteiro. O reset individual apaga os dados persistentes ligados ao serviço; o reset do PostgreSQL afeta também os bancos de n8n, Flowise, Open WebUI, LiteLLM e Phoenix. O reset do Redis limpa o cache compartilhado; os resets do LiteLLM e do Python MCP também limpam esse cache para restaurar seus estados iniciais, afetando temporariamente o cache e a memória compartilhada com outros serviços. O reset do Jupyter apaga notebooks e arquivos salvos. O reset completo limpa todos os volumes do projeto, recria os bancos iniciais e baixa novamente `llama3.2:3b` e `nomic-embed-text`; exige digitar a confirmação mostrada no painel. Arquivos do projeto, `.env`, WSL e imagens Docker são preservados.

Em **Configurações**, **Verificar atualizações** compara a branch local com a branch remota configurada no Git. **Atualizar sistema** só é liberado quando o repositório está limpo e há commits remotos disponíveis (ou uma aplicação anterior ficou pendente). A operação exige digitar `ATUALIZAR LABORATÓRIO`, sincroniza somente com avanço rápido, valida o Compose, atualiza imagens e recria os serviços dos perfis `full` e `management`. Os volumes nomeados são preservados; os containers podem reiniciar e as imagens podem exigir vários gigabytes de download. Alterações locais, branches divergentes e branches sem remoto são bloqueadas para evitar sobrescrever trabalho. O instalador cria um token interno aleatório em `.env`; `GITHUB_TOKEN` é opcional e só deve ser preenchido localmente para remotos privados via HTTPS. Nunca publique `.env`.

Em instalações antigas feitas pelo ZIP, execute o instalador atualizado para que ele tente preparar os metadados Git sem substituir arquivos locais. Para novas instalações, use sempre `git clone` como mostrado acima. Se os arquivos locais diferirem do repositório remoto, o dashboard bloqueará a atualização até que as diferenças sejam resolvidas.

O JupyterLab usa o volume persistente `jupyter_storage`, inclui bibliotecas Python para dados e APIs de IA e recebe endpoints internos por variáveis de ambiente (`OLLAMA_HOST`, `OPENAI_BASE_URL`, `QDRANT_URL`, `NEO4J_URI`, `REDIS_URL`, `PYTHON_MCP_URL` e outras). Para entrar com o token gerado no `.env`, execute `scripts\abrir_jupyter.ps1`. As instruções e um exemplo inicial ficam em `learning\notebooks\INICIO.md`.

## Operação

O instalador inicia a stack de aprendizagem. Para ver logs e estado, use PowerShell na pasta do projeto:

```powershell
$wslProject = (wsl -d Ubuntu-24.04 -u root -- wslpath -a (Get-Location).Path).Trim()
wsl -d Ubuntu-24.04 -u root --cd $wslProject docker compose --profile full ps
wsl -d Ubuntu-24.04 -u root --cd $wslProject docker compose --profile full stop
wsl -d Ubuntu-24.04 -u root --cd $wslProject docker compose --profile full up -d
```

`stop` para sem apagar dados. Para incluir Portainer numa aula, acrescente `--profile management` aos comandos `up` e `ps` junto com `--profile full`.

Para remover a stack e seus volumes, execute `scripts\destruir_ambiente.ps1` e digite `APAGAR`. Essa operação apaga bancos, histórico e modelos armazenados nos volumes do laboratório. Ela não remove a distribuição Ubuntu nem executa limpeza global do Docker.

## Modelos locais

O laboratório baixa `llama3.2:3b` para um primeiro uso leve e `nomic-embed-text` para embeddings. Outros modelos configurados no gateway, como `llama3.1:8b`, são baixados pelo Ollama quando solicitados. Em uma GPU com 8 GB de VRAM, comece pelo modelo 3B; o 8B pode exigir quantização e reduzir espaço disponível para contexto.

Para confirmar a GPU dentro do Ubuntu:

```powershell
wsl -d Ubuntu-24.04 -- nvidia-smi
```

Se não houver GPU NVIDIA, remova `docker-compose.gpu.yml` dos comandos Compose e use os modelos em CPU. O desempenho será menor.

## Arquitetura e limites atuais

O fluxo implementado conecta Open WebUI → LiteLLM → Ollama, com PostgreSQL, Redis, n8n, o servidor MCP e o dashboard. Tika, Whisper/TTS, Qdrant, Neo4j e Browserless são serviços prontos para uso por integrações. O repositório ainda não contém uma pipeline própria de ingestão e recuperação que ligue Tika, chunking, embeddings e Qdrant, nem um fluxo GraphRAG completo; essas partes devem ser implementadas antes de divulgar o laboratório como uma plataforma RAG pronta.

O Hermes Agent é uma opção de cliente de agentes para uma aula específica, executado no Ubuntu e apontado ao LiteLLM/MCP. Ele não é necessário para subir a infraestrutura e não precisa ser outro container permanente.

Veja a análise e as etapas recomendadas em [docs/ANALISE_E_PLANO.md](docs/ANALISE_E_PLANO.md).
