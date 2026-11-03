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

Ainda em `~/lab_ia`, valide a configuração e inicie todos os serviços de aprendizagem e administração. O primeiro comando baixa as imagens remotas e constrói as imagens do projeto:

```bash
sudo docker compose --profile full --profile management config -q
sudo docker compose --profile full --profile management up -d --build
```

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

Confirme os 19 serviços e os healthchecks que estão configurados:

```bash
sudo bash scripts/aguardar_servicos.sh "$PWD"
sudo docker compose --profile full --profile management ps
```

Abra no navegador do Windows:

- Dashboard: [http://localhost:9090/dashboard](http://localhost:9090/dashboard)
- Página inicial: [http://localhost:9090](http://localhost:9090)
- Open WebUI: [http://localhost:3000](http://localhost:3000)
- JupyterLab: execute `bash scripts/abrir_jupyter.sh` no Ubuntu; se o navegador não abrir automaticamente, copie o endereço exibido para o navegador do Windows.

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

## Operação básica

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

## Referências oficiais

- [Instalação do WSL](https://learn.microsoft.com/windows/wsl/install)
- [Systemd no WSL](https://learn.microsoft.com/windows/wsl/systemd)
- [Instalação do Docker Engine no Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [CUDA e GPU no WSL](https://docs.nvidia.com/cuda/wsl-user-guide/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
