#!/bin/bash
# Deploy Layer 2 Runtime Components Script
# Deploys databases and runtime services for data processing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
IMAGE_VERSION="v1.0.0"  # Version for our built datakit images

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

print_banner() {
    echo -e "${BLUE}"
    echo "🚀 =================================================="
    echo "   LAYER 2: DEPLOY RUNTIME COMPONENTS"
    echo "   Databases & Service Containers"
    echo "==================================================${NC}"
    echo
    echo "This script will:"
    echo "• Start PostgreSQL database containers"
    echo "• Initialize database schemas"
    echo "• Load sample data (optional)"
    echo "• Create Docker Compose configuration"
    echo "• Validate runtime connectivity"
    echo
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking deployment prerequisites..."

    # Check if core datakit images exist
    local required_images=("bronze-pagila" "postgres-runner" "dbt-runner")
    local missing_images=()

    for image in "${required_images[@]}"; do
        if ! docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "registry.localhost/datakits/$image:latest"; then
            missing_images+=("$image")
        fi
    done

    if [ ${#missing_images[@]} -gt 0 ]; then
        log_error "Missing required datakit images: ${missing_images[*]}"
        log_error "Please run: ./scripts/build-layer2-components.sh"
        return 1
    fi

    # Check Docker availability
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        return 1
    fi

    log_success "Deployment prerequisites verified"
}

# Setup PostgreSQL databases
setup_databases() {
    log_info "Setting up PostgreSQL databases for data processing..."

    # Create network if it doesn't exist
    if ! docker network ls --format "{{.Name}}" | grep -q "data-processing-network"; then
        log_info "Creating data processing network..."
        docker network create data-processing-network
        log_success "Data processing network created"
    else
        log_info "Data processing network already exists"
    fi

    # Setup source database (Pagila sample data)
    setup_source_database

    # Setup target data warehouse
    setup_warehouse_database

    log_success "Database infrastructure ready"
}

# Setup source database
setup_source_database() {
    local container_name="pagila-source"

    if docker ps --format "table {{.Names}}" | grep -q "$container_name"; then
        log_info "Source database already running"
        return 0
    fi

    if docker ps -a --format "table {{.Names}}" | grep -q "$container_name"; then
        log_info "Starting existing source database container..."
        docker start "$container_name"
    else
        log_info "Creating Pagila source database..."
        docker run -d \
            --name "$container_name" \
            --network data-processing-network \
            -p 5432:5432 \
            -e POSTGRES_DB=pagila \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_PASSWORD=postgres \
            -v pagila-source-data:/var/lib/postgresql/data \
            postgres:15.8
    fi

    # Wait for database to be ready
    log_info "Waiting for source database to be ready..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker exec "$container_name" pg_isready -U postgres >/dev/null 2>&1; then
            log_success "Source database is ready"
            break
        fi
        sleep 2
        attempt=$((attempt + 1))
    done

    if [ $attempt -gt $max_attempts ]; then
        log_error "Source database failed to start within timeout"
        return 1
    fi
}

# Setup warehouse database
setup_warehouse_database() {
    local container_name="data-warehouse"

    if docker ps --format "table {{.Names}}" | grep -q "$container_name"; then
        log_info "Data warehouse already running"
        return 0
    fi

    if docker ps -a --format "table {{.Names}}" | grep -q "$container_name"; then
        log_info "Starting existing warehouse database container..."
        docker start "$container_name"
    else
        log_info "Creating data warehouse database..."
        docker run -d \
            --name "$container_name" \
            --network data-processing-network \
            -p 5433:5432 \
            -e POSTGRES_DB=data_warehouse \
            -e POSTGRES_USER=warehouse \
            -e POSTGRES_PASSWORD=warehouse \
            -v data-warehouse-data:/var/lib/postgresql/data \
            postgres:15.8
    fi

    # Wait for database to be ready
    log_info "Waiting for warehouse database to be ready..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker exec "$container_name" pg_isready -U warehouse >/dev/null 2>&1; then
            log_success "Warehouse database is ready"
            break
        fi
        sleep 2
        attempt=$((attempt + 1))
    done

    if [ $attempt -gt $max_attempts ]; then
        log_error "Warehouse database failed to start within timeout"
        return 1
    fi

    # Initialize schemas
    log_info "Initializing data warehouse schemas..."
    docker exec "$container_name" psql -U warehouse -d data_warehouse -c "
        CREATE SCHEMA IF NOT EXISTS bronze_pagila;
        CREATE SCHEMA IF NOT EXISTS silver_core;
        CREATE SCHEMA IF NOT EXISTS gold_analytics;
        GRANT ALL ON SCHEMA bronze_pagila TO warehouse;
        GRANT ALL ON SCHEMA silver_core TO warehouse;
        GRANT ALL ON SCHEMA gold_analytics TO warehouse;
    " || {
        log_warning "Schema initialization had issues (may already exist)"
    }

    log_success "Data warehouse schemas initialized"
}

# Load sample data
load_sample_data() {
    if [ "${SKIP_SAMPLE_DATA:-false}" = "true" ]; then
        log_info "Skipping sample data loading (--skip-sample-data specified)"
        return 0
    fi

    log_info "Loading sample data..."

    if [ -x "$SCRIPT_DIR/load-sample-data.sh" ]; then
        if "$SCRIPT_DIR/load-sample-data.sh"; then
            log_success "Sample data loaded successfully"
        else
            log_warning "Sample data loading had issues - you can load it manually later"
        fi
    else
        log_warning "Sample data loader not found or not executable"
        log_info "Run manually: ./scripts/load-sample-data.sh"
    fi
}

# Create Docker Compose configuration
create_development_compose() {
    log_info "Creating development Docker Compose configuration..."

    cat > "$REPO_ROOT/docker-compose.layer2.yml" << EOF
version: '3.8'
services:
  pagila-source:
    image: postgres:15.8
    container_name: pagila-source
    environment:
      POSTGRES_DB: pagila
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pagila-source-data:/var/lib/postgresql/data
    networks:
      - data-processing

  data-warehouse:
    image: postgres:15.8
    container_name: data-warehouse
    environment:
      POSTGRES_DB: data_warehouse
      POSTGRES_USER: warehouse
      POSTGRES_PASSWORD: warehouse
    ports:
      - "5433:5432"
    volumes:
      - data-warehouse-data:/var/lib/postgresql/data
    networks:
      - data-processing

  bronze-processor:
    image: registry.localhost/datakits/bronze-pagila:$IMAGE_VERSION
    container_name: bronze-processor
    depends_on:
      - pagila-source
      - data-warehouse
    networks:
      - data-processing
    environment:
      SOURCE_DB_URL: "postgresql://postgres:postgres@pagila-source:5432/pagila"
      TARGET_DB_URL: "postgresql://warehouse:warehouse@data-warehouse:5432/data_warehouse"
    profiles:
      - processing

  dbt-runner:
    image: registry.localhost/datakits/dbt-runner:$IMAGE_VERSION
    container_name: dbt-runner
    depends_on:
      - data-warehouse
    networks:
      - data-processing
    volumes:
      - ./layer2-dbt-projects:/opt/dbt/projects
      - ~/.dbt:/root/.dbt
    environment:
      TARGET_DB_URL: "postgresql://warehouse:warehouse@data-warehouse:5432/data_warehouse"
    profiles:
      - processing

volumes:
  pagila-source-data:
  data-warehouse-data:

networks:
  data-processing:
    name: data-processing-network
    external: true
EOF

    log_success "Docker Compose configuration created"
    log_info "Use profiles to control services:"
    log_info "  docker-compose -f docker-compose.layer2.yml up -d  # Databases only"
    log_info "  docker-compose -f docker-compose.layer2.yml --profile processing up -d  # All services"
}

# Validate deployment
validate_deployment() {
    log_info "Validating Layer 2 deployment..."

    local validation_success=true

    # Check containers are running
    local required_containers=("pagila-source" "data-warehouse")
    for container in "${required_containers[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "$container"; then
            log_success "$container is running"
        else
            log_error "$container is not running"
            validation_success=false
        fi
    done

    # Test database connectivity
    log_info "Testing database connectivity..."
    if docker exec pagila-source pg_isready -U postgres >/dev/null 2>&1; then
        log_success "Source database connectivity verified"
    else
        log_error "Source database not accessible"
        validation_success=false
    fi

    if docker exec data-warehouse pg_isready -U warehouse >/dev/null 2>&1; then
        log_success "Warehouse database connectivity verified"
    else
        log_error "Warehouse database not accessible"
        validation_success=false
    fi

    # Check schemas exist
    local schemas=$(docker exec data-warehouse psql -U warehouse -d data_warehouse -t -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('bronze_pagila', 'silver_core', 'gold_analytics');" 2>/dev/null | tr -d ' ' | grep -v '^$' | wc -l)
    if [ "$schemas" -eq 3 ]; then
        log_success "All required database schemas exist"
    else
        log_warning "Some database schemas may be missing (found $schemas/3)"
    fi

    if [ "$validation_success" = true ]; then
        log_success "Layer 2 runtime deployment validation passed"
        return 0
    else
        log_error "Layer 2 runtime deployment validation failed"
        return 1
    fi
}

# Show deployment results
show_deployment_results() {
    echo
    echo -e "${GREEN}🎉 Layer 2 Runtime Deployment Complete!${NC}"
    echo
    echo -e "${BLUE}🗄️ Database Services:${NC}"
    echo "• Source Database: postgresql://postgres:postgres@localhost:5432/pagila"
    echo "• Data Warehouse: postgresql://warehouse:warehouse@localhost:5433/data_warehouse"
    echo
    echo -e "${BLUE}🐳 Container Management:${NC}"
    echo "• Docker Compose: docker-compose -f docker-compose.layer2.yml"
    echo "• Network: data-processing-network"
    echo "• Volumes: pagila-source-data, data-warehouse-data"
    echo
    echo -e "${BLUE}🚀 Next Steps:${NC}"
    echo "1. Run end-to-end data pipeline:"
    echo "   ./scripts/run-data-pipeline.sh --full-refresh --verbose"
    echo
    echo "2. Validate data processing:"
    echo "   ./scripts/validate-data-quality.sh --verbose"
    echo
    echo "3. Connect to databases:"
    echo "   # Source: docker exec -it pagila-source psql -U postgres -d pagila"
    echo "   # Warehouse: docker exec -it data-warehouse psql -U warehouse -d data_warehouse"
    echo
    echo -e "${YELLOW}💡 Development Tips:${NC}"
    echo "• Use docker-compose.layer2.yml for container management"
    echo "• Check container logs: docker logs <container-name>"
    echo "• Clean restart: ./scripts/teardown-layer2.sh --preserve-data"
    echo
}

# Parse command line arguments
SKIP_SAMPLE_DATA=false
FORCE_RECREATE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-sample-data)
            SKIP_SAMPLE_DATA=true
            shift
            ;;
        --force-recreate)
            FORCE_RECREATE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --skip-sample-data   Skip loading sample data"
            echo "  --force-recreate     Force recreation of databases"
            echo "  -h, --help          Show this help"
            exit 0
            ;;
        *)
            log_warning "Unknown option: $1"
            shift
            ;;
    esac
done

# Main execution
main() {
    print_banner
    check_prerequisites

    if [ "$FORCE_RECREATE" = true ]; then
        log_warning "Force recreate mode - removing existing containers..."
        docker rm -f pagila-source data-warehouse 2>/dev/null || true
    fi

    local deployment_success=true

    setup_databases || deployment_success=false
    load_sample_data || true  # Sample data loading is optional
    create_development_compose || deployment_success=false
    validate_deployment || deployment_success=false

    if [ "$deployment_success" = true ]; then
        show_deployment_results
        return 0
    else
        log_error "❌ Runtime deployment failed!"
        echo
        echo -e "${RED}Deployment issues detected:${NC}"
        echo "• Check Docker container status: docker ps -a"
        echo "• Check container logs: docker logs <container-name>"
        echo "• Verify network connectivity: docker network ls"
        echo "• Try manual database connection"
        echo
        return 1
    fi
}

# Handle script errors
trap 'log_error "Runtime deployment failed at line $LINENO. Exit code: $?"' ERR

# Run main function
main "$@"
