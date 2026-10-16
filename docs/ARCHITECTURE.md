# Arquitetura

O inventário dos serviços, o diagrama, a configuração Windows/WSL, os perfis Compose e as recomendações de evolução estão em [README.md](../README.md) e [ANALISE_E_PLANO.md](ANALISE_E_PLANO.md).

O perfil `full` inclui chat, modelos locais, ferramentas MCP, automação, observabilidade, documentos, voz, busca vetorial, grafo e browser headless. Portainer é optativo no perfil `management`. As portas do host estão vinculadas a `127.0.0.1`; a comunicação entre containers usa a rede `ai_network`.
