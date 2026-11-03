# Instruções para agentes de programação

Este arquivo é a orientação de trabalho deste repositório. Leia-o antes de alterar código ou documentação.

## Comece por aqui

1. Rode `git status --short` e examine `git diff` antes de editar. O diretório pode conter alterações do usuário ou de outra tarefa; preserve-as e não restaure, descarte ou sobrescreva trabalho sem autorização explícita.
2. Leia o trecho relevante do [README](README.md), a [arquitetura](docs/ARCHITECTURE.md) e a [análise/roteiro](docs/ANALISE_E_PLANO.md).
3. Identifique a configuração real em `docker-compose.yml`, `docker-compose.gpu.yml`, `.env.example`, scripts e código. Não deduza que um serviço está integrado só porque seu container ou porta existe.
4. Faça alterações pequenas e localizadas. Atualize os documentos que descrevem o comportamento alterado.

## O que é este repositório

- Projeto público: `https://github.com/georgeslucas50/lab_ia`.
- É um laboratório local de IA para instalação individual de cada aluno, não uma plataforma multiusuário hospedada.
- Suporta Ubuntu nativo e Ubuntu no WSL 2 para Windows usando Docker Compose. NVIDIA é opcional; sem GPU a stack usa CPU.
- O curso parte de alunos que já estudaram Python e pandas. O roteiro do curso está em `docs/ANALISE_E_PLANO.md`.
- A página inicial e dashboard são FastAPI/Jinja2/HTML/CSS/JavaScript em `apps/dashboard`.
- Não há requisito de usar Portainer no curso. Seu perfil `management` e acesso ao socket Docker são administrativos; não amplie sua exposição.

## Fonte de verdade e documentos

- `docker-compose.yml`: serviços, imagens, portas, dependências, variáveis, perfis, rede e volumes.
- `docker-compose.gpu.yml`: reserva de GPU NVIDIA no Compose; driver fica no host Windows/Linux, não no WSL.
- `docs/INSTALACAO_WINDOWS_WSL.md`: instalação manual no Windows/WSL; não recrie o instalador PowerShell removido após falhas que afetaram a sessão do Windows.
- `scripts/preparar_ambiente_linux.sh`: instalador do Ubuntu nativo; `scripts/aguardar_servicos.sh` confirma a prontidão da stack.
- `apps/dashboard/main.py`: rotas, controle de serviços, reset, atualizador e destino da Sala de Aula.
- `apps/dashboard/templates/` e `apps/dashboard/static/`: interface, CSS e JavaScript do dashboard.
- `apps/updater/`: atualização a partir do repositório GitHub.
- `apps/python-mcp/server.py`: API e ferramentas MCP.
- `config/litellm/config.yaml`: aliases e rotas do gateway LiteLLM.
- `learning/notebooks/`: exercícios iniciais Jupyter.
- `README.md`: instalação e operação para alunos.
- `docs/ARCHITECTURE.md`: desenho atual, fluxos e estado das integrações.
- `docs/ANALISE_E_PLANO.md`: decisões técnicas, lacunas e roteiro didático.
- Mantenha `AGENTS.md` conciso e operacional. Não o use para guardar segredos, configurações privadas ou histórico de conversa.

Ao acrescentar/remover serviço, atualize no mesmo trabalho, quando aplicável: Compose, dashboard (`SERVICES_DATA`, controles, links e reset), README (serviço/porta/perfil), diagrama de arquitetura e análise técnica. Explique se o serviço é obrigatório, opcional ou apenas infraestrutura.

## Inventário operacional atual

O Compose tem 19 serviços definidos: 17 de aprendizagem, `system-updater` e `portainer`. Oito serviços de aprendizagem não usam perfil; `full` acrescenta nove serviços. Com `full`, o Docker sobe 18 containers contando o atualizador. `management` acrescenta Portainer e leva a stack para 19 containers.

| Grupo | Serviços | Papel |
| --- | --- | --- |
| Modelos e chat | `ollama`, `open-webui` | Inferência e interface do aluno. |
| Gateway e observabilidade | `litellm`, `phoenix` | Roteamento compatível com OpenAI e traces/avaliações. |
| Dados compartilhados | `postgres`, `redis` | Persistência das aplicações e cache/memória transitória; resets podem afetar vários consumidores. |
| Ferramentas e desenvolvimento | `python-mcp`, `jupyter`, `dashboard`, `system-updater` | MCP/API, notebooks, gestão local e atualização pelo GitHub. |
| Aplicações didáticas opcionais | `n8n`, `flowise` | Workflows e fluxos visuais de agentes. |
| Documentos e recuperação | `tika`, `qdrant`, `neo4j` | Extração, busca vetorial e armazenamento em grafo. A stack não implica que ingestão/RAG/GraphRAG ponta a ponta já esteja pronta. |
| Mídia e navegação | `whisper-stt`, `openedai-tts`, `browserless` | STT, TTS, Chromium headless e scraping. Browserless não é um mecanismo de busca web. |
| Administração fora do curso | `portainer` | UI administrativa do Docker, perfil `management`. |

Confira as portas e os perfis no Compose/README; não mantenha uma segunda lista contraditória em documentação auxiliar.

No Windows/WSL, mantenha o fluxo manual documentado em `docs/INSTALACAO_WINDOWS_WSL.md`: WSL/Ubuntu, systemd, Docker Engine, clone Git, `.env` com segredos, Compose, modelos iniciais e verificação dos serviços. O instalador do Ubuntu nativo deve preparar `.env`, construir serviços locais, baixar imagens remotas, subir `full` e `management`, baixar os modelos iniciais e aguardar os 19 containers (healthchecks quando definidos). Só ative `docker-compose.gpu.yml` após validar a GPU no host e em um container; falhas devem manter o fallback CPU.

## Contratos e limites que não devem ser quebrados

- Portas de host devem continuar vinculadas a `127.0.0.1`, salvo decisão explícita de redesenho e controles de acesso. Não exponha n8n, Flowise, Neo4j, MCP, Docker API ou modelos à LAN por conveniência.
- Entre containers use DNS Compose (`http://ollama:11434`, `http://litellm:4000`, etc.); `localhost` dentro de um container é aquele próprio container.
- No estado atual, Open WebUI configura a conexão compatível com OpenAI via LiteLLM. Confirme configuração real antes de afirmar que existe conexão direta ao Ollama.
- LiteLLM envia traces ao Phoenix. Trace não equivale a avaliação de qualidade; verifique a configuração de avaliadores/datasets antes de documentar avaliação automática.
- Tika, Qdrant e Neo4j são serviços disponíveis, mas uma integração RAG/GraphRAG exige código/fluxo demonstrável de ingestão, busca, recuperação e apresentação de fontes.
- `dashboard_settings` persiste a URL da Sala de Aula. O reset de dados de aprendizagem deve preservá-la, salvo pedido explícito para alterar essa política.
- `.env` contém credenciais e tokens locais. Nunca leia/cole segredos em resposta, commit, issue ou documentação; use `.env.example` somente com valores fictícios ou placeholders.
- Atualizador sincroniza a cópia local com o branch padrão do GitHub e guarda alterações locais em backup, sem mesclá-las. Não alegue que ele incorpora automaticamente alterações locais.
- Volumes nomeados guardam dados importantes. Não execute `docker compose down -v`, remova volumes, zere serviços ou reinstale WSL por iniciativa própria. Essas ações apagam dados e exigem solicitação explícita.
- Nunca pare ou remova distribuições WSL, containers ou serviços de outros projetos para liberar recursos/portas sem autorização.

## Comandos e ambiente

Execute comandos Compose no diretório clonado dentro do Ubuntu Linux/WSL correspondente. No Windows, o `docker` pode não estar no PowerShell; descubra a distribuição e o caminho WSL reais. Exemplo PowerShell, substituindo os valores pelo ambiente da máquina (se o clone estiver em `/home/aluno/lab_ia`, use esse caminho em vez de `/mnt/c/...`):

```powershell
$distroUbuntu = 'Ubuntu-24.04'
$wslProjectPath = '/mnt/c/Users/SEU_USUARIO/lab_ia'
wsl.exe -d $distroUbuntu -- bash -lc "cd '$wslProjectPath' && docker compose config -q"
```

```bash
# Validar a configuração sem iniciar os containers
docker compose config -q

# Subir serviços de aprendizagem, sem Portainer
docker compose --profile full up -d --build

# GPU: somente após validar NVIDIA Container Toolkit no Linux/WSL
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile full up -d --build

# Atualizar apenas o dashboard quando a mudança e a autorização permitirem
docker compose up -d --force-recreate dashboard
```

O serviço `dashboard` monta `apps/dashboard` como somente leitura. Templates, CSS e JavaScript são servidos do bind mount; altere a query de cache (`?v=...`) ao mudar assets. Alterações em Python já importado, como `main.py`, exigem recriar/reiniciar o container para entrar em vigor. Não reconstrua ou reinicie a stack inteira se uma atualização isolada do serviço bastar.

O reset completo do dashboard é destrutivo. Leia `RESET_VOLUME_NAMES`, `RESET_TARGETS` e `_run_reset_job` antes de alterar reset, volumes ou bancos. PostgreSQL é compartilhado por várias aplicações; Redis também contém cache/memória compartilhados.

## Forma de trabalhar

- Não assuma que uma URL ou comportamento de um documento anterior ainda corresponde ao código. Confirme contra o Compose, a rota e o frontend atual.
- Não faça reformat de arquivos inteiros para uma alteração pontual; preserve finais de linha e mudanças pré-existentes.
- Use caminhos/nomes de serviços e IDs já adotados. Atualize cache-busting de CSS/JS quando o navegador puder servir conteúdo antigo.
- Para UI, mantenha o tema escuro atual, cores violeta e verde menta, responsividade, foco visível, estados de carregamento/erro/sucesso e textos em português claro.
- Para links configuráveis, valide URL no backend, escape valores nos templates e use `rel="noopener noreferrer"` com `target="_blank"`.
- Para docs, diferencie claramente estado atual, proposta e item futuro; marque integrações incompletas em vez de apresentá-las como prontas.
- Faça validações proporcionais à mudança. Não suba a stack completa nem baixe modelos grandes apenas para inspecionar documentação. Nunca use teste de reset em dados reais.
- Não publique, faça push ou altere GitHub sem pedido explícito. Não inclua `.env`, tokens, dumps de volumes ou dados de aluno em commits.
