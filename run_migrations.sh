#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🔄 Running local database migrations...${NC}"

# Detect if virtual environment exists
if [ -d "venv" ]; then
    ./venv/bin/alembic upgrade head
else
    alembic upgrade head
fi

echo -e "${GREEN}✅ Database migrations applied successfully!${NC}"
