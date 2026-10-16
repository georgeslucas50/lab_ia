-- Script de Inicialização Automática de Bancos de Dados no PostgreSQL
-- Executado automaticamente pelo container postgres durante o primeiro boot

SELECT 'CREATE DATABASE litellm_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'litellm_db')\gexec

SELECT 'CREATE DATABASE n8n_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'n8n_db')\gexec

SELECT 'CREATE DATABASE flowise_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'flowise_db')\gexec

SELECT 'CREATE DATABASE openwebui_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'openwebui_db')\gexec

SELECT 'CREATE DATABASE phoenix_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'phoenix_db')\gexec
