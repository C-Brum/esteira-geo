-- PostGIS Initialization Script for Docker
-- Este script é executado automaticamente ao iniciar o container
-- Cria apenas as extensões e schemas, sem dependências de tabelas

-- 1. Criar extensões PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- 2. Exibir versão instalada
SELECT postgis_version();

-- Sucesso: Extensões criadas
-- As tabelas serão criadas pelo pipeline Python quando executar
