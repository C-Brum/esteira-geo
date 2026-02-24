#!/bin/bash

# =====================================================
# Docker Development Helper Script for Linux/macOS
# =====================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "\n${CYAN}$(printf '=%.0s' {1..60})${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}$(printf '=%.0s' {1..60})${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

show_status() {
    print_header "Docker Containers Status"
    docker-compose ps
    echo ""
    print_info "Endpoints:"
    print_info "  Flask Dashboard: http://localhost:5000"
    print_info "  MinIO Console: http://localhost:9001 (user: minioadmin)"
    print_info "  PostgreSQL: localhost:5432"
}

start_environment() {
    print_header "Starting Esteira Geo Docker Environment"
    
    # Check if Docker is running
    if ! docker ps -q &>/dev/null; then
        print_error "Docker daemon is not running!"
        print_info "Please start Docker daemon."
        exit 1
    fi
    
    print_info "Building images..."
    docker-compose build
    
    print_info "Starting containers..."
    docker-compose up -d
    
    print_info "Waiting for services to be healthy..."
    sleep 10
    
    show_status
    print_success "Environment started! Waiting for PostGIS and MinIO to initialize..."
    print_info "This may take another 10-20 seconds. Check status: ./docker.sh status"
}

stop_environment() {
    print_header "Stopping Esteira Geo Docker Environment"
    docker-compose down
    print_success "Environment stopped"
}

show_logs() {
    local service=$1
    
    if [ -n "$service" ]; then
        print_header "Logs for $service"
        docker-compose logs -f --tail=50 "$service"
    else
        print_info "Available services: postgis, minio, pipeline, web"
        print_info "Usage: ./docker.sh logs postgis"
        docker-compose logs --tail=20
    fi
}

run_pipeline() {
    print_header "Running Full Pipeline ETL"
    print_info "Executing: Bronze -> Silver -> Gold -> PostGIS"
    
    docker-compose exec -T pipeline python /app/pipeline/main.py
    
    print_success "Pipeline completed!"
}

access_shell() {
    print_header "Accessing Pipeline Container Shell"
    docker-compose exec pipeline bash
}

run_tests() {
    print_header "Running Pipeline Tests"
    
    print_info "1. Creating Bronze data..."
    docker-compose exec -T pipeline python -c "from pipeline.etl.bronze_loader import load_sample_data; load_sample_data()"
    
    print_info "2. Processing Silver layer..."
    docker-compose exec -T pipeline python -c "from pipeline.etl.silver_processor import process_silver; process_silver()"
    
    print_info "3. Processing Gold layer (spatial join)..."
    docker-compose exec -T pipeline python -c "from pipeline.etl.gold_processor import process_gold; process_gold()"
    
    print_info "4. Loading to PostGIS..."
    docker-compose exec -T pipeline python -c "from pipeline.etl.postgis_loader import load_to_postgis; load_to_postgis()"
    
    print_success "All tests completed!"
}

clean_environment() {
    print_header "Cleaning Docker Environment"
    
    read -p "This will remove all containers and volumes. Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cancelled."
        return
    fi
    
    print_info "Removing containers and volumes..."
    docker-compose down -v
    
    print_info "Removing logs..."
    rm -rf logs
    
    print_success "Environment cleaned"
}

access_database() {
    print_header "Accessing PostgreSQL Database"
    
    print_info "Connecting to esteira_geo database..."
    docker-compose exec postgis psql -U esteira_user -d esteira_geo
}

access_minio() {
    print_header "MinIO Console"
    
    print_info "URL: http://localhost:9001"
    print_info "User: minioadmin"
    print_info "Pass: minioadmin123"
    
    # Try to open in browser (Linux/macOS)
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:9001" 2>/dev/null &
        print_info "Opening in browser (Linux)..."
    elif command -v open &> /dev/null; then
        open "http://localhost:9001" 2>/dev/null &
        print_info "Opening in browser (macOS)..."
    else
        print_info "Please open http://localhost:9001 in your browser"
    fi
}

show_help() {
    echo ""
    echo -e "${CYAN}Esteira Geo Docker Helper${NC}"
    echo ""
    echo "Usage: ./docker.sh [command]"
    echo ""
    echo "Commands:"
    echo "  up        - Start Docker environment"
    echo "  down      - Stop Docker environment"
    echo "  status    - Show container status"
    echo "  logs      - Show logs (optionally: logs [service])"
    echo "  pipeline  - Run full ETL pipeline"
    echo "  shell     - Access pipeline container shell"
    echo "  test      - Run all tests"
    echo "  db        - Access PostgreSQL database"
    echo "  minio     - Open MinIO Console"
    echo "  clean     - Clean all containers and volumes"
    echo ""
    echo "Examples:"
    echo "  ./docker.sh up"
    echo "  ./docker.sh logs pipeline"
    echo "  ./docker.sh pipeline"
    echo ""
}

# Main command dispatcher
case "${1:-status}" in
    up)
        start_environment
        ;;
    down)
        stop_environment
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    pipeline)
        run_pipeline
        ;;
    shell)
        access_shell
        ;;
    test)
        run_tests
        ;;
    clean)
        clean_environment
        ;;
    db)
        access_database
        ;;
    minio)
        access_minio
        ;;
    -h|--help|help)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
