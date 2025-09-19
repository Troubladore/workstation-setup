#!/bin/bash
# Layer 2 Data Processing Teardown Script
# Cleans up all data processing components for fresh testing

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

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

print_banner() {
    echo -e "${BLUE}"
    echo "🧹 =================================================="
    echo "   LAYER 2: COMPONENT TEARDOWN"
    echo "   Clean Component Environment"
    echo "==================================================${NC}"
    echo
    echo "This script will clean up:"
    echo "• Datakit container images from registry"
    echo "• Component test containers"
    echo "• DBT build artifacts and packages"
    echo "• Build logs and temporary files"
    echo
}

# Stop and remove test containers
stop_containers() {
    log_info "Stopping component test containers..."

    # Stop containers by name patterns (test containers only)
    local test_containers=(
        "test-bronze-pagila"
        "test-postgres-runner"
        "test-dbt-runner"
        "test-sqlserver-runner"
        "test-spark-runner"
    )

    for container in "${test_containers[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "$container"; then
            log_info "Stopping $container..."
            docker stop "$container" 2>/dev/null || log_warning "Could not stop $container"
        fi
    done

    # Remove containers
    for container in "${test_containers[@]}"; do
        if docker ps -a --format "table {{.Names}}" | grep -q "$container"; then
            log_info "Removing $container..."
            docker rm "$container" 2>/dev/null || log_warning "Could not remove $container"
        fi
    done

    # Stop any remaining containers using our datakit images
    local running_datakits=$(docker ps --format "table {{.Names}}\t{{.Image}}" | grep "$REGISTRY_HOST/datakits" | awk '{print $1}' || true)
    if [ -n "$running_datakits" ]; then
        log_info "Stopping additional datakit containers..."
        echo "$running_datakits" | xargs docker stop 2>/dev/null || true
        echo "$running_datakits" | xargs docker rm 2>/dev/null || true
    fi

    log_success "Containers stopped and removed"
}

# Clean up test volumes
cleanup_volumes() {
    log_info "Cleaning up test volumes..."

    # Remove any temporary volumes that might be created during component testing
    docker volume ls -q | grep -E "(test|temp|tmp)" | xargs docker volume rm 2>/dev/null || true

    log_success "Test volume cleanup completed"
}

# Remove container images
cleanup_images() {
    if [ "$PRESERVE_IMAGES" = true ]; then
        log_info "Preserving datakit images for fast rebuild"
        return 0
    fi

    if [ "$FULL_CLEAN" = true ]; then
        log_info "Removing all datakit images..."
        docker images --format "table {{.Repository}}:{{.Tag}} {{.ID}}" | \
            grep "$REGISTRY_HOST/datakits" | \
            awk '{print $2}' | \
            xargs docker rmi -f 2>/dev/null || log_info "No datakit images to remove"
    else
        # Interactive mode
        log_info "Cleaning up container images..."
        echo
        echo "Choose image cleanup level:"
        echo "1) Keep datakit images (fast rebuild)"
        echo "2) Remove datakit images (complete rebuild required)"
        echo
        read -p "Enter choice (1-2): " -n 1 -r image_choice
        echo

        case $image_choice in
            2)
                log_info "Removing datakit images from registry..."
                docker images --format "table {{.Repository}}:{{.Tag}} {{.ID}}" | \
                    grep "$REGISTRY_HOST/datakits" | \
                    awk '{print $2}' | \
                    xargs docker rmi -f 2>/dev/null || log_info "No datakit images to remove"
                ;;
            *)
                log_info "Keeping container images for fast rebuild"
                ;;
        esac
    fi

    log_success "Image cleanup completed"
}

# Clean up networks (minimal for components)
cleanup_networks() {
    log_info "Cleaning up test networks..."

    # Clean up any orphaned networks created during testing
    docker network prune -f >/dev/null 2>&1 || true

    log_success "Network cleanup completed"
}

# Clean up DBT artifacts
cleanup_dbt_artifacts() {
    log_info "Cleaning up DBT build artifacts..."

    cd "$REPO_ROOT"

    # Clean up DBT artifacts in each project
    local dbt_projects=("silver-core" "gold-dimensions" "gold-facts")
    for project in "${dbt_projects[@]}"; do
        if [ -d "layer2-dbt-projects/$project" ]; then
            log_info "Cleaning $project DBT artifacts..."
            cd "layer2-dbt-projects/$project"

            # Remove DBT build artifacts
            rm -rf target/ 2>/dev/null || true
            rm -rf dbt_packages/ 2>/dev/null || true
            rm -rf logs/ 2>/dev/null || true
            rm -f profiles.yml 2>/dev/null || true

            cd "$REPO_ROOT"
        fi
    done

    log_success "DBT artifacts cleaned"
}

# Remove development configuration files
cleanup_config_files() {
    log_info "Cleaning up development configuration files..."

    cd "$REPO_ROOT"

    # Remove Docker Compose files
    rm -f docker-compose.layer2.yml 2>/dev/null && log_success "Removed docker-compose.layer2.yml" || log_info "docker-compose.layer2.yml not found"

    # Remove any temporary configuration files
    find . -name "*.tmp" -o -name "*.temp" | xargs rm -f 2>/dev/null || true

    log_success "Configuration cleanup completed"
}

# Verify teardown completion
verify_teardown() {
    log_info "Verifying component teardown completion..."

    local issues_found=0

    # Check for remaining test containers
    local remaining_containers=$(docker ps -a --format "table {{.Names}}" | grep -E "^test-" | wc -l)
    if [ "$remaining_containers" -gt 0 ]; then
        log_warning "Found $remaining_containers remaining test containers:"
        docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep -E "^test-" || true
        issues_found=$((issues_found + 1))
    fi

    # Check for remaining images in registry (informational)
    if docker images --format "table {{.Repository}}" | grep -q "$REGISTRY_HOST/datakits" 2>/dev/null; then
        if [ "$PRESERVE_IMAGES" = true ] || [ "$FULL_CLEAN" != true ]; then
            log_info "Datakit images preserved in registry (as requested)"
        fi
        docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep "$REGISTRY_HOST/datakits" || true
    fi

    if [ $issues_found -eq 0 ]; then
        log_success "Teardown verification passed - Layer 2 components are clean"
    else
        log_warning "Teardown verification found $issues_found potential issues"
        echo "You may need to manually address the warnings above"
    fi
}

# Show rebuild instructions
show_rebuild_instructions() {
    echo
    echo -e "${GREEN}🎉 Layer 2 Teardown Complete${NC}"
    echo
    echo "Component testing environment removed:"
    echo "✅ Test containers stopped and removed"
    echo "✅ Images cleaned (based on your selection)"
    echo "✅ Networks cleaned up"
    echo "✅ DBT artifacts removed"
    echo "✅ Development configuration files cleaned"
    echo
    echo -e "${BLUE}🔄 To Rebuild Layer 2:${NC}"
    echo
    echo "Build components:"
    echo "  ./scripts/build-layer2-components.sh"
    echo
    echo "Test components:"
    echo "  ./scripts/test-layer2-components.sh"
    echo
    echo "Build with optional components (like Spark):"
    echo "  ./scripts/build-layer2-components.sh --build-optional"
    echo
    echo -e "${YELLOW}💡 Note: Layer 1 (platform foundation) is preserved${NC}"
    echo "Your Traefik and registry services continue running normally."
    echo
    echo -e "${BLUE}🚀 Next Steps:${NC}"
    echo "After validating components, move to Layer 3 for pipeline orchestration."
    echo
}

# Parse command line arguments
FULL_CLEAN=false
PRESERVE_IMAGES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full-clean)
            FULL_CLEAN=true
            shift
            ;;
        --preserve-images)
            PRESERVE_IMAGES=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --full-clean      Remove everything including component images"
            echo "  --preserve-images Keep component images for fast rebuild"
            echo "  -h, --help       Show this help"
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

    # Confirm teardown
    echo -e "${YELLOW}⚠️  This will remove Layer 2 data processing components.${NC}"
    echo "Layer 1 (platform foundation) will be preserved."
    echo
    read -p "Continue with Layer 2 teardown? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Layer 2 teardown cancelled"
        exit 0
    fi

    # Override interactive choices if flags provided
    if [ "$FULL_CLEAN" = true ]; then
        log_info "Full clean mode - removing all test volumes and images"
    elif [ "$PRESERVE_IMAGES" = true ]; then
        log_info "Preserve images mode - keeping component images for fast rebuild"
    fi

    stop_containers
    cleanup_networks

    if [ "$FULL_CLEAN" = true ]; then
        # Non-interactive full clean
        log_warning "Full clean: removing all test volumes and images..."
        docker volume ls -q | grep -E "(test|temp|tmp)" | xargs docker volume rm 2>/dev/null || true
        docker images --format "table {{.Repository}}:{{.Tag}} {{.ID}}" | grep "$REGISTRY_HOST/datakits" | awk '{print $2}' | xargs docker rmi -f 2>/dev/null || true
    elif [ "$PRESERVE_IMAGES" = true ]; then
        # Skip interactive volume and image cleanup
        log_info "Preserving images and test volumes for fast rebuild"
    else
        # Interactive mode
        cleanup_volumes
        cleanup_images
    fi

    cleanup_dbt_artifacts
    cleanup_config_files
    verify_teardown
    show_rebuild_instructions
}

# Handle script errors
trap 'log_error "Layer 2 teardown failed at line $LINENO. Exit code: $?"' ERR

# Run main function
main "$@"
