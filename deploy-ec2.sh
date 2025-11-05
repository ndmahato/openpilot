#!/bin/bash
# EC2 Deployment Script for OpenPilot Detection System
# Run this script on your EC2 instance after installing Docker

set -e  # Exit on any error

echo "========================================"
echo "OpenPilot Detection - EC2 Deployment"
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker not found. Installing Docker...${NC}"
    sudo yum update -y
    sudo yum install -y docker
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -a -G docker $USER
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

# Pull latest image
echo -e "${YELLOW}Pulling latest image from Docker Hub...${NC}"
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull

# Stop existing container (if any)
echo -e "${YELLOW}Stopping existing container (if any)...${NC}"
docker compose down 2>/dev/null || true

# Start container
echo -e "${YELLOW}Starting container...${NC}"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

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
    echo "  Stop:         docker compose down"
    echo ""
    echo "Remember to:"
    echo "  1. Configure Security Group to allow port 5000"
    echo "  2. Configure firewall (if enabled): sudo firewall-cmd --permanent --add-port=5000/tcp"
    echo ""
else
    echo -e "${RED}✗ Container failed to start${NC}"
    echo "Check logs with: docker logs openpilot-detection"
    exit 1
fi
