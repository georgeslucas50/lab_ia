# Análise técnica e plano de evolução

## 1. Leitura do laboratório

O Compose define 18 serviços. O núcleo é formado por PostgreSQL, Redis, Ollama, LiteLLM, Open WebUI, Python MCP, Phoenix e dashboard. JupyterLab está no perfil `full`, junto a n8n, documentos, voz, construção visual de agentes, busca vetorial, grafos e navegação web. Portainer fica no perfil de administração. O dashboard customizado é a única interface central; a configuração antiga de Homepage estava órfã e foi removida.

O desenho tem bons blocos para ensino, mas o conjunto não é ainda uma plataforma de RAG/agentes integrada. Qdrant, Neo4j, Tika e Browserless sobem, porém o repositório não tem uma pipeline que extraia documentos, divida em trechos, gere embeddings, indexe no Qdrant e responda com recuperação. Também não há fluxo de GraphRAG demonstrando ingestão e consulta no Neo4j. A presença de uma porta ou container não comprova uma integração funcional.

O setup anterior dependia de criar manualmente o usuário Ubuntu, instalava ferramentas de GPU sem separar o driver do Windows do suporte a containers e tentava iniciar o MCP por uma API FastMCP removida. O instalador novo seleciona Ubuntu 24.04, inicializa um usuário via cloud-init, ativa systemd, instala Docker e expõe o MCP com o app HTTP atual do FastMCP. O dashboard consulta os serviços em paralelo e diferencia falha de rede de serviço ativo.

## 2. Serviços para manter, tornar opcionais ou adicionar

| Decisão | Serviços | Motivo |
| --- | --- | --- |
| Manter sempre ativos | PostgreSQL, Redis, Ollama, LiteLLM, Open WebUI, Python MCP, dashboard e Phoenix | Formam o caminho base de chat, ferramentas e administração. Phoenix fica ativo porque o LiteLLM envia traces para ele. |
| Manter em perfil opcional | n8n, Tika, Whisper, OpenEDAI TTS, Flowise, Qdrant, Neo4j, Browserless e Portainer | São recursos úteis em módulos específicos, mas aumentam RAM, CPU, armazenamento e tempo de inicialização. `full` ativa os serviços de aprendizagem; Portainer fica fora do padrão no perfil `management`. |
| Não inserir como container fixo | Hermes Agent | É um cliente/runtime de agentes. Faz mais sentido instalar como ferramenta optativa no Ubuntu e conectá-lo ao LiteLLM e ao MCP quando a aula tratar de agentes autônomos. |
| Incluir no perfil `full` | JupyterLab | Os notebooks são uma ferramenta central do curso; o serviço traz bibliotecas de dados/IA, persistência própria e configuração de rede para os serviços da stack. |
| Considerar após necessidade de exposição externa | Caddy ou Traefik | Só acrescenta valor se o laboratório passar a servir usuários pela rede. Hoje as portas ficam em loopback; um proxy público aumentaria a área de exposição. |
| Não adicionar ainda | Outro banco, broker ou servidor de modelos | A stack já tem PostgreSQL, Redis, Ollama, LiteLLM e dois bancos especializados. Primeiro implemente e ensine o fluxo de ponta a ponta. |

Hermes não é um servidor de modelos e não substitui Ollama, LiteLLM, n8n ou Flowise. Se adotado, deve ser uma opção de cliente: conectar ao endpoint OpenAI compatível do LiteLLM e registrar o MCP HTTP. Não deixe acesso a shell/ferramentas irrestritas em máquinas compartilhadas; use exercícios e credenciais isolados. A instalação em recipiente próprio só deve ser avaliada se a turma precisar de sessões persistentes e administradas pelo Compose.

### Portas e rede

As portas publicadas no Compose foram vinculadas a `127.0.0.1`. Isso evita que o Docker publique esses serviços em todas as interfaces da máquina. Entre containers, use nomes DNS do Compose, por exemplo `http://ollama:11434`, `http://litellm:4000` e `http://qdrant:6333`. Entre Windows e WSL 2, use `http://localhost:<porta>`.

Portainer é uma interface administrativa e tem acesso ao socket Docker. A montagem como somente leitura não transforma a API do socket numa interface sem privilégios; deixe o serviço fora do perfil de aprendizagem, ative-o apenas na aula de gestão e mantenha-o local. Configure autenticação inicial no primeiro acesso. O mesmo vale para n8n, Neo4j e Flowise: não os exponha à LAN sem autenticação e controle de acesso apropriados.

## 3. Inicialização Windows, WSL e GPU

O fluxo automatizado usa Ubuntu 24.04 no WSL 2, instala Docker Engine/Compose dentro da distribuição e executa `docker compose --profile full --profile management up -d --build`, cobrindo os 18 serviços. O script pede elevação, agenda retomada após reinicialização quando recursos do Windows ou o driver exigirem reboot, e não remove distribuições existentes. Se o catálogo ou a validação da NVIDIA falhar, instala a stack em CPU e informa como habilitar a GPU depois. O perfil GPU só é passado se `nvidia-smi` funcionar no Ubuntu.

Há dois componentes diferentes no suporte NVIDIA:

1. O driver de GPU é instalado no Windows. O script preserva um driver que já funciona; se houver GPU NVIDIA sem `nvidia-smi`, consulta o catálogo oficial, valida domínio e assinatura do instalador e instala somente o driver de vídeo.
2. O NVIDIA Container Toolkit é instalado no Ubuntu WSL para que o Docker encaminhe a GPU ao container Ollama. O instalador deliberadamente não instala um driver Linux dentro do WSL.

Sem NVIDIA compatível, o Compose inicia em CPU. Requisitos e limites de reinicialização estão descritos no README. Os modelos e dados ficam em volumes Docker no sistema de arquivos Linux do WSL. Isso mantém os dados pesados fora do diretório Windows; os arquivos de código continuam no local do projeto.

## 4. Plano de melhorias

### Etapa A — Instalação confiável e repetível

- Executar o instalador em Windows 10/11 limpo, com e sem NVIDIA, e também numa máquina que já tenha outra distribuição WSL e outros projetos Docker.
- Validar retomada após reinicialização e preservar a instalação quando a rede ou o download de imagens falhar.
- Fixar versões testadas das imagens, principalmente `latest`, `main` e `main-latest`, depois de decidir uma cadência de atualização. Manter `postgres:16-alpine` como base previsível.
- Fazer uma matriz curta de portas ocupadas, sem parar aplicações de terceiros automaticamente.

### Etapa B — Caminho didático mínimo

- Acrescentar um exemplo completo Open WebUI → LiteLLM → Ollama e outro de n8n → MCP.
- Documentar modelos compatíveis com VRAM e RAM diferentes e ensinar como iniciar/parar serviços opcionais por perfil.
- Medir o custo dos oito serviços sempre ativos e só ligar n8n no perfil `full` ou `workflows`.

### Etapa C — RAG real

- Implementar ingestão de PDF e texto: upload → Tika → normalização → chunking com metadados → embeddings via Ollama/LiteLLM → coleção no Qdrant.
- Implementar busca com filtros e apresentar trechos/fontes junto da resposta.
- Acrescentar limpeza/reindexação, limites de tamanho, tipos permitidos e proteção contra URLs arbitrárias no endpoint de ingestão.
- Manter Neo4j como uma aula separada de GraphRAG, com modelo de entidades/relacionamentos, estratégia de extração e consultas demonstráveis. Não anunciar o banco isolado como GraphRAG pronto.

### Etapa D — Segurança, observabilidade e operação

- Fixar tags ou digests de imagens e atualizar numa janela planejada, em vez de seguir `latest` em cada reinstalação.
- Manter `.env` fora do controle de versão e um `.env.example` sem credenciais. O exemplo estava idêntico ao `.env` local; foi substituído por marcadores e um `.gitignore` protege os segredos em commits futuros.
- Acrescentar autenticação ou política de acesso à API interna do MCP, validar URLs de scraping/OCR e restringir destinos privados para reduzir SSRF.
- Incluir backup/restore documentado dos volumes PostgreSQL, n8n, Qdrant e Neo4j; testar restauração antes de cada ciclo de aulas.
- Configurar explicitamente tracing do LiteLLM para Phoenix e incluir uma atividade que confirme traces e latências.
- Adicionar healthchecks onde a imagem oferece endpoint estável e distinguir “serviço fora do perfil” de “serviço com falha”.
- Registrar consumo de RAM/VRAM em uma aula padrão para recalibrar os limites por máquina.

## 5. Desempenho

- Ollama fica limitado a um modelo carregado e uma geração paralela para reduzir pressão de VRAM. O keep-alive de 10 minutos reduz recarga durante a aula; ajuste conforme o uso compartilhado.
- Use `llama3.2:3b` como opção inicial em GPUs de 8 GB e `nomic-embed-text` para embeddings. `llama3.1:8b` deve ser opcional, pois pode competir com contexto e memória da GPU.
- Faster-Whisper está em CPU int8 para não disputar VRAM do Ollama. Tika, Chromium e Neo4j podem pressionar RAM/CPU quando vários alunos iniciam tarefas pesadas ao mesmo tempo.
- O Redis ganhou limite de 256 MB; o Neo4j usa heap e page cache menores. Esses valores são pontos de partida, não substituem medição em máquinas da turma.
- Em notebooks com 16 GB de RAM, use perfis por aula em vez de abrir sempre todos os serviços. 32 GB deixa o perfil completo mais confortável.
- Os dados persistentes usam volumes nomeados no ext4 do WSL. Evite guardar modelos, bancos e caches grandes em `/mnt/c`; o código no diretório Windows pode ser usado, mas operações com muitos arquivos pequenos são mais lentas que no ext4.
- Não configure limites globais fixos de memória do WSL sem conhecer a RAM dos alunos. Se for necessário usar `.wslconfig`, forneça exemplos por faixa de RAM e ensine a reiniciar o WSL para aplicar a configuração.

## 6. Hermes Agent: decisão

**Recomendação: não subir Hermes automaticamente junto da stack.** O laboratório já inclui n8n (automação), Flowise (construtor visual), Open WebUI (chat) e Python MCP (ferramentas). Hermes seria redundante como serviço permanente para o objetivo atual e executaria num contexto de agente com permissões próprias.

Inclua-o como atividade opcional depois que o endpoint LiteLLM e o MCP estiverem documentados. A aula deve configurar o provedor OpenAI compatível para `http://localhost:4000/v1`, selecionar um modelo configurado no LiteLLM e apontar as ferramentas ao endpoint `/mcp`. Primeiro valide uma integração real com um agente; só então decida se vale manter instruções ou uma imagem própria no repositório.

## 7. Referências técnicas

- [Instalar WSL](https://learn.microsoft.com/en-us/windows/wsl/install) e [configurar systemd](https://learn.microsoft.com/en-us/windows/wsl/systemd).
- [Cloud-init no Ubuntu para WSL](https://ubuntu.com/wsl/docs/latest/howto/cloud-init/).
- [CUDA no WSL](https://docs.nvidia.com/cuda/wsl-user-guide/) e [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
- [Publicação de portas no Docker Compose](https://docs.docker.com/reference/compose-file/services/).
- [Implantação HTTP do FastMCP](https://gofastmcp.com/deployment/http) e [LiteLLM com Phoenix](https://docs.litellm.ai/docs/observability/langfuse_otel_integration).
- [Hermes Agent](https://github.com/NousResearch/hermes-agent).
