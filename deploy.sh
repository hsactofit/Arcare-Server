#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🚀 Starting local CI/CD pipeline...${NC}"

# Step 1: Run the local test suite
echo -e "${YELLOW}🔍 Running test suite...${NC}"
if [ -d "venv" ]; then
    ./venv/bin/python test_api.py
else
    python3 test_api.py
fi

# Capture test exit status
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}❌ Tests failed! Aborting deployment.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Tests passed successfully!${NC}"

# Step 2: Deploying via Docker Compose
echo -e "${YELLOW}🐳 Deploying updated code to Docker containers...${NC}"

# Detect if we need to use 'sg docker' for group permissions
if ! docker ps >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Direct docker access denied. Retrying with 'sg docker'...${NC}"
    sg docker -c "docker compose up -d --build"
else
    docker compose up -d --build
fi

echo -e "${GREEN}✨ CI/CD Deployment complete! Service is online.${NC}"
