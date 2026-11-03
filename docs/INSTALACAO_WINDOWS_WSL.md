# Instalação manual no Windows com WSL 2

Este guia prepara uma instalação local do laboratório no Ubuntu 24.04 dentro do WSL 2. O aluno instala o WSL, o Docker Engine e, por fim, os serviços do projeto com Docker Compose. Não execute scripts PowerShell de preparação do ambiente: o processo é manual.

## Requisitos

- Windows 11 ou Windows 10 atualizado, virtualização habilitada na BIOS/UEFI.
- Recomendado: 16 GB de RAM (32 GB para modelos maiores) e pelo menos 40 GB livres em disco.
- Acesso à internet para instalar Ubuntu, Docker, imagens e modelos.
- Para melhor desempenho, mantenha o repositório dentro do sistema de arquivos Linux do WSL (`/home/...`), não em `/mnt/c`.

Se você já executou o antigo instalador PowerShell e ele solicitou reinicialização, confira se ficou uma tarefa agendada para retomar a instalação. No PowerShell, execute:

```powershell
Get-ScheduledTask -TaskName 'LaboratorioIA-ContinuarInstalacao' -ErrorAction SilentlyContinue
```

Se essa tarefa existir, remova apenas a retomada antiga:

```powershell
Unregister-ScheduledTask -TaskName 'LaboratorioIA-ContinuarInstalacao' -Confirm:$false
```

## 1. Instale WSL 2 e Ubuntu 24.04

Abra o **PowerShell como Administrador** e execute:

```powershell
wsl --install -d Ubuntu-24.04
```

Reinicie o Windows se for solicitado. Abra **Ubuntu 24.04** pelo menu Iniciar. Na primeira abertura, crie seu usuário Linux e sua senha. Guarde a senha: o Ubuntu a pedirá para comandos `sudo`.

No PowerShell, confirme que a distribuição está na versão 2:

```powershell
wsl --update
wsl --set-default-version 2
wsl --list --verbose
```

Se a coluna `VERSION` de `Ubuntu-24.04` mostrar `1`, converta a distribuição:

```powershell
wsl --set-version Ubuntu-24.04 2
```

## 2. Confirme o systemd no Ubuntu

No terminal Ubuntu, execute:

```bash
ps -p 1 -o comm=
```

Se a saída for `systemd`, siga para a etapa 3. Caso contrário, atualize o WSL no PowerShell (`wsl --update`), abra `/etc/wsl.conf` no Ubuntu e adicione a seção abaixo. Se o arquivo já tiver uma seção `[boot]`, acrescente `systemd=true` nela em vez de criar uma seção duplicada:

```bash
sudo nano /etc/wsl.conf
```

```ini
[boot]
systemd=true
```

Salve e feche o editor. No PowerShell, encerre apenas esta distribuição e abra o Ubuntu novamente:

```powershell
wsl --terminate Ubuntu-24.04
```

Confirme que `ps -p 1 -o comm=` agora mostra `systemd`. A configuração do WSL é por distribuição; não use `wsl --shutdown` se outras distribuições estiverem trabalhando.

## 3. Instale Docker Engine e o plugin Compose no Ubuntu

Execute estes comandos **dentro do Ubuntu**, não no PowerShell. Eles configuram o repositório oficial do Docker para Ubuntu e instalam o Engine, o CLI e o plugin Compose:

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

Valide a instalação antes de prosseguir:

```bash
sudo docker run hello-world
sudo docker compose version
sudo systemctl status docker --no-pager
```

Os comandos Compose deste guia usam `sudo`. Não é necessário adicionar o usuário ao grupo `docker`, que concede privilégios equivalentes a root. Este procedimento instala Docker Engine dentro do Ubuntu WSL; não configure também o Docker Desktop para controlar o mesmo daemon.

## 4. Clone o projeto dentro do Ubuntu

Instale Git e OpenSSL e clone o repositório no diretório Linux do usuário. Não use **Code → Download ZIP**: o atualizador do dashboard precisa do histórico e do remoto Git.

Se você já executou uma versão anterior do laboratório nesta distribuição, pare os containers antigos **antes de excluir a pasta antiga**. No terminal antigo, dentro da pasta do projeto, execute `sudo docker compose --profile full --profile management stop`. Guarde o `.env` antigo e copie-o para o novo clone se quiser manter os volumes de dados: as senhas nele precisam continuar correspondendo aos bancos já inicializados. Não remova volumes durante a migração.

```bash
sudo apt install -y git openssl
cd ~
git clone https://github.com/georgeslucas50/lab_ia.git
cd ~/lab_ia
```

Mantenha esta pasta no mesmo local. Atualizações futuras do dashboard usam o remoto `origin` deste clone.

## 5. Crie as credenciais locais

O Compose precisa de credenciais para os bancos, serviços e notebook. Copie o modelo e gere valores aleatórios no arquivo `.env`:

```bash
cp .env.example .env

set_env() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" .env; then
    sed -i "s|^${key}=.*|${key}=${value}|" .env
  else
    printf '%s=%s\n' "$key" "$value" >> .env
  fi
}

for key in POSTGRES_PASSWORD LITELLM_SALT_KEY N8N_ENCRYPTION_KEY FLOWISE_SECRET_KEY BROWSERLESS_TOKEN JUPYTER_TOKEN UPDATER_TOKEN; do
  set_env "$key" "$(openssl rand -hex 32)"
done
set_env LITELLM_MASTER_KEY "sk-local-$(openssl rand -hex 32)"
set_env NEO4J_AUTH "neo4j/$(openssl rand -hex 32)"
chmod 600 .env
```

Não publique nem compartilhe `.env`. O arquivo contém senhas e tokens. `GITHUB_TOKEN` pode ficar vazio porque este repositório é público.

## 6. Baixe e inicie os serviços

Ainda em `~/lab_ia`, valide a configuração e inicie todos os serviços de aprendizagem e administração. Os perfis `full` e `management` iniciam os 19 containers definidos no projeto; o Portainer fica disponível para administração local, mas não faz parte das atividades do curso. O primeiro comando baixa as imagens remotas e constrói as imagens do projeto:

```bash
sudo docker compose --profile full --profile management config -q
sudo docker compose --profile full --profile management up -d --build
```

Se pretende acessar o Portainer, abra [http://localhost:9001](http://localhost:9001) assim que os containers iniciarem e crie a conta administradora em até cinco minutos. Se não for configurá-lo agora, ignore esta etapa; caso o prazo expire, inicie o serviço pelo dashboard ou execute `sudo docker compose --profile full --profile management restart portainer` e faça o cadastro.

A primeira execução pode baixar vários gigabytes e levar algum tempo. Aguarde o Ollama responder e baixe os dois modelos iniciais:

```bash
ollama_ready=false
for attempt in {1..120}; do
  if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null; then
    ollama_ready=true
    break
  fi
  sleep 3
done
if [[ "$ollama_ready" != true ]]; then
  sudo docker compose logs --tail 100 ollama
  echo 'O Ollama não iniciou. Confira os logs antes de continuar.' >&2
  exit 1
fi
sudo docker compose exec -T ollama ollama pull llama3.2:3b
sudo docker compose exec -T ollama ollama pull nomic-embed-text
```

Confirme os 19 containers. O script aguarda todos ficarem em execução e valida os healthchecks existentes; nem todos os serviços definem um healthcheck, então faça também os testes funcionais da próxima etapa.

```bash
sudo bash scripts/aguardar_servicos.sh "$PWD"
sudo docker compose --profile full --profile management ps
```

Abra no navegador do Windows:

- Dashboard: [http://localhost:9090/dashboard](http://localhost:9090/dashboard)
- Página inicial: [http://localhost:9090](http://localhost:9090)
- Open WebUI: [http://localhost:3000](http://localhost:3000)
- JupyterLab: execute `bash scripts/abrir_jupyter.sh` no Ubuntu; se o navegador não abrir automaticamente, copie o endereço exibido para o navegador do Windows.

## 7. Faça o primeiro acesso e valide o laboratório

As credenciais técnicas geradas na etapa 5 não criam automaticamente contas de usuário nas interfaces. Na primeira abertura, configure as contas abaixo e guarde as senhas em local seguro. O `.env` é local e contém chaves de serviços; não o envie a colegas nem o publique.

| Serviço | Endereço | Primeiro acesso |
| --- | --- | --- |
| Dashboard | [http://localhost:9090/dashboard](http://localhost:9090/dashboard) | Não exige conta. Confira se os serviços aparecem como online. |
| Open WebUI | [http://localhost:3000](http://localhost:3000) | Crie a primeira conta; ela recebe o papel de administrador. O cadastro é fechado automaticamente depois. |
| LiteLLM API | `http://localhost:4000/v1` | Não tem conta web de aluno. Clientes externos usam `LITELLM_MASTER_KEY` do `.env`; o Open WebUI já recebe essa chave pelo Compose. |
| n8n | [http://localhost:5678](http://localhost:5678) | Complete a tela inicial para criar a conta proprietária. Não há SMTP configurado, então a recuperação de senha por e-mail não estará disponível; guarde a senha. |
| Flowise | [http://localhost:3001](http://localhost:3001) | Siga a tela de configuração inicial e crie a conta administradora. O Compose não define `FLOWISE_USERNAME` nem `FLOWISE_PASSWORD`, portanto não há usuário ou senha padrão para usar. |
| Neo4j | [http://localhost:7474](http://localhost:7474) | Entre com o usuário `neo4j` e a senha definida em `NEO4J_AUTH` no `.env`. Essa variável define a senha inicial do volume; alterar seu valor depois não troca automaticamente a senha já gravada no banco. |
| JupyterLab | via `bash scripts/abrir_jupyter.sh` | O script lê o token local do `.env`, verifica o serviço e mostra o endereço autenticado. Não compartilhe esse endereço, pois ele contém o token. |
| Phoenix | [http://localhost:6006](http://localhost:6006) | Não exige conta nesta instalação local. Os traces enviados pelo LiteLLM aparecem após uma chamada de modelo instrumentada. |
| Qdrant | [http://localhost:6333/dashboard](http://localhost:6333/dashboard) | Não exige conta nesta instalação local. É uma interface de inspeção do banco vetorial. |
| Portainer | [http://localhost:9001](http://localhost:9001) | Não é usado nas aulas. A conta administradora deve ser criada até cinco minutos após o container iniciar; se o prazo expirar, reinicie o serviço conforme a etapa 6. |

O Open WebUI já está configurado para chamar o LiteLLM, que encaminha a solicitação ao Ollama. Essa conexão pode ser validada sem configurar credenciais adicionais na interface:

1. Entre no Open WebUI e selecione `llama3.2:3b` na lista de modelos.
2. Envie: `Responda apenas: laboratório funcionando.`
3. Confirme que chegou uma resposta. Isso testa o caminho Open WebUI → LiteLLM → Ollama.
4. Abra o Phoenix e verifique se a chamada gerou um trace. A primeira carga pode demorar enquanto os serviços inicializam.
5. Abra o JupyterLab pelo script auxiliar e execute uma célula com:

   ```python
   import requests
   requests.get("http://ollama:11434/api/tags", timeout=10).json()
   ```

   Uma resposta JSON com os modelos confirma a comunicação do notebook com o Ollama pela rede Docker.

No n8n, um teste independente de APIs externas é criar um workflow com **Manual Trigger** e **Edit Fields (Set)**, executar e confirmar que o nó mostra a saída. Isso valida a interface e a execução básica; não configura uma integração com IA.

As telas do n8n e Flowise começam sem fluxos didáticos importados. Suas contas e interfaces estão prontas, mas o aluno criará os workflows e agentes durante as aulas. O Flowise também não recebe uma conexão de modelo pré-configurada; configure o provedor durante a atividade usando os endpoints internos do Compose. Apenas o caminho Open WebUI → LiteLLM → Ollama já vem conectado.

PostgreSQL, Redis, Tika, Whisper, TTS, Browserless e Python MCP oferecem APIs ou serviços internos para os outros containers; não é necessário criar uma conta web para cada um durante a instalação. Browserless usa `BROWSERLESS_TOKEN` do `.env` para autenticar chamadas técnicas. A presença de Tika, Qdrant e Neo4j também não significa que já exista um pipeline RAG ou GraphRAG completo integrado.

O Portainer tem acesso administrativo ao daemon Docker. Use-o apenas localmente e não publique sua porta na rede; as portas desta stack já estão vinculadas a `127.0.0.1`.

## GPU NVIDIA (opcional)

Instale no Windows um driver NVIDIA com suporte a WSL. Não instale driver Linux NVIDIA dentro do Ubuntu WSL. Confira no Ubuntu:

```bash
nvidia-smi
```

Se o driver aparecer, instale o NVIDIA Container Toolkit no Ubuntu seguindo o [guia oficial da NVIDIA](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html), configure o runtime Docker e reinicie o Docker:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /usr/share/keyrings
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Valide a GPU em um container antes de ativá-la no laboratório:

```bash
sudo docker run --rm --runtime=nvidia --gpus all ubuntu:24.04 nvidia-smi
```

Se o teste funcionar, suba a stack usando o overlay de GPU:

```bash
sudo docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile full --profile management up -d --build
```

Se o teste falhar, use a stack sem o overlay; o Ollama funcionará em CPU.

## 8. Operação básica

Para iniciar novamente os serviços depois de abrir o Ubuntu:

```bash
cd ~/lab_ia
sudo docker compose --profile full --profile management up -d
```

Para parar os containers sem apagar os dados persistentes:

```bash
sudo docker compose --profile full --profile management stop
```

Os dados ficam em volumes Docker dentro do Ubuntu WSL. **Não use `docker compose down -v`**: essa opção apaga volumes, modelos, bancos, notebooks e dados dos serviços. Para consultar falhas, use `sudo docker compose --profile full --profile management logs --tail 100 NOME_DO_SERVICO`.

Para aplicar as alterações publicadas no GitHub, use **Configurações → Verificar atualizações** no dashboard e, quando estiver pronto, **Atualizar sistema**. O atualizador consulta o branch padrão do GitHub e preserva `.env` e volumes. A atualização pode baixar imagens e reiniciar serviços; não interrompa o WSL ou o Docker enquanto estiver em andamento.

## 9. Solução de problemas

| Sintoma | Verificação e ação |
| --- | --- |
| Docker não responde | No Ubuntu, confira `sudo systemctl status docker --no-pager` e `sudo docker info`. Se o serviço estiver parado, inicie-o com `sudo systemctl start docker`. |
| `docker compose config -q` informa variável vazia | Confira se `.env` existe em `~/lab_ia`, se os marcadores foram substituídos e se o arquivo veio de `.env.example`. Não cole o conteúdo do `.env` em chamados ou mensagens. |
| Um serviço não iniciou ou não responde | Use `sudo docker compose --profile full --profile management ps` e `sudo docker compose --profile full --profile management logs --tail 100 NOME_DO_SERVICO`. Resolva a causa antes de repetir `up -d`. |
| Erro de porta já em uso | Identifique o processo no Ubuntu com `sudo ss -lntp | grep ':PORTA'`. Não encerre processos de outros projetos sem descobrir a que serviço pertencem. |
| Open WebUI não mostra modelos ou o chat falha | Confirme que os modelos foram baixados com `sudo docker compose exec ollama ollama list`; consulte os logs de `litellm`, `ollama` e `open-webui`. O endereço entre containers é o DNS Compose (`ollama`, `litellm`), não `localhost`. |
| Jupyter pede token ou o link não abre | Execute `bash scripts/abrir_jupyter.sh` dentro de `~/lab_ia`. Confira se `JUPYTER_TOKEN` existe no `.env` e se o serviço `jupyter` está ativo no dashboard. |
| GPU não aparece | Valide primeiro `nvidia-smi` no Ubuntu e depois o teste de GPU em container da seção seguinte. Sem validação bem-sucedida, suba o Compose sem `docker-compose.gpu.yml`; o Ollama usa CPU. |
| Inicialização lenta ou falta de memória | A primeira execução baixa imagens e modelos; espere os downloads terminarem. Comece com `llama3.2:3b`, feche aplicações pesadas e mantenha espaço livre para os modelos. |

Após corrigir `.env` ou arquivos Compose, valide novamente com `sudo docker compose --profile full --profile management config -q`. Se alterou credenciais de banco após os volumes terem sido inicializados, restaurar os valores antigos do `.env` pode ser necessário; as variáveis de inicialização não trocam automaticamente senhas já gravadas nos bancos.

## Referências oficiais

- [Instalação do WSL](https://learn.microsoft.com/windows/wsl/install)
- [Systemd no WSL](https://learn.microsoft.com/windows/wsl/systemd)
- [Instalação do Docker Engine no Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [Primeiro usuário e autenticação do Open WebUI](https://docs.openwebui.com/features/authentication-access/rbac/roles/)
- [Gerenciamento de usuários no n8n](https://docs.n8n.io/deploy/host-n8n/configure-n8n/user-management/)
- [Autenticação do Flowise](https://docs.flowiseai.com/configuration/authorization/app-level)
- [Configuração inicial do Portainer](https://docs.portainer.io/start/install-ce/server/setup)
- [CUDA e GPU no WSL](https://docs.nvidia.com/cuda/wsl-user-guide/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
