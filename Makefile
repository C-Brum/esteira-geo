# Makefile for Esteira Geo Docker Development
# Usage: make [target]

.PHONY: help up down status logs pipeline shell test clean db minio setup

# Default target
help:
	@echo "Esteira Geo - Docker Development"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  setup          - Setup environment (install Docker, Python, etc)"
	@echo "  up             - Start Docker environment"
	@echo "  down           - Stop Docker environment"
	@echo "  status         - Show container status"
	@echo "  logs           - Show all logs"
	@echo "  logs-pipeline  - Show pipeline logs"
	@echo "  logs-postgis   - Show PostgreSQL logs"
	@echo "  logs-web       - Show Flask logs"
	@echo "  pipeline       - Run full ETL pipeline"
	@echo "  shell          - Access pipeline container shell"
	@echo "  test           - Run all tests"
	@echo "  bronze         - Run Bronze layer test"
	@echo "  silver         - Run Silver layer test"
	@echo "  gold           - Run Gold layer test"
	@echo "  db             - Access PostgreSQL database"
	@echo "  minio          - Open MinIO Console"
	@echo "  clean          - Clean containers and volumes"
	@echo "  prune          - Remove unused Docker resources"
	@echo ""
	@echo "Examples:"
	@echo "  make up              # Start environment"
	@echo "  make pipeline        # Run ETL"
	@echo "  make logs-pipeline   # See pipeline logs"
	@echo "  make db              # Connect to database"
	@echo ""

# Setup
setup:
	@echo "Running setup..."
	@chmod +x setup.sh docker.sh
	@./setup.sh

# Docker management
up:
	@echo "Starting Esteira Geo Docker environment..."
	@docker-compose up -d
	@sleep 5
	@docker-compose ps
	@echo ""
	@echo "✓ Environment started"
	@echo ""
	@echo "Endpoints:"
	@echo "  Flask: http://localhost:5000"
	@echo "  MinIO: http://localhost:9001"
	@echo "  PostgreSQL: localhost:5432"

down:
	@echo "Stopping Docker environment..."
	@docker-compose down
	@echo "✓ Environment stopped"

status:
	@docker-compose ps
	@echo ""
	@echo "Endpoints:"
	@echo "  Flask: http://localhost:5000"
	@echo "  MinIO: http://localhost:9001"
	@echo "  PostgreSQL: localhost:5432"

# Logging
logs:
	@docker-compose logs --tail=50 -f

logs-pipeline:
	@docker-compose logs -f --tail=100 pipeline

logs-postgis:
	@docker-compose logs -f --tail=50 postgis

logs-web:
	@docker-compose logs -f --tail=50 web

# Pipeline execution
pipeline:
	@echo "Running ETL Pipeline..."
	@docker-compose exec -T pipeline python /app/pipeline/main.py

bronze:
	@echo "Running Bronze layer..."
	@docker-compose exec -T pipeline python -c "from pipeline.etl.bronze_loader import load_sample_data; load_sample_data()"

silver:
	@echo "Running Silver layer..."
	@docker-compose exec -T pipeline python -c "from pipeline.etl.silver_processor import process_silver; process_silver()"

gold:
	@echo "Running Gold layer (spatial join)..."
	@docker-compose exec -T pipeline python -c "from pipeline.etl.gold_processor import process_gold; process_gold()"

postgis:
	@echo "Loading to PostGIS..."
	@docker-compose exec -T pipeline python -c "from pipeline.etl.postgis_loader import load_to_postgis; load_to_postgis()"

# Testing
test:
	@echo "Running all tests..."
	@echo ""
	@echo "1. Bronze layer..."
	@docker-compose exec -T pipeline python -c "from pipeline.etl.bronze_loader import load_sample_data; load_sample_data()"
	@echo ""
	@echo "2. Silver layer..."
	@docker-compose exec -T pipeline python -c "from pipeline.etl.silver_processor import process_silver; process_silver()"
	@echo ""
	@echo "3. Gold layer..."
	@docker-compose exec -T pipeline python -c "from pipeline.etl.gold_processor import process_gold; process_gold()"
	@echo ""
	@echo "4. PostGIS..."
	@docker-compose exec -T pipeline python -c "from pipeline.etl.postgis_loader import load_to_postgis; load_to_postgis()"
	@echo ""
	@echo "✓ All tests completed!"

# Interactive access
shell:
	@docker-compose exec pipeline bash

db:
	@docker-compose exec postgis psql -U esteira_user -d esteira_geo

minio:
	@echo "MinIO Console: http://localhost:9001"
	@echo "User: minioadmin"
	@echo "Pass: minioadmin123"
	@command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:9001 || echo "Please open http://localhost:9001 in your browser"

# Cleanup
clean:
	@echo "Cleaning Docker environment..."
	@docker-compose down -v
	@rm -rf logs/*
	@echo "✓ Environment cleaned"

prune:
	@echo "Pruning Docker resources..."
	@docker system prune -f
	@echo "✓ Docker resources pruned"

# Verify setup
verify:
	@echo "Verifying setup..."
	@command -v docker >/dev/null && echo "✓ Docker installed" || echo "✗ Docker not found"
	@command -v docker-compose >/dev/null && echo "✓ Docker Compose installed" || echo "✗ Docker Compose not found"
	@command -v python3 >/dev/null && echo "✓ Python 3 installed" || echo "✗ Python 3 not found"
	@test -f .env && echo "✓ .env file exists" || echo "⚠ .env file not found (run: make setup)"
	@test -d pipeline/data && echo "✓ Data directories exist" || echo "⚠ Data directories missing (run: make setup)"

# Build images
build:
	@echo "Building Docker images..."
	@docker-compose build
	@echo "✓ Images built"

rebuild:
	@echo "Rebuilding Docker images..."
	@docker-compose build --no-cache
	@echo "✓ Images rebuilt"
