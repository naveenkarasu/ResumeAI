#!/bin/bash
# ResumeAI - Docker Development

set -e

echo "Starting ResumeAI with Docker (Development)"

# Build and start containers
docker-compose -f docker-compose.dev.yml up --build

echo "✅ Development environment stopped."
