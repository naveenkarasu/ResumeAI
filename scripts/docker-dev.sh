#!/bin/bash
# Resume RAG Platform - Docker Development

set -e

echo "🐳 Starting Resume RAG Platform with Docker (Development)"

# Build and start containers
docker-compose -f docker-compose.dev.yml up --build

echo "✅ Development environment stopped."
