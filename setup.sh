#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Docker is installed
check_docker_installed() {
    if ! command -v docker &> /dev/null; then
        echo ""
        echo -e "${RED}✗ Error: Docker is not installed${NC}"
        echo -e "${YELLOW}Please install Docker from: https://docs.docker.com/get-docker/${NC}"
        echo ""
        exit 1
    fi
}

# Check if Docker Compose is installed
check_docker_compose_installed() {
    if ! command -v docker compose &> /dev/null && ! command -v docker-compose &> /dev/null; then
        echo ""
        echo -e "${RED}✗ Error: Docker Compose is not installed${NC}"
        echo -e "${YELLOW}Please install Docker Compose from: https://docs.docker.com/compose/install/${NC}"
        echo ""
        exit 1
    fi
}

# Check if Docker daemon is running
check_docker_running() {
    if ! docker info &> /dev/null; then
        echo ""
        echo -e "${RED}✗ Error: Docker daemon is not running${NC}"
        echo -e "${YELLOW}Please start Docker and try again${NC}"
        echo ""
        exit 1
    fi
}

# Progress bar function
show_progress() {
    local current=$1
    local total=$2
    local label=$3
    local width=50
    
    local percent=$((current * 100 / total))
    local filled=$((percent * width / 100))
    
    printf "\r${BLUE}[%-${width}s]${NC} ${label} (%d%%)" "$(printf '#%.0s' $(seq 1 $filled))" "$percent"
    
    if [ $current -eq $total ]; then
        echo ""
    fi
}

# Generate random password function
generate_random_password() {
    # Generate a random 32-character password
    openssl rand -base64 32 | tr -d '=' | cut -c1-32
}

# Check dependencies before starting
echo -e "${BLUE}Checking prerequisites...${NC}"
check_docker_installed
check_docker_compose_installed
check_docker_running
echo -e "${GREEN}✓ All prerequisites met${NC}"
echo ""

# Clear previous .env if exists
if [ -f .env ]; then
    echo -e "${YELLOW}Found existing .env file${NC}"
    echo ""
    echo "What would you like to do?"
    echo "  1) Remove and create new .env (recommended)"
    echo "  2) Append to existing .env"
    echo "  3) Skip .env configuration and start services"
    echo "  4) Exit"
    echo ""
    echo -ne "Select option [${YELLOW}1${NC}]: "
    read env_option
    env_option="${env_option:-1}"
    
    case "$env_option" in
        1)
            rm .env
            echo -e "${GREEN}✓ Cleared existing .env file${NC}"
            ;;
        2)
            echo -e "${GREEN}✓ Will append to existing .env file${NC}"
            ;;
        3)
            echo -e "${GREEN}✓ Skipping .env configuration${NC}"
            skip_env_config=true
            ;;
        4)
            echo -e "${YELLOW}Exiting setup${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}✗ Invalid option${NC}"
            exit 1
            ;;
    esac
    echo ""
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Statement Project Initialization${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Skip env configuration if user selected option 3
if [ "$skip_env_config" = true ]; then
    echo -e "${YELLOW}Skipping environment variable configuration${NC}"
    echo ""
else
    echo -e "${YELLOW}Please configure environment variables:${NC}"
    echo ""

    # Check if .env.example exists
    if [ ! -f .env.example ]; then
        echo -e "${RED}✗ Error: .env.example file not found${NC}"
        exit 1
    fi

    # Parse .env.example file to get variables and their default values
    declare -a vars=()
    count=0

    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        
        # Extract variable name and value
        if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
            var_name="${BASH_REMATCH[1]}"
            default_value="${BASH_REMATCH[2]}"
            vars+=("${var_name}|${default_value}")
            count=$((count + 1))
        fi
    done < .env.example

    total_vars=$count

    # Process each variable
    for var_pair in "${vars[@]}"; do
        count=$((count + 1))
        
        # Split by pipe delimiter (|)
        var_name="${var_pair%|*}"
        default_value="${var_pair#*|}"
        
        # Skip values that end with "..." (truncated values)
        if [[ "$default_value" =~ \.\.\.$  ]]; then
            default_value=""
        fi
        
        # Display prompt
        if [ -z "$default_value" ]; then
            echo -e "${GREEN}${count}. ${var_name}${NC}"
            echo -ne "   Value: "
            read user_value
            
            # Generate random password for MONGO_PASSWORD and ELASTIC_PASSWORD if empty
            if [ -z "$user_value" ]; then
                if [ "$var_name" = "MONGO_PASSWORD" ] || [ "$var_name" = "ELASTIC_PASSWORD" ]; then
                    user_value=$(generate_random_password)
                    echo -e "   ${YELLOW}[Generated]${NC} ${user_value}"
                fi
            fi
        else
            echo -e "${GREEN}${count}. ${var_name}${NC}"
            echo -ne "   Value [${YELLOW}${default_value}${NC}]: "
            read user_value
            user_value="${user_value:-$default_value}"
        fi
        
        # Convert relative paths to absolute paths for DATA_PATH
        if [ "$var_name" = "DATA_PATH" ]; then
            if [[ "$user_value" != /* ]]; then
                # Path is relative, convert to absolute
                user_value="$(cd "$(dirname "$user_value")" && pwd)/$(basename "$user_value")"
            fi
            # Create the directory if it doesn't exist
            mkdir -p "$user_value"
        fi
        
        # Write to .env file
        echo "${var_name}=${user_value}" >> .env
        echo ""
    done

    echo ""
    echo -e "${GREEN}✓ Created .env file successfully${NC}"
    echo ""
fi

# Run docker compose init
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Running Docker Initialization${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Count steps for progress
total_steps=2
current_step=1

show_progress "$current_step" "$total_steps" "Initializing Docker containers"
if ! docker compose run --rm init; then
    echo ""
    echo -e "${RED}✗ Error: Docker initialization failed${NC}"
    echo -e "${YELLOW}Please check your Docker setup and try again${NC}"
    exit 1
fi
current_step=$((current_step + 1))

show_progress "$current_step" "$total_steps" "Starting services"

# Get list of services from docker-compose
services=$(docker compose config --services)
service_array=($services)
total_services=${#service_array[@]}

# Track service status
declare -A service_status

# Initialize all services as pending
for service in "${service_array[@]}"; do
    service_status[$service]="pending"
done

# Run docker compose up and monitor progress
docker compose up -d > /tmp/docker_compose.log 2>&1 &
compose_pid=$!

# Monitor service startup
last_updated=0
last_log_update=0
startup_timeout=300
start_time=$(date +%s)
log_line_count=0
max_log_lines=10

echo ""

while kill -0 $compose_pid 2>/dev/null; do
    ready_count=0
    
    # Check each service status
    for service in "${service_array[@]}"; do
        # Check if container is running
        if docker compose ps "$service" 2>/dev/null | grep -q "Up"; then
            service_status[$service]="running"
        fi
    done
    
    # Count running services
    for service in "${service_array[@]}"; do
        if [ "${service_status[$service]}" = "running" ]; then
            ready_count=$((ready_count + 1))
        fi
    done
    
    # Print/update log lines (every 2 seconds)
    current_time=$(date +%s)
    if [ $((current_time - last_log_update)) -ge 2 ]; then
        # Get total lines in log
        current_line_count=$(wc -l < /tmp/docker_compose.log 2>/dev/null || echo 0)
        
        if [ $current_line_count -gt 0 ]; then
            # Get last 6 lines
            tail_start=$((current_line_count - max_log_lines + 1))
            if [ $tail_start -lt 1 ]; then
                tail_start=1
            fi
            
            # Clear previous log display (move up and clear)
            for i in $(seq 1 $max_log_lines); do
                echo -ne "\033[A\033[K"
            done
            
            # Print the last 6 lines
            tail -n +$tail_start /tmp/docker_compose.log | while read -r log_line; do
                echo -e "${YELLOW}  │${NC} $log_line"
            done
        fi
        
        last_log_update=$current_time
    fi
    
    # Calculate elapsed time for progress
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    
    # Calculate progress: services ready + elapsed time factor
    progress=$((ready_count * 100 / total_services))
    # Add time-based progress (max 20% from time)
    time_progress=$((elapsed * 20 / startup_timeout))
    if [ $time_progress -gt 20 ]; then
        time_progress=20
    fi
    total_progress=$((progress + time_progress))
    if [ $total_progress -gt 99 ]; then
        total_progress=99
    fi
    
    # Update progress bar
    current_tick=$(date +%s%N | cut -b1-10)
    if [ $((current_tick - last_updated)) -ge 1 ]; then
        width=40
        filled=$((total_progress * width / 100))
        
        printf "\r${BLUE}[%-${width}s]${NC} %d%% | %d/%d services ready" \
            "$(printf '#%.0s' $(seq 1 $filled))" \
            "$total_progress" "$ready_count" "$total_services"
        
        last_updated=$current_tick
    fi
    
    # Check timeout
    if [ $elapsed -gt $startup_timeout ]; then
        echo ""
        echo -e "${YELLOW}⚠ Service startup timeout, stopping...${NC}"
        docker compose down > /dev/null 2>&1
        break
    fi
    
    sleep 0.3
done

# Final progress bar at 100%
printf "\r${BLUE}[%-40s]${NC} %d%% | %d/%d services ready\n" \
    "$(printf '#%.0s' $(seq 1 40))" \
    "100" "$total_services" "$total_services"

# Wait for compose to complete
wait $compose_pid
compose_exit=$?

if [ $compose_exit -ne 0 ]; then
    echo ""
    echo -e "${RED}✗ Error: Failed to start Docker services${NC}"
    echo -e "${YELLOW}Docker logs:${NC}"
    cat /tmp/docker_compose.log
    exit 1
fi

echo ""
echo -e "${GREEN}✓ All services started successfully${NC}"

echo ""
echo -e "${GREEN}✓ Docker services started successfully${NC}"
echo ""

# Display service information
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Services Information${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Frontend${NC}        : ${BLUE}http://localhost:3000${NC}"
echo -e "${GREEN}Backend API${NC}     : ${BLUE}http://localhost:8765${NC}"
echo -e "${GREEN}Elasticsearch${NC}   : ${BLUE}http://localhost:9200${NC}"
echo -e "${GREEN}MongoDB${NC}         : ${BLUE}mongodb:27017${NC}"
echo ""
echo -e "${YELLOW}Note: It may take a few moments for all services to be fully ready.${NC}"
echo -e "${YELLOW}Use 'docker compose logs -f' to view service logs.${NC}"
echo ""
echo -e "${GREEN}✓ Initialization complete!${NC}"
echo ""
