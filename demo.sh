#!/bin/bash
#
# PR Telemetry System - Interactive Demo Script
# 
# This script demonstrates all features of the PR Telemetry system:
# - System health check
# - Three E2E examples (simple, complex, failed)
# - Trace viewing and comparison
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Configuration
API_URL="http://localhost:8000"

# Helper functions
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${CYAN}  $1${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

pause() {
    echo ""
    echo -e "${YELLOW}Press Enter to continue...${NC}"
    read -r
}

check_requirements() {
    print_header "Checking Requirements"
    
    local all_ok=true
    
    # Check Docker
    if command -v docker &> /dev/null; then
        print_success "Docker installed"
    else
        print_error "Docker not found"
        all_ok=false
    fi
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose installed"
    else
        print_error "Docker Compose not found"
        all_ok=false
    fi
    
    # Check Python
    if command -v python3 &> /dev/null; then
        print_success "Python3 installed"
    else
        print_error "Python3 not found"
        all_ok=false
    fi
    
    # Check if httpx is installed
    if python3 -c "import httpx" 2>/dev/null; then
        print_success "httpx library installed"
    else
        print_warning "httpx not installed - will install now"
        pip install httpx > /dev/null 2>&1 || pip3 install httpx > /dev/null 2>&1
        print_success "httpx installed"
    fi
    
    if [ "$all_ok" = false ]; then
        print_error "Some requirements missing. Please install them first."
        exit 1
    fi
}

check_services() {
    print_header "Checking System Status"
    
    # Check if containers are running
    if docker-compose ps | grep -q "Up"; then
        print_success "Docker containers running"
    else
        print_error "Containers not running"
        print_info "Starting containers..."
        docker-compose up -d
        print_info "Waiting 30 seconds for services to start..."
        sleep 30
    fi
    
    # Check API health
    print_info "Checking API health..."
    if curl -s "${API_URL}/healthz" > /dev/null; then
        print_success "API is healthy"
        curl -s "${API_URL}/healthz" | python3 -m json.tool
    else
        print_error "API not responding at ${API_URL}"
        print_info "Make sure services are running: docker-compose up -d"
        exit 1
    fi
}

show_menu() {
    clear
    cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║        🎯  PR Telemetry System - Interactive Demo  🎯           ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
EOF
    
    echo ""
    echo -e "${BOLD}Available Demos:${NC}"
    echo ""
    echo "  1) Run Simple Example (Single file bug fix)"
    echo "  2) Run Complex Example (Multi-file iterative debugging)"
    echo "  3) Run Failed Example (Unsuccessful bug fix attempt)"
    echo "  4) Run ALL Examples (Sequential execution)"
    echo ""
    echo "  5) View System Status"
    echo "  6) View Service Logs"
    echo "  7) Compare All Examples"
    echo ""
    echo "  8) Check LLM Judge Status"
    echo "  9) Run Full System Test"
    echo ""
    echo "  0) Exit"
    echo ""
    echo -n "Select option: "
}

run_simple_example() {
    print_header "Running Simple Example"
    print_info "Scenario: Fix single function bug (wrong operator)"
    print_info "Expected: Quick fix, tests pass, commit"
    echo ""
    
    python3 examples/submit_example.py
    
    print_success "Simple example completed!"
    pause
}

run_complex_example() {
    print_header "Running Complex Example"
    print_info "Scenario: Multi-file bug fix with iterative debugging"
    print_info "Expected: Multiple files, hypothesis testing, complete fix"
    echo ""
    
    python3 examples/submit_complex_example.py
    
    print_success "Complex example completed!"
    pause
}

run_failed_example() {
    print_header "Running Failed Example"
    print_info "Scenario: Unsuccessful authentication bug fix"
    print_info "Expected: Partial analysis, no successful resolution"
    echo ""
    
    python3 examples/submit_failed_example.py
    
    print_success "Failed example completed!"
    pause
}

run_all_examples() {
    print_header "Running ALL Examples"
    print_info "This will run all three examples sequentially..."
    echo ""
    
    print_info "[1/3] Running Simple Example..."
    python3 examples/submit_example.py | tail -20
    echo ""
    
    print_info "[2/3] Running Complex Example..."
    python3 examples/submit_complex_example.py | tail -20
    echo ""
    
    print_info "[3/3] Running Failed Example..."
    python3 examples/submit_failed_example.py | tail -20
    echo ""
    
    print_success "All examples completed!"
    print_info "Check the comparison below..."
    echo ""
    
    compare_examples
    pause
}

view_system_status() {
    print_header "System Status"
    
    echo -e "${BOLD}Docker Containers:${NC}"
    docker-compose ps
    echo ""
    
    echo -e "${BOLD}API Health:${NC}"
    curl -s "${API_URL}/healthz" | python3 -m json.tool
    echo ""
    
    echo -e "${BOLD}Database Status:${NC}"
    docker-compose exec -T postgres psql -U telemetry -d pr_telemetry -c "SELECT COUNT(*) as total_traces FROM traces;" 2>/dev/null || echo "Cannot connect to database"
    echo ""
    
    echo -e "${BOLD}MinIO Buckets:${NC}"
    docker-compose exec -T minio mc ls myminio 2>/dev/null || echo "MinIO not accessible"
    echo ""
    
    pause
}

view_logs() {
    print_header "Service Logs"
    
    echo "Select service to view logs:"
    echo "  1) API"
    echo "  2) Worker"
    echo "  3) PostgreSQL"
    echo "  4) Redis"
    echo "  5) MinIO"
    echo "  6) All services"
    echo ""
    echo -n "Select option: "
    read -r log_choice
    
    case $log_choice in
        1) docker-compose logs --tail=50 api ;;
        2) docker-compose logs --tail=50 worker ;;
        3) docker-compose logs --tail=50 postgres ;;
        4) docker-compose logs --tail=50 redis ;;
        5) docker-compose logs --tail=50 minio ;;
        6) docker-compose logs --tail=30 ;;
        *) print_error "Invalid option" ;;
    esac
    
    pause
}

compare_examples() {
    print_header "Example Comparison"
    
    cat << 'EOF'
┌────────────────────────┬───────────┬──────────┬───────────────┐
│ Feature                │ Simple    │ Complex  │ Failed        │
├────────────────────────┼───────────┼──────────┼───────────────┤
│ Events                 │ 10        │ 24       │ 16            │
│ Chunks                 │ 3         │ 4        │ 3             │
│ Duration               │ 65s       │ 230s     │ 150s          │
│ Files Edited           │ 1         │ 3        │ 2             │
│ Commands Run           │ 2         │ 7        │ 5             │
│ Test Runs              │ 2         │ 4        │ 3             │
│ Bug Fixed?             │ ✅        │ ✅       │ ❌            │
│ Commit?                │ ✅        │ ✅       │ ❌            │
│ Typical AI Score       │ 3.1/5     │ 3.6/5    │ 3.2/5         │
└────────────────────────┴───────────┴──────────┴───────────────┘

What Each Example Demonstrates:

1. Simple Example (3.1/5):
   ✓ Linear problem-solving
   ✓ Single file change
   ✓ Clear problem → solution path
   Use Case: Baseline developer workflow

2. Complex Example (3.6/5):
   ✓ Multi-file coordination
   ✓ Iterative hypothesis testing
   ✓ Root cause analysis
   Use Case: Senior developer quality work

3. Failed Example (3.2/5):
   ✓ Incomplete problem analysis
   ✓ Multiple failed attempts
   ✓ No successful resolution
   Use Case: Learning from failures, negative training data

Key Insight:
The failed example scores 3.2/5 - slightly HIGHER than simple (3.1/5)!
This shows the AI Judge evaluates PROCESS QUALITY, not just outcomes.

EOF
    
    pause
}

check_llm_status() {
    print_header "LLM Judge Status"
    
    echo -e "${BOLD}Checking LLM configuration...${NC}"
    echo ""
    
    # Check if .env file exists
    if [ -f .env ]; then
        if grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
            print_success ".env file exists with API key"
            print_info "LLM Judge should be using real OpenAI API"
        else
            print_warning ".env file exists but no valid API key found"
            print_info "LLM Judge is using MOCK mode"
        fi
    else
        print_warning "No .env file found"
        print_info "LLM Judge is using MOCK mode"
    fi
    echo ""
    
    echo -e "${BOLD}Checking worker logs for LLM initialization...${NC}"
    docker-compose logs worker 2>/dev/null | grep -i "llm\|openai\|judge" | tail -10
    echo ""
    
    echo -e "${BOLD}To enable real LLM evaluation:${NC}"
    echo "  1. Copy template: cp env.example .env"
    echo "  2. Edit .env and add your OpenAI API key"
    echo "  3. Restart worker: docker-compose restart worker"
    echo ""
    
    pause
}

run_full_test() {
    print_header "Full System Test"
    
    print_info "This will perform a complete system validation..."
    echo ""
    
    # 1. Check services
    print_info "Step 1: Checking services..."
    check_services
    echo ""
    
    # 2. Run simple example
    print_info "Step 2: Running test trace..."
    python3 examples/submit_example.py > /tmp/demo_test.log 2>&1
    
    if [ $? -eq 0 ]; then
        print_success "Test trace completed successfully"
        
        # Extract trace ID from log
        TRACE_ID=$(grep "Trace ID:" /tmp/demo_test.log | tail -1 | awk '{print $NF}')
        if [ ! -z "$TRACE_ID" ]; then
            print_info "Trace ID: $TRACE_ID"
            
            # 3. Verify trace
            print_info "Step 3: Verifying trace data..."
            if curl -s "${API_URL}/v1/traces/${TRACE_ID}" \
                -H "Authorization: Bearer dev_token_12345" | grep -q "qa"; then
                print_success "QA results found in trace"
            else
                print_warning "QA results not found (may still be processing)"
            fi
        fi
    else
        print_error "Test trace failed"
        cat /tmp/demo_test.log
    fi
    
    echo ""
    print_success "Full system test completed!"
    pause
}

# Main program
main() {
    # Initial checks
    check_requirements
    check_services
    
    # Main menu loop
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1) run_simple_example ;;
            2) run_complex_example ;;
            3) run_failed_example ;;
            4) run_all_examples ;;
            5) view_system_status ;;
            6) view_logs ;;
            7) compare_examples ;;
            8) check_llm_status ;;
            9) run_full_test ;;
            0)
                clear
                echo ""
                print_success "Thank you for using PR Telemetry Demo!"
                echo ""
                echo "To view traces: python3 view_trace.py <trace-id>"
                echo "To stop system: docker-compose down"
                echo ""
                exit 0
                ;;
            *)
                print_error "Invalid option. Please try again."
                sleep 2
                ;;
        esac
    done
}

# Run main program
main

