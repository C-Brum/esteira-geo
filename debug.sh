#!/bin/bash

# =====================================================
# Pipeline Debug & Test Helper Script
# Executa testes granulares e valida ambiente
# =====================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Test Docker connectivity
test_docker() {
    print_header "Testing Docker Setup"
    
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found"
        return 1
    fi
    print_success "Docker installed"
    
    if ! docker ps -q &>/dev/null; then
        print_error "Docker daemon not running"
        return 1
    fi
    print_success "Docker daemon running"
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose not found"
        return 1
    fi
    print_success "Docker Compose installed"
    
    return 0
}

# Test containers status
test_containers() {
    print_header "Testing Container Status"
    
    RUNNING=$(docker-compose ps --services --filter "status=running" 2>/dev/null | wc -l)
    TOTAL=$(docker-compose ps --services 2>/dev/null | wc -l)
    
    print_info "Running containers: $RUNNING/$TOTAL"
    docker-compose ps
    
    # Check health
    if docker-compose ps postgis | grep -q "healthy"; then
        print_success "PostgreSQL is healthy"
    else
        print_warning "PostgreSQL health status unknown or unhealthy"
    fi
    
    if docker-compose ps minio | grep -q "healthy"; then
        print_success "MinIO is healthy"
    else
        print_warning "MinIO health status unknown or unhealthy"
    fi
}

# Test PostgreSQL connection
test_postgres() {
    print_header "Testing PostgreSQL Connection"
    
    if docker-compose exec -T postgis pg_isready -U esteira_user -d esteira_geo &>/dev/null; then
        print_success "PostgreSQL is reachable"
        
        # Test with query
        RESULT=$(docker-compose exec -T postgis psql -U esteira_user -d esteira_geo -t -c "SELECT COUNT(*) FROM information_schema.tables" 2>/dev/null || echo "0")
        print_info "Database tables count: $RESULT"
    else
        print_error "Cannot connect to PostgreSQL"
        print_info "Wait 10-20 seconds for PostgreSQL to initialize"
        return 1
    fi
}

# Test MinIO connectivity
test_minio() {
    print_header "Testing MinIO Connectivity"
    
    if docker-compose exec -T minio curl -f http://localhost:9000/minio/health/live &>/dev/null; then
        print_success "MinIO is reachable"
    else
        print_warning "MinIO health check failed"
        return 1
    fi
    
    # Check buckets
    BUCKETS=$(docker-compose exec -T minio mc ls myminio/ 2>/dev/null | wc -l)
    print_info "MinIO buckets: $BUCKETS"
}

# Test Flask app
test_flask() {
    print_header "Testing Flask Application"
    
    if curl -s http://localhost:5000/health | grep -q "OK"; then
        print_success "Flask app is responding"
    else
        print_warning "Flask app not responding or not healthy"
        return 1
    fi
}

# Run data validation
validate_data() {
    print_header "Validating Data Layers"
    
    print_info "Checking Bronze layer..."
    BRONZE_COUNT=$(docker-compose exec -T pipeline python -c "
import os
import glob
files = glob.glob('/data/bronze/*.parquet')
print(len(files))
" 2>/dev/null || echo "0")
    if [ "$BRONZE_COUNT" -gt 0 ]; then
        print_success "Bronze layer has $BRONZE_COUNT files"
    else
        print_warning "No files in Bronze layer"
    fi
    
    print_info "Checking Silver layer..."
    SILVER_COUNT=$(docker-compose exec -T pipeline python -c "
import os
import glob
files = glob.glob('/data/silver/*.parquet')
print(len(files))
" 2>/dev/null || echo "0")
    if [ "$SILVER_COUNT" -gt 0 ]; then
        print_success "Silver layer has $SILVER_COUNT files"
    else
        print_warning "No files in Silver layer"
    fi
    
    print_info "Checking Gold layer..."
    GOLD_COUNT=$(docker-compose exec -T pipeline python -c "
import os
import glob
files = glob.glob('/data/gold/*.parquet')
print(len(files))
" 2>/dev/null || echo "0")
    if [ "$GOLD_COUNT" -gt 0 ]; then
        print_success "Gold layer has $GOLD_COUNT files"
    else
        print_warning "No files in Gold layer"
    fi
}

# Run specific test
run_test() {
    local test_name=$1
    
    case $test_name in
        bronze)
            print_header "Testing Bronze Layer (Data Generation)"
            docker-compose exec -T pipeline python -c "from pipeline.etl.bronze_loader import load_sample_data; load_sample_data()"
            ;;
        silver)
            print_header "Testing Silver Layer (Normalization)"
            docker-compose exec -T pipeline python -c "from pipeline.etl.silver_processor import process_silver; process_silver()"
            ;;
        gold)
            print_header "Testing Gold Layer (Spatial Join)"
            docker-compose exec -T pipeline python -c "from pipeline.etl.gold_processor import process_gold; process_gold()"
            ;;
        postgis)
            print_header "Testing PostGIS Loading"
            docker-compose exec -T pipeline python -c "from pipeline.etl.postgis_loader import load_to_postgis; load_to_postgis()"
            ;;
        pipeline)
            print_header "Testing Full Pipeline"
            docker-compose exec -T pipeline python /app/pipeline/main.py
            ;;
        *)
            print_error "Unknown test: $test_name"
            return 1
            ;;
    esac
}

# Generate diagnostic report
generate_report() {
    print_header "Generating Diagnostic Report"
    
    REPORT_FILE="diagnostics_$(date +%Y%m%d_%H%M%S).log"
    
    {
        echo "=== Esteira Geo Diagnostics Report ==="
        echo "Generated: $(date)"
        echo ""
        
        echo "=== Docker Version ==="
        docker --version
        docker-compose --version
        echo ""
        
        echo "=== Container Status ==="
        docker-compose ps
        echo ""
        
        echo "=== Docker Images ==="
        docker images | grep esteira
        echo ""
        
        echo "=== Logs (Last 50 lines each) ==="
        echo "--- Pipeline ---"
        docker-compose logs --tail=50 pipeline || echo "No logs"
        echo ""
        echo "--- PostgreSQL ---"
        docker-compose logs --tail=50 postgis || echo "No logs"
        echo ""
        echo "--- Web ---"
        docker-compose logs --tail=50 web || echo "No logs"
        echo ""
        
        echo "=== Disk Usage ==="
        docker system df
        echo ""
        
    } | tee "$REPORT_FILE"
    
    print_success "Report saved to: $REPORT_FILE"
}

# Show help
show_help() {
    echo ""
    echo -e "${CYAN}Esteira Geo - Debug & Test Helper${NC}"
    echo ""
    echo "Usage: ./debug.sh [command]"
    echo ""
    echo "Commands:"
    echo "  docker       - Test Docker setup"
    echo "  containers   - Check container status"
    echo "  postgres     - Test PostgreSQL connection"
    echo "  minio        - Test MinIO connectivity"
    echo "  flask        - Test Flask application"
    echo "  validate     - Validate data layers"
    echo "  test-bronze  - Test Bronze layer"
    echo "  test-silver  - Test Silver layer"
    echo "  test-gold    - Test Gold layer"
    echo "  test-postgis - Test PostGIS loading"
    echo "  test-all     - Run all tests"
    echo "  status       - Full diagnostic check"
    echo "  report       - Generate diagnostic report"
    echo ""
    echo "Examples:"
    echo "  ./debug.sh docker"
    echo "  ./debug.sh test-pipeline"
    echo "  ./debug.sh validate"
    echo ""
}

# Main
main() {
    case "${1:-status}" in
        docker)
            test_docker
            ;;
        containers)
            test_containers
            ;;
        postgres)
            test_postgres
            ;;
        minio)
            test_minio
            ;;
        flask)
            test_flask
            ;;
        validate)
            validate_data
            ;;
        test-bronze)
            run_test "bronze"
            ;;
        test-silver)
            run_test "silver"
            ;;
        test-gold)
            run_test "gold"
            ;;
        test-postgis)
            run_test "postgis"
            ;;
        test-all)
            run_test "bronze"
            sleep 2
            run_test "silver"
            sleep 2
            run_test "gold"
            sleep 2
            run_test "postgis"
            ;;
        status)
            test_docker && test_containers && test_postgres && test_minio && test_flask && validate_data
            print_header "✓ All checks completed"
            ;;
        report)
            generate_report
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
}

main "$@"
