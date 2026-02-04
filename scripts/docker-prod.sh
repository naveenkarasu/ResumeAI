#!/bin/bash
# ResumeAI - Docker Production

set -e

echo "Starting ResumeAI with Docker (Production)"

# Check for .env
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "   Copy .env.example to .env and configure your settings"
    exit 1
fi

# Build and start containers
docker-compose up -d --build

echo ""
echo "✅ Production environment started!"
echo "   API: http://localhost:8000"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
