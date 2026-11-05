#!/bin/bash
# ForexNews AI - Startup Script

set -e

echo "🚀 Starting ForexNews AI..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Copying from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}❌ Please edit .env with your API keys before running!${NC}"
    exit 1
fi

# Check for required API keys
source .env
MISSING_KEYS=()

if [ -z "$ALPHA_VANTAGE_API_KEY" ] || [ "$ALPHA_VANTAGE_API_KEY" = "your_alpha_vantage_key_here" ]; then
    MISSING_KEYS+=("ALPHA_VANTAGE_API_KEY")
fi

if [ -z "$NEWSAPI_KEY" ] || [ "$NEWSAPI_KEY" = "your_newsapi_key_here" ]; then
    MISSING_KEYS+=("NEWSAPI_KEY")
fi

if [ -z "$OANDA_API_KEY" ] || [ "$OANDA_API_KEY" = "your_oanda_key_here" ]; then
    MISSING_KEYS+=("OANDA_API_KEY")
fi

if [ ${#MISSING_KEYS[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Missing API keys: ${MISSING_KEYS[*]}${NC}"
    echo -e "${YELLOW}   The system will run with limited functionality (yfinance/CCXT fallback)${NC}"
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p backend/ml/models
mkdir -p data/{raw,processed,cache}
mkdir -p logs

# Pull latest images
echo "📦 Pulling Docker images..."
docker-compose pull

# Start services
echo "🔧 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
check_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service is ready${NC}"
            return 0
        fi
        echo -e "${YELLOW}⏳ Waiting for $service... (attempt $attempt/$max_attempts)${NC}"
        sleep 2
        ((attempt++))
    done

    echo -e "${RED}❌ $service failed to start${NC}"
    return 1
}

echo "🔍 Checking service health..."
check_service "Backend" "http://localhost:8000/health"
check_service "Frontend" "http://localhost:3000/health"

echo ""
echo -e "${GREEN}🎉 ForexNews AI is running!${NC}"
echo ""
echo "📊 Access points:"
echo "   Frontend:     http://localhost:3000"
echo "   Backend API:  http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo "   Flower:       http://localhost:5555"
echo ""
echo "📝 Logs:"
echo "   docker-compose logs -f backend"
echo "   docker-compose logs -f frontend"
echo "   docker-compose logs -f celery-worker"
echo ""
echo "🛑 To stop: docker-compose down"