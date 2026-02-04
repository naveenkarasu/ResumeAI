#!/bin/bash
# Resume RAG Platform - Production Build Script

set -e

echo "🏗️  Building Resume RAG Platform for Production"

# Build frontend
echo "📦 Building frontend..."
cd frontend
npm ci --only=production
npm run build
cd ..

echo "✅ Frontend built successfully!"
echo "   Output: frontend/dist/"

# Verify backend
echo "🔍 Verifying backend..."
python -c "from src.ui.api import app; print('Backend OK')"

echo ""
echo "✅ Build complete! Ready for deployment."
echo ""
echo "To deploy with Docker:"
echo "  docker-compose up -d"
echo ""
echo "To run without Docker:"
echo "  ENVIRONMENT=production python -m uvicorn src.ui.api.main:app --workers 4"
