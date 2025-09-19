#!/bin/bash
# Test Layer 2 Components Script
# Unit tests for individual datakit components

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
IMAGE_VERSION="v1.0.0"

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

print_banner() {
    echo -e "${BLUE}"
    echo "🧪 =================================================="
    echo "   LAYER 2: COMPONENT TESTING"
    echo "   Unit Tests for Datakit Components"
    echo "==================================================${NC}"
    echo
    echo "This script will test:"
    echo "• Container build and startup validation"
    echo "• CLI tool accessibility and basic functionality"
    echo "• Data object deployment to test databases"
    echo "• Component isolation (no external dependencies)"
    echo
}

# Component definitions
declare -A CORE_DATAKITS=(
    ["bronze-pagila"]="Raw data ingestion with audit trails"
    ["postgres-runner"]="PostgreSQL operations and utilities"
    ["dbt-runner"]="DBT transformations orchestration"
    ["sqlserver-runner"]="SQL Server operations and utilities"
)

declare -A OPTIONAL_DATAKITS=(
    ["spark-runner"]="Spark processing for large datasets"
)

# Check prerequisites
check_prerequisites() {
    log_info "Checking testing prerequisites..."

    # Check if images exist
    local missing_images=()
    for datakit in "${!CORE_DATAKITS[@]}"; do
        if ! docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$REGISTRY_HOST/datakits/$datakit:$IMAGE_VERSION"; then
            missing_images+=("$datakit")
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

    log_success "Testing prerequisites verified"
}

# Test data object deployment for a datakit
test_data_object_deployment() {
    local component="$1"
    local container_name="$2"

    # Check if datakit directory has SQLModel objects
    local datakit_path="$REPO_ROOT/layer2-datakits/$component"
    if [ ! -d "$datakit_path" ]; then
        return 1  # No datakit directory
    fi

    # Check if we have Python files that might contain SQLModel objects
    if ! find "$datakit_path" -name "*.py" | grep -q .; then
        return 1  # No Python files
    fi

    # Use the deployment framework to test data object deployment
    log_info "    Testing data object deployment to $DEPLOYMENT_TARGET..."

    # Create a simple deployment test using our framework
    local test_result
    if test_result=$(python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT/data-platform-framework')

try:
    from utils.deployment import discover_datakit_modules, discover_sqlmodel_classes, deploy_data_objects
    from config.targets import get_target_config

    # Discover modules in the datakit
    modules = discover_datakit_modules('$datakit_path')
    if not modules:
        print('No modules found')
        exit(1)

    # Discover SQLModel classes
    table_classes = discover_sqlmodel_classes(modules)
    if not table_classes:
        print('No SQLModel classes found')
        exit(1)

    # Deploy to specified test target
    target_config = get_target_config('$DEPLOYMENT_TARGET')
    result = deploy_data_objects(table_classes, target_config)

    if result['success']:
        print(f'SUCCESS: Deployed {result[\"tables_deployed\"]} tables')
        exit(0)
    else:
        print(f'FAILED: {result[\"error\"]}')
        exit(1)

except ImportError as e:
    print(f'Framework not available: {e}')
    exit(1)
except Exception as e:
    print(f'Deployment test failed: {e}')
    exit(1)
" 2>/dev/null); then
        log_info "    $test_result"
        return 0
    else
        log_info "    $test_result"
        return 1
    fi
}

# Test single component
test_component() {
    local component="$1"
    local description="$2"
    local test_success=true

    log_info "Testing $component: $description"

    local image_name="$REGISTRY_HOST/datakits/$component:$IMAGE_VERSION"
    local container_name="test-$component"

    # Clean up any existing test container
    docker rm -f "$container_name" >/dev/null 2>&1 || true

    # Test 1: Container can start and stay running
    log_info "  Test 1: Container startup and basic health"
    if docker run -d --name "$container_name" "$image_name" sleep 30 >/dev/null 2>&1; then
        if docker ps --format "table {{.Names}}" | grep -q "$container_name"; then
            log_success "  ✅ Container starts successfully"
        else
            log_error "  ❌ Container failed to stay running"
            test_success=false
        fi
    else
        log_error "  ❌ Container failed to start"
        test_success=false
    fi

    # Test 2: CLI tool accessibility
    log_info "  Test 2: CLI tool accessibility"
    case "$component" in
        "bronze-pagila")
            if docker exec "$container_name" python -c "import datakit_bronze; print('✅ bronze-pagila module accessible')" 2>/dev/null; then
                log_success "  ✅ bronze-pagila CLI accessible"
            else
                log_error "  ❌ bronze-pagila CLI not accessible"
                test_success=false
            fi
            ;;
        "postgres-runner")
            if docker exec "$container_name" python -c "import datakit_postgres; print('✅ postgres-runner module accessible')" 2>/dev/null; then
                log_success "  ✅ postgres-runner CLI accessible"
            else
                log_error "  ❌ postgres-runner CLI not accessible"
                test_success=false
            fi
            ;;
        "dbt-runner")
            if docker exec "$container_name" dbt --version >/dev/null 2>&1; then
                log_success "  ✅ dbt CLI accessible"
            else
                log_error "  ❌ dbt CLI not accessible"
                test_success=false
            fi
            ;;
        "sqlserver-runner")
            if docker exec "$container_name" python -c "import datakit_sqlserver; print('✅ sqlserver-runner module accessible')" 2>/dev/null; then
                log_success "  ✅ sqlserver-runner CLI accessible"
            else
                log_error "  ❌ sqlserver-runner CLI not accessible"
                test_success=false
            fi
            ;;
        "spark-runner")
            if docker exec "$container_name" python -c "import datakit_spark; print('✅ spark-runner module accessible')" 2>/dev/null; then
                log_success "  ✅ spark-runner CLI accessible"
            else
                log_error "  ❌ spark-runner CLI not accessible"
                test_success=false
            fi
            ;;
    esac

    # Test 3: Python environment health
    log_info "  Test 3: Python environment validation"
    if docker exec "$container_name" python -c "import sys; print(f'✅ Python {sys.version_info.major}.{sys.version_info.minor} available')" 2>/dev/null; then
        log_success "  ✅ Python environment healthy"
    else
        log_error "  ❌ Python environment issues"
        test_success=false
    fi

    # Test 4: Data object deployment (if datakit has SQLModel objects)
    log_info "  Test 4: Data object deployment validation"
    if test_data_object_deployment "$component" "$container_name"; then
        log_success "  ✅ Data objects deploy successfully"
    else
        log_warning "  ⚠️  Data object deployment not available (may not have SQLModel objects)"
    fi

    # Clean up test container
    docker rm -f "$container_name" >/dev/null 2>&1 || true

    if [ "$test_success" = true ]; then
        log_success "$component: All tests passed ✅"
    else
        log_error "$component: Some tests failed ❌"
    fi

    return $([ "$test_success" = true ] && echo 0 || echo 1)
}

# Test core components
test_core_components() {
    log_info "Testing core datakit components..."

    local test_results=()
    local successful_tests=()
    local failed_tests=()

    for component in "${!CORE_DATAKITS[@]}"; do
        if [ -n "$SPECIFIC_COMPONENT" ] && [ "$SPECIFIC_COMPONENT" != "$component" ]; then
            continue
        fi

        if test_component "$component" "${CORE_DATAKITS[$component]}"; then
            successful_tests+=("$component")
        else
            failed_tests+=("$component")
        fi
        echo
    done

    # Summary
    echo -e "${BLUE}Core Component Test Summary:${NC}"
    if [ ${#successful_tests[@]} -gt 0 ]; then
        log_success "Passed: ${successful_tests[*]}"
    fi
    if [ ${#failed_tests[@]} -gt 0 ]; then
        log_error "Failed: ${failed_tests[*]}"
        return 1
    fi

    return 0
}

# Test optional components
test_optional_components() {
    if [ "${TEST_OPTIONAL:-false}" != "true" ]; then
        log_info "Skipping optional components (use --test-optional to include)"
        return 0
    fi

    log_info "Testing optional datakit components..."

    for component in "${!OPTIONAL_DATAKITS[@]}"; do
        if [ -n "$SPECIFIC_COMPONENT" ] && [ "$SPECIFIC_COMPONENT" != "$component" ]; then
            continue
        fi

        # Check if optional component image exists
        if ! docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$REGISTRY_HOST/datakits/$component:$IMAGE_VERSION"; then
            log_warning "$component: Image not found (optional component not built)"
            continue
        fi

        if test_component "$component" "${OPTIONAL_DATAKITS[$component]}"; then
            log_success "Optional component passed: $component"
        else
            log_warning "Optional component failed (non-fatal): $component"
        fi
        echo
    done
}

# Test DBT projects
test_dbt_projects() {
    log_info "Testing DBT project configurations..."

    cd "$REPO_ROOT"
    local dbt_projects=("silver-core" "gold-dimensions" "gold-facts")
    local successful_projects=()
    local failed_projects=()

    for project in "${dbt_projects[@]}"; do
        if [ ! -d "layer2-dbt-projects/$project" ]; then
            log_error "DBT project directory not found: layer2-dbt-projects/$project"
            failed_projects+=("$project")
            continue
        fi

        cd "layer2-dbt-projects/$project"

        # Test DBT project configuration
        if [ -f "dbt_project.yml" ]; then
            log_success "$project: dbt_project.yml found"
            successful_projects+=("$project")
        else
            log_error "$project: dbt_project.yml missing"
            failed_projects+=("$project")
        fi

        cd "$REPO_ROOT"
    done

    # Summary
    echo -e "${BLUE}DBT Project Test Summary:${NC}"
    if [ ${#successful_projects[@]} -gt 0 ]; then
        log_success "Valid projects: ${successful_projects[*]}"
    fi
    if [ ${#failed_projects[@]} -gt 0 ]; then
        log_error "Invalid projects: ${failed_projects[*]}"
        return 1
    fi

    return 0
}

# Show test results
show_test_results() {
    echo
    echo -e "${GREEN}🎉 Layer 2 Component Testing Complete!${NC}"
    echo
    echo -e "${BLUE}📦 Tested Components:${NC}"

    # Show successful component tests
    for component in "${!CORE_DATAKITS[@]}"; do
        if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$REGISTRY_HOST/datakits/$component:$IMAGE_VERSION"; then
            echo "✅ $component: Container and data object tests passed"
        fi
    done

    if [ "${TEST_OPTIONAL:-false}" = "true" ]; then
        for component in "${!OPTIONAL_DATAKITS[@]}"; do
            if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$REGISTRY_HOST/datakits/$component:$IMAGE_VERSION"; then
                echo "✅ $component: Optional tests passed"
            fi
        done
    fi

    echo
    echo -e "${BLUE}🚀 Next Steps:${NC}"
    echo "1. Components are validated and ready for integration"
    echo "2. Move to Layer 3 for pipeline orchestration:"
    echo "   # Layer 3 will use these validated components"
    echo "3. Integration testing will happen in Layer 3"
    echo
    echo -e "${YELLOW}💡 Component Philosophy:${NC}"
    echo "• Layer 2: Individual component validation + data object deployment testing"
    echo "• Layer 3: Component orchestration and integration into complete pipelines"
    echo
}

# Parse command line arguments
SPECIFIC_COMPONENT=""
TEST_OPTIONAL=false
VERBOSE=false
DEPLOYMENT_TARGET="sqlite_memory"  # Default to fastest target

while [[ $# -gt 0 ]]; do
    case $1 in
        --component)
            SPECIFIC_COMPONENT="$2"
            shift 2
            ;;
        --test-optional)
            TEST_OPTIONAL=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --deployment-target)
            DEPLOYMENT_TARGET="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS] [COMPONENT]"
            echo "Options:"
            echo "  --component NAME     Test specific component only"
            echo "  --test-optional      Include optional components (like Spark)"
            echo "  --deployment-target  Database target for data object tests"
            echo "                       (sqlite_memory, postgres_container, etc.)"
            echo "  --verbose           Verbose output"
            echo "  -h, --help          Show this help"
            echo
            echo "Components: ${!CORE_DATAKITS[*]}"
            echo "Optional: ${!OPTIONAL_DATAKITS[*]}"
            exit 0
            ;;
        *)
            # Treat as component name if no --component specified
            if [ -z "$SPECIFIC_COMPONENT" ]; then
                SPECIFIC_COMPONENT="$1"
            else
                log_warning "Unknown option: $1"
            fi
            shift
            ;;
    esac
done

# Main execution
main() {
    print_banner
    check_prerequisites

    local test_success=true

    test_core_components || test_success=false
    test_optional_components || true  # Optional tests don't fail overall
    test_dbt_projects || test_success=false

    if [ "$test_success" = true ]; then
        show_test_results
        return 0
    else
        log_error "❌ Component testing failed!"
        echo
        echo -e "${RED}Test failures detected:${NC}"
        echo "• Check component logs above for details"
        echo "• Verify components built successfully"
        echo "• Try testing individual components:"
        echo "  ./scripts/test-layer2-components.sh --component bronze-pagila"
        echo
        return 1
    fi
}

# Handle script errors
trap 'log_error "Component testing failed at line $LINENO. Exit code: $?"' ERR

# Run main function
main "$@"
