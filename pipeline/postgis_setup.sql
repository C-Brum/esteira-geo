-- Setup do PostGIS para Esteira Geo
-- Execute esses comandos após criar as tabelas via Ansible

-- 1. Ativar PostGIS (se não estiver já ativado)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- 2. Visualizar versão instalada
SELECT postgis_version();

-- 3. Verificar tabelas criadas pelo pipeline
\dt

-- 4. Consultas de validação

-- Contar total de cidadãos
SELECT COUNT(*) as total_citizens FROM citizens;

-- Contar cidadãos afetados
SELECT COUNT(*) as affected_citizens FROM citizens WHERE affected_by_flooding = TRUE;

-- Contar cidadãos não afetados
SELECT COUNT(*) as unaffected_citizens FROM citizens WHERE affected_by_flooding = FALSE;

-- Visualizar alguns cidadãos afetados
SELECT 
    citizen_id, name, address, 
    ST_AsText(geometry) as location,
    affected_by_flooding
FROM citizens 
WHERE affected_by_flooding = TRUE
LIMIT 10;

-- Bounding box total
SELECT ST_AsText(ST_Extent(geometry)) as bbox FROM citizens;

-- 5. Análises espaciais

-- Contar cidadãos por area de enchente
SELECT 
    fa.area_name,
    COUNT(c.citizen_id) as affected_count
FROM flooding_areas fa
LEFT JOIN citizens c ON ST_Contains(fa.geometry, c.geometry)
WHERE c.affected_by_flooding = TRUE
GROUP BY fa.area_name;

-- Distância mínima de cada cidadão para área de enchente
SELECT 
    c.citizen_id,
    c.name,
    MIN(ST_Distance(c.geometry::geography, fa.geometry::geography)) as min_distance_meters
FROM citizens c
CROSS JOIN flooding_areas fa
GROUP BY c.citizen_id, c.name
ORDER BY min_distance_meters
LIMIT 10;

-- 6. Criar view para dashboard Flask

CREATE VIEW v_citizens_summary AS
SELECT 
    'total' as category,
    COUNT(*) as count,
    0 as percentage
FROM citizens
UNION ALL
SELECT 
    'affected' as category,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM citizens), 2) as percentage
FROM citizens
WHERE affected_by_flooding = TRUE
UNION ALL
SELECT 
    'unaffected' as category,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM citizens), 2) as percentage
FROM citizens
WHERE affected_by_flooding = FALSE;

-- 7. Consultar view
SELECT * FROM v_citizens_summary;

-- 8. Criar tabela de estatísticas (opcional)

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id SERIAL PRIMARY KEY,
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_citizens INTEGER,
    affected_citizens INTEGER,
    unaffected_citizens INTEGER,
    processing_time_seconds DECIMAL,
    status VARCHAR(20)
);

-- Inserir registro de execução
INSERT INTO pipeline_runs (total_citizens, affected_citizens, unaffected_citizens, status)
SELECT 
    COUNT(*),
    COUNT(*) FILTER (WHERE affected_by_flooding = TRUE),
    COUNT(*) FILTER (WHERE affected_by_flooding = FALSE),
    'success'
FROM citizens;

-- Consultar histórico
SELECT * FROM pipeline_runs ORDER BY run_date DESC;

-- 9. Limpeza (se necessário)

-- Limpar dados
-- DELETE FROM citizens;
-- DELETE FROM flooding_areas;

-- Dropar view
-- DROP VIEW IF EXISTS v_citizens_summary;

-- Desativar PostGIS (não recomendado)
-- DROP EXTENSION postgis CASCADE;
