# Laboratório de IA

Desenvolvido por **Georges Lucas Silva Queiroz de Albuquerque** · [GitHub](https://github.com/georgeslucas50) · [LinkedIn](https://www.linkedin.com/in/georges-lucas-0928123b3/)

Ambiente local de estudo para modelos, aplicações de chat, automações e serviços de apoio a RAG. O laboratório pode rodar no Ubuntu pelo WSL 2 no Windows ou diretamente em uma instalação nativa do Ubuntu. As duas opções usam os mesmos arquivos Docker Compose; cada host mantém suas próprias imagens, modelos e volumes. A GPU NVIDIA é opcional; com driver compatível, o Ollama usa a GPU, e sem ela funciona em CPU.

Para manutenção do repositório, agentes de programação devem começar por [AGENTS.md](AGENTS.md). Consulte também a [arquitetura atual](docs/ARCHITECTURE.md) e a [análise técnica e roteiro de evolução](docs/ANALISE_E_PLANO.md). O README é a referência de instalação para alunos.

## Instalação no Linux nativo

O instalador automatizado atende Ubuntu LTS 22.04, 24.04 ou 26.04 em computadores x86_64/amd64 com systemd. Em outras distribuições, os arquivos Compose podem ser usados após a configuração manual do Docker Engine e, se houver GPU, do NVIDIA Container Toolkit.

Requisitos recomendados: 16 GB de RAM (32 GB recomendado), 40 GB livres em disco ou mais para modelos adicionais, virtualização habilitada quando o Ubuntu estiver em uma máquina virtual e acesso à internet. A primeira execução baixa imagens e modelos grandes. Para GPU, instale e valide primeiro o driver NVIDIA apropriado para a versão do Ubuntu; o instalador não instala drivers de vídeo no Linux.

Instale Git e clone o repositório — não use **Code → Download ZIP**, pois as atualizações do dashboard consultam o GitHub por meio do remoto Git:

```bash
sudo apt update
sudo apt install -y git
git clone https://github.com/georgeslucas50/lab_ia.git
cd lab_ia
chmod +x scripts/preparar_ambiente_linux.sh scripts/abrir_jupyter.sh
./scripts/preparar_ambiente_linux.sh
```

O instalador verifica ou instala o Docker Engine e o plugin Docker Compose oficiais, cria ou completa `.env` sem substituir valores locais preenchidos, valida e constrói as imagens locais e baixa as imagens remotas necessárias aos perfis `full` e `management`. Depois inicia os 19 serviços, baixa `llama3.2:3b` e `nomic-embed-text` e aguarda os containers ficarem em execução e os healthchecks configurados ficarem saudáveis. A primeira instalação pode levar bastante tempo e baixar vários gigabytes. Se identificar uma GPU NVIDIA com driver funcional, instala o NVIDIA Container Toolkit, testa o uso da GPU por um container e habilita o complemento Compose; essa configuração reinicia o Docker Engine e pode reiniciar brevemente containers de outros projetos. Caso contrário, sobe o laboratório em CPU. Se encontrar pacotes Docker incompatíveis, o instalador para sem removê-los ou apagar dados existentes. No primeiro uso, o seu usuário é incluído no grupo `docker`; encerre e reabra a sessão do Ubuntu para executar comandos Docker sem `sudo`. Esse grupo concede privilégios equivalentes a root.

Depois da instalação, acesse [http://localhost:9090/dashboard](http://localhost:9090/dashboard). Para abrir o JupyterLab com autenticação, execute `./scripts/abrir_jupyter.sh`.

## Instalação no Windows

A instalação no Windows é manual: o aluno instala WSL 2 e Ubuntu, configura o Docker Engine dentro do Ubuntu, clona o repositório e inicia os containers com Docker Compose. **Não execute um script PowerShell de preparação do ambiente.** Siga o [guia detalhado de instalação Windows/WSL](docs/INSTALACAO_WINDOWS_WSL.md), que também mostra como criar o `.env`, baixar as imagens e modelos iniciais, configurar as contas no primeiro acesso, validar as integrações e habilitar GPU NVIDIA opcional.

O guia usa o Docker Engine dentro da distribuição Ubuntu WSL, não o Docker Desktop. Clone o projeto dentro do diretório Linux (`/home/...`) e use `git clone`, não **Code → Download ZIP**: o atualizador do dashboard precisa do remoto e do histórico Git. As credenciais ficam em `.env`, arquivo local ignorado pelo Git; não o compartilhe.

## Serviços e portas

O Compose define 19 serviços: 17 serviços de aprendizagem, o `system-updater` de apoio e o Portainer. Oito serviços de aprendizagem iniciam sem perfil; o perfil `full` acrescenta os outros nove. Assim, `docker compose --profile full up -d` inicia 18 containers contando o atualizador, sem Portainer; o perfil `management` acrescenta o Portainer. O guia Windows e o instalador Linux usam `full` e `management`.

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

Em **Configurações**, **Verificar atualizações** consulta o branch padrão diretamente no GitHub, sem depender da branch, dos commits ou das alterações pendentes da cópia local. **Atualizar sistema** sincroniza o código com o branch padrão publicado, inclusive quando não há um commit novo para reaplicar. Antes de trocar os arquivos, o atualizador guarda alterações locais e não rastreadas em um backup do Git; elas não são mescladas automaticamente. O arquivo `.env` e os volumes nomeados são preservados. A operação exige digitar `ATUALIZAR LABORATÓRIO`, valida o Compose, atualiza imagens e recria os serviços dos perfis `full` e `management`. Os containers podem reiniciar e as imagens podem exigir vários gigabytes de download. O instalador Linux gera o token interno em `.env`; na instalação Windows manual, siga a etapa de criação de credenciais do guia. `GITHUB_TOKEN` é opcional e só deve ser preenchido localmente para remotos privados via HTTPS. Nunca publique `.env`.

Instalações antigas feitas por ZIP devem passar para um clone Git para habilitar as atualizações do dashboard. Se você já usou o laboratório no mesmo Ubuntu/WSL, pare a stack antiga antes de iniciar o clone novo e preserve o `.env` correspondente aos volumes existentes. Não apague volumes como parte da troca de pasta. Se os arquivos locais diferirem do repositório remoto, o dashboard bloqueará a atualização até que as diferenças sejam resolvidas.

O JupyterLab usa o volume persistente `jupyter_storage`, inclui bibliotecas Python para dados e APIs de IA e recebe endpoints internos por variáveis de ambiente (`OLLAMA_HOST`, `OPENAI_BASE_URL`, `QDRANT_URL`, `NEO4J_URI`, `REDIS_URL`, `PYTHON_MCP_URL` e outras). No Ubuntu nativo ou no Ubuntu WSL, execute `bash scripts/abrir_jupyter.sh`. As instruções e um exemplo inicial ficam em `learning\notebooks\INICIO.md`.

## Modelos locais

O laboratório baixa `llama3.2:3b` para um primeiro uso leve e `nomic-embed-text` para embeddings. Outros modelos configurados no gateway, como `llama3.1:8b`, são baixados pelo Ollama quando solicitados. Em uma GPU com 8 GB de VRAM, comece pelo modelo 3B; o 8B pode exigir quantização e reduzir espaço disponível para contexto.

Para confirmar a GPU dentro do Ubuntu WSL:

```powershell
wsl -d Ubuntu-24.04 -- nvidia-smi
```

No Ubuntu nativo, confira o driver com `nvidia-smi`. O instalador Linux habilita a GPU somente depois de validar o driver do host, o NVIDIA Container Toolkit e o acesso por um container. No WSL, o driver deve ser instalado no Windows e o Toolkit dentro do Ubuntu, conforme o guia manual. Consulte a [documentação oficial de instalação do Docker para Ubuntu](https://docs.docker.com/engine/install/ubuntu/) e a [documentação do NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) para requisitos e solução de problemas.

Se não houver GPU NVIDIA, use os modelos em CPU; o desempenho será menor.

Veja a [arquitetura atual](docs/ARCHITECTURE.md), a [análise técnica e roteiro de evolução](docs/ANALISE_E_PLANO.md) e as [instruções para agentes de programação](AGENTS.md).
