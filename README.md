# Laboratório de IA

Desenvolvido por **Georges Lucas Silva Queiroz de Albuquerque** · [GitHub](https://github.com/georgeslucas50) · [LinkedIn](https://www.linkedin.com/in/georges-lucas-0928123b3/)

Ambiente local de estudo para modelos, aplicações de chat, automações e serviços de apoio a RAG. O laboratório pode rodar no Ubuntu pelo WSL 2 no Windows ou diretamente em uma instalação nativa do Ubuntu. As duas opções usam os mesmos arquivos Docker Compose; cada host mantém suas próprias imagens, modelos e volumes. A GPU NVIDIA é opcional; com driver compatível, o Ollama usa a GPU, e sem ela funciona em CPU.

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

O instalador instala o Docker Engine e o plugin Docker Compose oficiais quando eles não estão disponíveis, cria ou completa `.env` sem substituir valores locais já preenchidos, valida a configuração e sobe os perfis `full` e `management`. Se identificar uma GPU NVIDIA com driver funcional, instala o NVIDIA Container Toolkit, testa o acesso à GPU e habilita o complemento Compose; essa configuração reinicia o Docker Engine e pode reiniciar brevemente containers de outros projetos. Caso contrário, sobe o laboratório em CPU. Se encontrar pacotes Docker incompatíveis, o instalador para sem removê-los ou apagar dados existentes. No primeiro uso, o seu usuário é incluído no grupo `docker`; encerre e reabra a sessão do Ubuntu para executar comandos Docker sem `sudo`. Esse grupo concede privilégios equivalentes a root.

Depois da instalação, acesse [http://localhost:9090/dashboard](http://localhost:9090/dashboard). Para abrir o JupyterLab com autenticação, execute `./scripts/abrir_jupyter.sh`.

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

O Compose define 18 serviços. O perfil `full` inicia os 17 serviços de aprendizagem; Portainer fica separado no perfil de administração `management`. Oito serviços essenciais iniciam sem perfil. Os instaladores Windows e Linux ativam os dois perfis e sobem os 18 serviços; numa execução manual, use só `full` para deixar Portainer parado.

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

As portas publicadas ficam vinculadas a `127.0.0.1`, para acesso apenas nesta máquina. Aplicações em containers conversam pela rede interna `ai_network`; não use `localhost` entre containers. Volumes nomeados guardam modelos e dados no armazenamento do Docker do host: no Windows, dentro do Ubuntu WSL; no Linux nativo, no próprio Ubuntu. Esses dados não são transferidos automaticamente de uma instalação para a outra.

No dashboard, **Documentação** abre o índice de guias por container e **Configurações** permite zerar um serviço ou o laboratório inteiro. O reset individual apaga os dados persistentes ligados ao serviço; o reset do PostgreSQL afeta também os bancos de n8n, Flowise, Open WebUI, LiteLLM e Phoenix. O reset do Redis limpa o cache compartilhado; os resets do LiteLLM e do Python MCP também limpam esse cache para restaurar seus estados iniciais, afetando temporariamente o cache e a memória compartilhada com outros serviços. O reset do Jupyter apaga notebooks e arquivos salvos. O reset completo limpa todos os volumes do projeto, recria os bancos iniciais e baixa novamente `llama3.2:3b` e `nomic-embed-text`; exige digitar a confirmação mostrada no painel. Arquivos do projeto, `.env`, WSL e imagens Docker são preservados.

Em **Configurações**, **Verificar atualizações** consulta o branch padrão diretamente no GitHub, sem depender da branch, dos commits ou das alterações pendentes da cópia local. **Atualizar sistema** sincroniza o código com o branch padrão publicado, inclusive quando não há um commit novo para reaplicar. Antes de trocar os arquivos, o atualizador guarda alterações locais e não rastreadas em um backup do Git; elas não são mescladas automaticamente. O arquivo `.env` e os volumes nomeados são preservados. A operação exige digitar `ATUALIZAR LABORATÓRIO`, valida o Compose, atualiza imagens e recria os serviços dos perfis `full` e `management`. Os containers podem reiniciar e as imagens podem exigir vários gigabytes de download. O instalador cria um token interno aleatório em `.env`; `GITHUB_TOKEN` é opcional e só deve ser preenchido localmente para remotos privados via HTTPS. Nunca publique `.env`.

Em instalações antigas feitas pelo ZIP, execute o instalador atualizado para que ele tente preparar os metadados Git sem substituir arquivos locais. Para novas instalações, use sempre `git clone` como mostrado acima. Se os arquivos locais diferirem do repositório remoto, o dashboard bloqueará a atualização até que as diferenças sejam resolvidas.

O JupyterLab usa o volume persistente `jupyter_storage`, inclui bibliotecas Python para dados e APIs de IA e recebe endpoints internos por variáveis de ambiente (`OLLAMA_HOST`, `OPENAI_BASE_URL`, `QDRANT_URL`, `NEO4J_URI`, `REDIS_URL`, `PYTHON_MCP_URL` e outras). No Windows, execute `scripts\abrir_jupyter.ps1`; no Ubuntu nativo, execute `./scripts/abrir_jupyter.sh`. As instruções e um exemplo inicial ficam em `learning\notebooks\INICIO.md`.

## Modelos locais

O laboratório baixa `llama3.2:3b` para um primeiro uso leve e `nomic-embed-text` para embeddings. Outros modelos configurados no gateway, como `llama3.1:8b`, são baixados pelo Ollama quando solicitados. Em uma GPU com 8 GB de VRAM, comece pelo modelo 3B; o 8B pode exigir quantização e reduzir espaço disponível para contexto.

Para confirmar a GPU dentro do Ubuntu WSL:

```powershell
wsl -d Ubuntu-24.04 -- nvidia-smi
```

No Ubuntu nativo, confira o driver com `nvidia-smi`. O instalador habilita a GPU somente depois de validar o driver do host, o NVIDIA Container Toolkit e o acesso a partir de um container. Consulte a [documentação oficial de instalação do Docker para Ubuntu](https://docs.docker.com/engine/install/ubuntu/) e a [documentação do NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) para requisitos e solução de problemas.

Se não houver GPU NVIDIA, use os modelos em CPU; o desempenho será menor.

Veja a análise e as etapas recomendadas em [docs/ANALISE_E_PLANO.md](docs/ANALISE_E_PLANO.md).
