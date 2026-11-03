# Análise técnica, lacunas e roteiro do curso

Este documento separa o que existe hoje no repositório do que ainda precisa ser preparado para uma aula. O Compose e o código são a fonte de verdade operacional; leia também [AGENTS.md](../AGENTS.md), [README.md](../README.md) e [ARCHITECTURE.md](ARCHITECTURE.md).

## 1. Objetivo e público

O laboratório atende alunos em instalação local individual. Neste estágio do curso, os alunos já estudaram Python, pandas e fundamentos de dados. A formação deve avançar da operação de modelos locais para integração por API, observabilidade, RAG, ferramentas, automações, agentes visuais e operação da stack.

Ao final, espera-se que o aluno consiga explicar os principais serviços, usá-los em atividades, integrar serviços por API, identificar falhas comuns e manter seus dados locais. O currículo cobre todos os serviços de aprendizagem, exceto Portainer, cuja função é administrativa.

## 2. Estado atual do repositório

- Windows usa Ubuntu 24.04 no WSL 2; Linux nativo usa Docker Engine/Compose no Ubuntu suportado. Os instaladores preparam Docker e `.env`, constroem imagens locais, baixam imagens remotas e os modelos iniciais, e aguardam os containers/healthchecks.
- GPU NVIDIA é opcional. Windows mantém o driver no host; WSL/Ubuntu configura Container Toolkit e valida o uso por um container antes de ativar o overlay. CPU é fallback.
- O Compose define 19 serviços: 17 de aprendizagem, `system-updater` e Portainer. Oito serviços de aprendizagem não usam perfil; `full` habilita mais nove; `management` habilita Portainer.
- Dashboard é uma aplicação FastAPI/Jinja2 e centraliza links, estado, ações start/stop permitidas, documentação, diagrama, resets e atualização via GitHub.
- Página inicial tem cartões Laboratório e Sala de Aula. Sala de Aula usa uma URL HTTP(S) editável em Configurações, persistida no volume `dashboard_settings`. Sem URL, mostra “Em Construção”. Isso é um link e não uma implementação de LMS.
- JupyterLab está disponível no perfil `full`, tem volume persistente e variáveis para chamar serviços internos.
- `.env` local contém credenciais e deve permanecer fora de commits e documentação.

Consulte os números atuais diretamente em `docker-compose.yml`; a contagem por perfil depende de distinguir serviços de aprendizagem de suporte/administrativos.

## 3. O que está integrado e o que ainda é lacuna

| Capacidade | Estado que deve ser assumido | Trabalho necessário antes de ensinar como fluxo completo |
| --- | --- | --- |
| Ollama + Open WebUI | Stack permite chat local e Open WebUI está configurado via endpoint LiteLLM. | Preparar aula de execução/modelos, parâmetros, comparação e Modelfile. Se a aula exigir gestão nativa direta de modelos do Ollama na UI, configurar e demonstrar essa conexão. |
| LiteLLM | Gateway OpenAI-compatível e rotas locais estão configurados; Redis e Phoenix participam da infraestrutura conforme configuração. | Conferir aliases, chaves, limites e cache atuais em `config/litellm/config.yaml` antes de escrever instruções. Não pressupor provedores de nuvem ativos. |
| Phoenix | Interface/collector existem; LiteLLM envia traces conforme configuração atual. | Exercício precisa validar uma trace real e preparar datasets/rubricas/avaliadores. Tracing isolado não avalia automaticamente qualidade ou alucinação. |
| RAG documental | Tika, modelo de embeddings e Qdrant estão disponíveis; Open WebUI possui capacidades nativas de documentos. | Criar e validar fluxo definido para a aula: extração, normalização, chunking, metadados, embeddings, indexação, busca, fontes, reindexação e limpeza. Não alegar que Tika/Qdrant sozinhos formam RAG. |
| GraphRAG | Neo4j disponível para aulas. | Criar dataset/modelo de entidades, ingestão e consultas que mostrem a diferença para busca vetorial. O container sozinho não demonstra GraphRAG. |
| Browserless | Chromium headless disponível; MCP oferece scraper. | Restringir alvos e inputs, explicar scraping versus busca web, validar limites e erros. Não tratar Browserless como buscador geral. |
| MCP | Servidor Python expõe FastAPI/FastMCP em `/mcp` e inclui ferramentas de Tika, Browserless, Redis e saúde. | Demonstrar cliente compatível, validação de parâmetros e limites. Revisar autenticação e segurança antes de exposição além da máquina local. |
| n8n e Flowise | Containers e interfaces existem, com persistência. | Preparar exemplos exportáveis, importar em ambiente limpo e verificar as integrações usadas. Não tratar cada ferramenta como um agente pronto antes de criar o fluxo. |
| Voz | Faster-Whisper STT e OpenEDAI TTS estão configurados em serviços próprios. | Testar ciclo completo no Open WebUI e registrar latência, modelos/vozes, formatos aceitos e consumo da máquina de referência. |
| Sala de Aula | Cartão configurável aponta para uma URL. | Portal, conteúdo, login, progresso, entregas e avaliações pertencem ao projeto separado; não há SSO ou API de sincronização implícita. |

## 4. Roteiro do curso

### Módulo 1 — Ollama e Open WebUI

Operar o servidor local e a interface: listar, baixar, inspecionar e remover modelos; comparar tamanho, quantização, contexto, RAM/VRAM e latência; criar customizações Modelfile; usar chat, instruções e presets do Workspace; experimentar visão quando houver modelo compatível. Diferenciar personalização/prompt de fine-tuning dos pesos.

**Prática:** criar um assistente local e comparar duas opções de modelo ou configuração com as mesmas perguntas.

### Módulo 2 — APIs, LiteLLM e Python

Usar Jupyter para fazer chamadas ao Ollama e LiteLLM, gerar embeddings, organizar resultados com Python, lidar com erros/timeouts e medir latência. Entender API compatível com OpenAI, aliases, cache Redis e papel do PostgreSQL sem aprofundar administração de banco.

**Prática:** notebook reprodutível que compara respostas e registra métricas sem salvar credenciais no código.

### Módulo 3 — Phoenix: tracing e avaliação

Ler traces/spans, entradas/saídas, latência e erros; criar exemplos e critérios explícitos para avaliação; comparar modelos e prompts; tratar conteúdo de traces como dados potencialmente sensíveis.

**Prática:** instrumentar a atividade de API e comparar duas versões com uma pequena rubrica/dataset.

### Módulo 4 — RAG documental e vetorial

Trabalhar com extração via Tika, limpeza e chunking, metadados, embeddings do Ollama, coleções Qdrant, busca semântica e apresentação de fontes. Cobrir reindexação e remoção segura.

**Prática:** responder perguntas a partir de um conjunto de documentos da aula e exibir os trechos recuperados.

### Módulo 5 — Neo4j, GraphRAG e coleta de páginas

Modelar entidades/relações, consultar Neo4j, usar Browserless/MCP para coleta controlada e comparar busca em grafo com busca vetorial. Separar scraping de web search.

**Prática:** dataset pequeno com relações explícitas e perguntas que demonstrem quando o grafo ajuda.

### Módulo 6 — MCP e ferramentas

Entender function calling e MCP, testar ferramentas disponíveis, construir uma ferramenta Python com esquema e validação, conectar ferramenta a um cliente/fluxo e limitar permissões.

**Prática:** agente que chama uma ferramenta de domínio controlado e retorna resultado estruturado.

### Módulo 7 — Automação com n8n

Usar triggers, webhooks, HTTP, condições, transformações, chamadas LiteLLM/MCP, tratamento de timeout/erro e credenciais salvas no n8n.

**Prática:** workflow acionado por webhook que chama um modelo, estrutura resultado e apresenta falhas de forma previsível.

### Módulo 8 — Fluxos e agentes visuais com Flowise

Criar fluxos com modelo, prompt, retriever e ferramentas; inspecionar conexões, contexto e estado; comparar com Python e n8n.

**Prática:** protótipo visual de RAG ou agente e análise dos limites do fluxo.

### Módulo 9 — Áudio e multimodalidade

Conectar entrada de áudio, Whisper STT, modelo e TTS; tratar imagens com modelos de visão Ollama compatíveis; avaliar qualidade, latência e limites de CPU/GPU.

**Prática:** protótipo que recebe áudio ou imagem e produz resposta textual ou falada.

### Módulo 10 — Operação e projeto final

Usar dashboard e Docker Compose sem Portainer; ler estados/healthchecks e logs; operar perfis; explicar DNS/portas, dependências, volumes, reset, backup/restore, atualização pelo GitHub e uso de RAM/VRAM. Não apagar dados sem confirmação explícita.

**Projeto final:** aplicação local com modelo, RAG sobre documentos, uma ferramenta/automação, trace Phoenix e avaliação definida. Entregar código/notebook ou export do fluxo, conjunto de avaliação e instruções de operação/diagnóstico.

## 5. Plano de evolução técnica

### Prioridade A — Repetibilidade da stack

- Fixar versões testadas/digests de imagens que ainda usam `latest`, `main` ou `main-latest`; estabelecer política e cadência de atualização.
- Manter matriz de instalação Windows/WSL com e sem GPU e Ubuntu Linux nativo, incluindo atualização e retomada após reboot.
- Verificar perfis e dashboard contra os serviços que realmente existem no Compose; diferenciar “fora do perfil”, “não criado”, “parado” e “falhou”.

### Prioridade B — Caminho de modelo e observabilidade

- Documentar caminho Open WebUI → LiteLLM → Ollama e chamada Jupyter → LiteLLM/Ollama.
- Preparar demonstração de Phoenix com trace reproduzível, dataset e avaliadores explícitos.
- Documentar configurações reais de aliases/chaves/cache; não publicar tokens ou valores de `.env`.

### Prioridade C — RAG e agentes demonstráveis

- Completar e validar uma pipeline documental com ingestão, limites de tamanho/tipo, chunking, metadados, embeddings, busca, fontes e reindexação.
- Fazer atividade separada de GraphRAG que crie e consulte relações no Neo4j.
- Proteger MCP e scraping: validar destino, bloquear redes privadas quando apropriado, impor timeout/tamanho e restringir acesso.
- Versionar exemplos n8n/Flowise exportáveis, com dados de exemplo e sem credenciais pessoais.

### Prioridade D — Dados e operação

- Documentar backup e restore de PostgreSQL, Jupyter, n8n, Qdrant e Neo4j; praticar restauração em dados descartáveis.
- Medir consumo de memória/CPU/VRAM por aula e documentar perfis enxutos para máquinas de 16 GB.
- Fixar healthchecks e mensagens do dashboard; manter resets compartilhados claramente descritos.
- Manter o destino da Sala de Aula no volume `dashboard_settings`, fora dos resets de dados didáticos.

## 6. Desempenho e segurança operacional

- Começar com `llama3.2:3b` e `nomic-embed-text`; testar modelos maiores apenas contra capacidade da máquina.
- Ollama, Chromium, Neo4j e extração de documentos podem disputar memória/CPU. Faster-Whisper está configurado em CPU para reduzir disputa de VRAM.
- Volumes Docker guardam dados em filesystem Linux do WSL ou host Linux. Evite dados pesados em `/mnt/c`; backups devem considerar volume e projeto separadamente.
- Portas locais são de loopback; acesso por rede exige desenho de segurança novo. Não publicar por padrão.
- `.env` nunca entra no Git. Tokens, arquivos de aluno, logs com prompts e dumps de banco não devem ser incluídos em suporte público.
- O reset de PostgreSQL afeta bancos de várias aplicações; o reset de Redis afeta caches e memória compartilhados.
- A instalação precisa de internet para baixar imagens/modelos. “Local” não significa que qualquer integração opcional (provedores externos, scraping, web search) seja automaticamente offline.

## 7. Referências

- [Instalação e inventário](../README.md)
- [Arquitetura](ARCHITECTURE.md)
- [Instruções para agentes](../AGENTS.md)
- [Início do Jupyter](../learning/notebooks/INICIO.md)
- [WSL e systemd](https://learn.microsoft.com/en-us/windows/wsl/)
- [Docker Compose](https://docs.docker.com/compose/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
- [FastMCP](https://gofastmcp.com/deployment/http)
