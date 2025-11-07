#!/bin/bash
# EC2 Deployment Script for OpenPilot Detection System
# Compatible with Ubuntu and Amazon Linux 2
# Run this script on your EC2 instance

set -e  # Exit on any error

echo "========================================"
echo "OpenPilot Detection - EC2 Deployment"
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo -e "${RED}Cannot detect OS${NC}"
    exit 1
fi

echo -e "${YELLOW}Detected OS: $OS${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found. Installing Docker...${NC}"
    
    if [ "$OS" = "ubuntu" ]; then
        # Ubuntu installation
        echo -e "${YELLOW}Installing Docker on Ubuntu...${NC}"
        sudo apt-get update -y
        sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update -y
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER
        
    elif [ "$OS" = "amzn" ]; then
        # Amazon Linux installation
        echo -e "${YELLOW}Installing Docker on Amazon Linux...${NC}"
        sudo yum update -y
        sudo yum install -y docker
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -a -G docker $USER
    else
        echo -e "${RED}Unsupported OS: $OS${NC}"
        echo "This script supports Ubuntu and Amazon Linux 2"
        exit 1
    fi
    
    echo -e "${GREEN}Docker installed successfully${NC}"
    echo -e "${YELLOW}Please logout and login again, then re-run this script${NC}"
    exit 0
fi

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: docker-compose.yml not found in current directory${NC}"
    echo "Please upload docker-compose.yml and docker-compose.prod.yml first"
    exit 1
fi

# Check Docker Compose command (v1 vs v2)
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif docker-compose --version &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo -e "${RED}Docker Compose not found. Installing...${NC}"
    if [ "$OS" = "ubuntu" ]; then
        # Docker Compose plugin should be installed with Docker
        sudo apt-get install -y docker-compose-plugin
    elif [ "$OS" = "amzn" ]; then
        # Install Docker Compose v1 for Amazon Linux
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
    
    # Re-check
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif docker-compose --version &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        echo -e "${RED}Failed to install Docker Compose${NC}"
        exit 1
    fi
fi

echo -e "${YELLOW}Using: $COMPOSE_CMD${NC}"

# Pull latest image
echo -e "${YELLOW}Pulling latest image from Docker Hub...${NC}"
if [ -f "docker-compose.prod.yml" ]; then
    if ! $COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml pull 2>/dev/null; then
        echo -e "${YELLOW}⚠ Pull failed. This might be because:${NC}"
        echo -e "${YELLOW}  1. Repository is private (requires 'docker login')${NC}"
        echo -e "${YELLOW}  2. Image doesn't exist on Docker Hub${NC}"
        echo -e "${YELLOW}  3. Network issues${NC}"
        echo ""
        echo -e "${YELLOW}Checking if we need to build locally instead...${NC}"
        
        # Check if Dockerfile exists
        if [ -f "Dockerfile" ] && [ -f "requirements.txt" ] && [ -f "test_yolo_multi_mobile.py" ]; then
            echo -e "${GREEN}Found source files. Building image locally...${NC}"
            echo -e "${YELLOW}This will take 5-10 minutes on first build.${NC}"
            
            # Build locally
            if [ -f "docker-compose.override.yml" ]; then
                $COMPOSE_CMD up --build -d
            else
                # Create temporary override to build
                cat > docker-compose.override.yml << 'EOF'
services:
  multi-device-detection:
    build:
      context: .
      dockerfile: Dockerfile
EOF
                $COMPOSE_CMD up --build -d
                rm docker-compose.override.yml
            fi
            
            # Skip the rest of the pull/start logic
            BUILD_MODE=true
        else
            echo -e "${RED}✗ Cannot pull image and source files not found for building${NC}"
            echo ""
            echo -e "${YELLOW}Solutions:${NC}"
            echo "1. If repository is private, run: docker login"
            echo "2. Upload source files (Dockerfile, test_yolo_multi_mobile.py, requirements.txt)"
            echo "3. Make repository public at: https://hub.docker.com/repository/docker/kainosit/openpilot"
            exit 1
        fi
    fi
else
    if ! $COMPOSE_CMD pull 2>/dev/null; then
        echo -e "${RED}✗ Pull failed${NC}"
        echo "Try: docker login"
        exit 1
    fi
fi

# Only proceed with down/up if we didn't already build
if [ "$BUILD_MODE" != "true" ]; then
    # Stop existing container (if any)
    echo -e "${YELLOW}Stopping existing container (if any)...${NC}"
    $COMPOSE_CMD down 2>/dev/null || true

    # Start container
    echo -e "${YELLOW}Starting container...${NC}"
    if [ -f "docker-compose.prod.yml" ]; then
        $COMPOSE_CMD -f docker-compose.yml -f docker-compose.prod.yml up -d
    else
        $COMPOSE_CMD up -d
    fi
fi

# Wait for container to be healthy
echo -e "${YELLOW}Waiting for container to be healthy...${NC}"
sleep 10

# Check container status
CONTAINER_STATUS=$(docker inspect --format='{{.State.Status}}' openpilot-detection 2>/dev/null || echo "not found")

if [ "$CONTAINER_STATUS" == "running" ]; then
    echo -e "${GREEN}✓ Container is running${NC}"
    
    # Get EC2 instance public IP (works on EC2)
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")
    PRIVATE_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4 2>/dev/null || hostname -I | awk '{print $1}')
    
    # Check health
    sleep 30  # Wait for app to fully start
    if curl -s http://localhost:5000/status > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Health check passed${NC}"
    else
        echo -e "${YELLOW}⚠ Waiting for application to start (this may take up to 1 minute)...${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}========================================"
    echo "Deployment Successful!"
    echo "========================================${NC}"
    echo ""
    echo "Access URLs:"
    echo -e "  Public:  ${GREEN}http://$PUBLIC_IP:5000${NC}"
    echo -e "  Private: http://$PRIVATE_IP:5000"
    echo ""
    echo "Useful commands:"
    echo "  View logs:    docker logs -f openpilot-detection"
    echo "  Check status: docker ps"
    echo "  Restart:      docker restart openpilot-detection"
    echo "  Stop:         $COMPOSE_CMD down"
    echo ""
    echo "Remember to:"
    echo "  1. Configure Security Group to allow port 5000"
    if [ "$OS" = "ubuntu" ]; then
        echo "  2. Configure firewall (if enabled): sudo ufw allow 5000/tcp"
    elif [ "$OS" = "amzn" ]; then
        echo "  2. Configure firewall (if enabled): sudo firewall-cmd --permanent --add-port=5000/tcp"
    fi
    echo ""
else
    echo -e "${RED}✗ Container failed to start${NC}"
    echo "Check logs with: docker logs openpilot-detection"
    exit 1
fi
