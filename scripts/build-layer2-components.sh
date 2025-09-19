#!/bin/bash
# Build Layer 2 Static Components Script
# Builds all datakit container images and validates they work

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
REGISTRY_HOST="registry.localhost"
IMAGE_VERSION="v1.0.0"  # Version for our built datakit images

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

print_banner() {
    echo -e "${BLUE}"
    echo "🔨 =================================================="
    echo "   LAYER 2: BUILD STATIC COMPONENTS"
    echo "   Container Images & DBT Projects"
    echo "==================================================${NC}"
    echo
    echo "This script will:"
    echo "• Build all datakit container images"
    echo "• Push images to local registry"
    echo "• Validate DBT project configurations"
    echo "• Prepare static components for deployment"
    echo
}

# Component definitions
declare -A DATAKITS=(
    ["bronze-pagila"]="Raw data ingestion with audit trails"
    ["postgres-runner"]="PostgreSQL operations and utilities"
    ["dbt-runner"]="DBT transformations orchestration"
    ["sqlserver-runner"]="SQL Server operations and utilities"
)

# Skip Spark for now due to Java dependency issues
declare -A OPTIONAL_DATAKITS=(
    ["spark-runner"]="Spark processing for large datasets"
)

declare -A DBT_PROJECTS=(
    ["silver-core"]="Data cleaning and conformance"
    ["gold-dimensions"]="Slowly changing dimensions"
    ["gold-facts"]="Fact tables and metrics"
)

# Check prerequisites
check_prerequisites() {
    log_info "Checking build prerequisites..."

    # Check if platform foundation is running
    if ! curl -k -s --connect-timeout 5 https://registry.localhost/v2/_catalog >/dev/null 2>&1; then
        log_error "Layer 1 platform foundation not running"
        log_error "Please complete Layer 1 setup first"
        return 1
    fi

    # Check Docker availability
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running or not accessible"
        return 1
    fi

    log_success "Build prerequisites verified"
}

# Build single datakit with error handling
build_single_datakit() {
    local datakit="$1"
    local description="$2"

    if [ ! -d "$REPO_ROOT/layer2-datakits/$datakit" ]; then
        log_error "Datakit directory not found: layer2-datakits/$datakit"
        return 1
    fi

    local image_name="$REGISTRY_HOST/datakits/$datakit"

    # Check if image already exists (unless force rebuild)
    if [ "${FORCE_REBUILD:-false}" = "false" ]; then
        if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$image_name:$IMAGE_VERSION"; then
            log_success "$datakit:$IMAGE_VERSION already exists - skipping build"
            return 0
        fi
    fi

    log_info "Building $datakit: $description"
    cd "$REPO_ROOT/layer2-datakits/$datakit"

    # Build container with both latest and version tags
    if docker build -t "$image_name:$IMAGE_VERSION" -t "$image_name:latest" . 2>&1 | tee "/tmp/build_${datakit}.log"; then
        log_success "Built $datakit:$IMAGE_VERSION successfully"
    else
        log_error "Failed to build $datakit - check /tmp/build_${datakit}.log"
        return 1
    fi

    # Push both tags to local registry
    if docker push "$image_name:$IMAGE_VERSION" 2>&1 | tee -a "/tmp/build_${datakit}.log" && \
       docker push "$image_name:latest" 2>&1 | tee -a "/tmp/build_${datakit}.log"; then
        log_success "Pushed $datakit:$IMAGE_VERSION and :latest to registry"
    else
        log_error "Failed to push $datakit to registry - check /tmp/build_${datakit}.log"
        return 1
    fi

    cd "$REPO_ROOT"
    return 0
}

# Build all core datakits
build_core_datakits() {
    log_info "Building core datakit images..."

    local build_success=true
    local successful_builds=()
    local skipped_builds=()
    local failed_builds=()

    for datakit in "${!DATAKITS[@]}"; do
        # Capture what happened
        if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$REGISTRY_HOST/datakits/$datakit:$IMAGE_VERSION" && [ "${FORCE_REBUILD:-false}" = "false" ]; then
            skipped_builds+=("$datakit")
        fi

        if build_single_datakit "$datakit" "${DATAKITS[$datakit]}"; then
            if [[ ! " ${skipped_builds[*]} " =~ " $datakit " ]]; then
                successful_builds+=("$datakit")
            fi
        else
            failed_builds+=("$datakit")
            build_success=false
        fi
        echo
    done

    # Summary
    echo -e "${BLUE}Core Datakit Build Summary:${NC}"
    if [ ${#skipped_builds[@]} -gt 0 ]; then
        log_success "Already built (skipped): ${skipped_builds[*]}"
    fi
    if [ ${#successful_builds[@]} -gt 0 ]; then
        log_success "Successfully built: ${successful_builds[*]}"
    fi
    if [ ${#failed_builds[@]} -gt 0 ]; then
        log_error "Failed to build: ${failed_builds[*]}"
    fi

    return $([ "$build_success" = true ] && echo 0 || echo 1)
}

# Build optional datakits (with warnings for failures)
build_optional_datakits() {
    if [ "${BUILD_OPTIONAL:-false}" != "true" ]; then
        log_info "Skipping optional datakits (use --build-optional to include)"
        return 0
    fi

    log_info "Building optional datakit images..."

    for datakit in "${!OPTIONAL_DATAKITS[@]}"; do
        log_info "Attempting optional build: $datakit"
        if build_single_datakit "$datakit" "${OPTIONAL_DATAKITS[$datakit]}"; then
            log_success "Optional datakit built: $datakit"
        else
            log_warning "Optional datakit failed (continuing): $datakit"
            log_info "Check /tmp/build_${datakit}.log for details"
        fi
        echo
    done
}

# Setup DBT project configurations
setup_dbt_projects() {
    log_info "Setting up DBT project configurations..."

    cd "$REPO_ROOT"

    # Create profiles directory if it doesn't exist
    mkdir -p "$HOME/.dbt"

    # Check if DBT is available
    if ! command -v dbt >/dev/null 2>&1; then
        log_info "Installing DBT..."
        pip install --user "dbt-postgres==1.8.2" "dbt-core==1.8.2" || {
            log_error "Failed to install DBT"
            return 1
        }
    fi

    local setup_success=true
    local successful_projects=()
    local failed_projects=()

    for project in "${!DBT_PROJECTS[@]}"; do
        log_info "Configuring DBT project $project: ${DBT_PROJECTS[$project]}"

        if [ ! -d "layer2-dbt-projects/$project" ]; then
            log_error "DBT project directory not found: layer2-dbt-projects/$project"
            failed_projects+=("$project")
            setup_success=false
            continue
        fi

        cd "layer2-dbt-projects/$project"

        # Skip if already configured (unless force rebuild)
        if [ "${FORCE_REBUILD:-false}" = "false" ] && [ -d "dbt_packages" ]; then
            log_success "DBT project $project already configured - skipping"
            successful_projects+=("$project")
            cd "$REPO_ROOT"
            continue
        fi

        # Install DBT dependencies (optional - may fail for some projects)
        if [ -f "packages.yml" ]; then
            log_info "Installing DBT dependencies for $project..."
            if dbt deps 2>&1 | tee "/tmp/dbt_deps_${project}.log"; then
                log_success "DBT dependencies installed for $project"
            else
                log_warning "DBT deps had issues for $project - check /tmp/dbt_deps_${project}.log"
            fi
        fi

        # Create basic profiles.yml if it doesn't exist
        if [ ! -f "$HOME/.dbt/profiles.yml" ]; then
            log_info "Creating basic DBT profiles configuration..."
            cat > "$HOME/.dbt/profiles.yml" << 'EOF'
# Basic DBT profiles for development
# This will be updated by deployment scripts with actual connection details
default:
  target: dev
  outputs:
    dev:
      type: postgres
      host: localhost
      port: 5433
      user: warehouse
      password: warehouse
      dbname: data_warehouse
      schema: bronze_pagila
      threads: 4
EOF
        fi

        successful_projects+=("$project")
        cd "$REPO_ROOT"
    done

    # Summary
    echo -e "${BLUE}DBT Project Setup Summary:${NC}"
    if [ ${#successful_projects[@]} -gt 0 ]; then
        log_success "Configured projects: ${successful_projects[*]}"
    fi
    if [ ${#failed_projects[@]} -gt 0 ]; then
        log_error "Failed projects: ${failed_projects[*]}"
    fi

    return $([ "$setup_success" = true ] && echo 0 || echo 1)
}

# Validate built components
validate_components() {
    log_info "Validating built components..."

    local validation_success=true

    # Check core datakit images in registry
    log_info "Checking core datakit images..."
    for datakit in "${!DATAKITS[@]}"; do
        if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$REGISTRY_HOST/datakits/$datakit:$IMAGE_VERSION"; then
            log_success "$datakit:$IMAGE_VERSION image available in registry"
        else
            log_error "$datakit:$IMAGE_VERSION image not found in registry"
            validation_success=false
        fi
    done

    # Check optional datakit images (warnings only)
    if [ "${BUILD_OPTIONAL:-false}" = "true" ]; then
        log_info "Checking optional datakit images..."
        for datakit in "${!OPTIONAL_DATAKITS[@]}"; do
            if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$REGISTRY_HOST/datakits/$datakit:$IMAGE_VERSION"; then
                log_success "$datakit:$IMAGE_VERSION image available in registry"
            else
                log_warning "$datakit:$IMAGE_VERSION image not found in registry (optional)"
            fi
        done
    fi

    # Check DBT profiles exist
    if [ -f "$HOME/.dbt/profiles.yml" ]; then
        log_success "DBT profiles configuration exists"
    else
        log_error "DBT profiles configuration missing"
        validation_success=false
    fi

    return $([ "$validation_success" = true ] && echo 0 || echo 1)
}

# Show build results
show_build_results() {
    echo
    echo -e "${GREEN}🎉 Layer 2 Component Build Complete!${NC}"
    echo
    echo -e "${BLUE}📦 Built Components:${NC}"

    # Show successful datakit builds
    for datakit in "${!DATAKITS[@]}"; do
        if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$REGISTRY_HOST/datakits/$datakit:$IMAGE_VERSION"; then
            echo "✅ $REGISTRY_HOST/datakits/$datakit:$IMAGE_VERSION"
        fi
    done

    if [ "${BUILD_OPTIONAL:-false}" = "true" ]; then
        for datakit in "${!OPTIONAL_DATAKITS[@]}"; do
            if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$REGISTRY_HOST/datakits/$datakit:$IMAGE_VERSION"; then
                echo "✅ $REGISTRY_HOST/datakits/$datakit:$IMAGE_VERSION (optional)"
            fi
        done
    fi

    echo
    echo -e "${BLUE}🔧 Configuration:${NC}"
    echo "• DBT profiles: $HOME/.dbt/profiles.yml"
    echo "• Build logs: /tmp/build_*.log"
    echo
    echo -e "${BLUE}🚀 Next Steps:${NC}"
    echo "1. Deploy runtime components:"
    echo "   ./scripts/deploy-layer2-runtime.sh"
    echo
    echo "2. Or run everything together:"
    echo "   ./scripts/setup-layer2.sh"
    echo
}

# Parse command line arguments
BUILD_OPTIONAL=false
FORCE_REBUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build-optional)
            BUILD_OPTIONAL=true
            shift
            ;;
        --force-rebuild)
            FORCE_REBUILD=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --build-optional   Build optional components (like Spark)"
            echo "  --force-rebuild    Force rebuild of all components"
            echo "  -h, --help        Show this help"
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

    if [ "$FORCE_REBUILD" = true ]; then
        log_info "Force rebuild mode - removing existing images..."
        docker images --format "table {{.Repository}}:{{.Tag}} {{.ID}}" | \
            grep "$REGISTRY_HOST/datakits" | \
            awk '{print $2}' | \
            xargs docker rmi -f 2>/dev/null || true
    fi

    local build_success=true

    build_core_datakits || build_success=false
    build_optional_datakits || true  # Optional builds don't fail the overall process
    setup_dbt_projects || build_success=false
    validate_components || build_success=false

    if [ "$build_success" = true ]; then
        show_build_results
        return 0
    else
        log_error "❌ Component build failed!"
        echo
        echo -e "${RED}Build issues detected:${NC}"
        echo "• Check build logs in /tmp/build_*.log"
        echo "• Review error messages above"
        echo "• Try building individual components:"
        echo "  docker build -t test layer2-datakits/[component-name]"
        echo
        return 1
    fi
}

# Handle script errors
trap 'log_error "Component build failed at line $LINENO. Exit code: $?"' ERR

# Run main function
main "$@"
