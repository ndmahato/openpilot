#!/bin/bash
# Docker Hub Setup and Verification Script
# Run this before deploy-ec2.sh if you encounter pull errors

set -e

echo "========================================="
echo "Docker Hub Setup & Verification"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed!${NC}"
    echo "Please run deploy-ec2.sh first, it will install Docker."
    exit 1
fi

echo -e "${YELLOW}Step 1: Verify Docker Hub image exists${NC}"
echo "Checking if kainosit/openpilot:latest is accessible..."
echo ""

# Try to pull without authentication first
if docker pull kainosit/openpilot:latest 2>&1 | grep -q "pull access denied"; then
    echo -e "${RED}✗ Image requires authentication or doesn't exist publicly${NC}"
    echo ""
    echo -e "${YELLOW}The repository might be:${NC}"
    echo "  1. Private (requires Docker Hub login)"
    echo "  2. Not yet pushed to Docker Hub"
    echo "  3. Under a different name"
    echo ""
    
    # Ask if user wants to login
    read -p "Do you have Docker Hub credentials for this repository? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Step 2: Login to Docker Hub${NC}"
        echo "Enter your Docker Hub credentials:"
        docker login
        
        echo ""
        echo -e "${YELLOW}Trying to pull again...${NC}"
        if docker pull kainosit/openpilot:latest; then
            echo -e "${GREEN}✓ Successfully pulled image!${NC}"
            echo ""
            echo -e "${GREEN}You can now run: ./deploy-ec2.sh${NC}"
        else
            echo -e "${RED}✗ Still cannot pull image${NC}"
            echo ""
            echo -e "${YELLOW}Alternative: Build from source${NC}"
            echo "The deploy-ec2.sh script can build the image locally if you have:"
            echo "  - Dockerfile"
            echo "  - test_yolo_multi_mobile.py"
            echo "  - requirements.txt"
            echo "  - SYSTEM_DOCUMENTATION.md"
            echo ""
            echo "Upload these files and run deploy-ec2.sh"
        fi
    else
        echo ""
        echo -e "${YELLOW}Alternative Options:${NC}"
        echo ""
        echo "Option 1: Make repository public"
        echo "  - Visit: https://hub.docker.com/repository/docker/kainosit/openpilot"
        echo "  - Go to Settings → Make Public"
        echo ""
        echo "Option 2: Build from source"
        echo "  - Upload source files to EC2:"
        echo "    • Dockerfile"
        echo "    • test_yolo_multi_mobile.py"
        echo "    • requirements.txt"
        echo "    • SYSTEM_DOCUMENTATION.md"
        echo "  - Run: ./deploy-ec2.sh"
        echo "  - Script will automatically build if pull fails"
        echo ""
        echo "Option 3: Use different image"
        echo "  - Update docker-compose.yml with accessible image"
    fi
else
    echo -e "${GREEN}✓ Image is publicly accessible!${NC}"
    echo ""
    docker images kainosit/openpilot:latest
    echo ""
    echo -e "${GREEN}You can now run: ./deploy-ec2.sh${NC}"
fi

echo ""
echo "========================================="
echo "For more help, see:"
echo "  - QUICK_DEPLOY.md"
echo "  - EC2_DEPLOYMENT_GUIDE.md"
echo "========================================="
