#!/bin/bash
# Quick start script for AI-Driven Outreach Engine

echo "🚀 AI-Driven Outreach Engine - Quick Start"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
    echo ""
fi

# Check if database exists
if [ ! -f outreach.db ]; then
    echo "🗄️  Initializing database..."
    python3 -c "from src.database import engine, Base; Base.metadata.create_all(bind=engine); print('✅ Database initialized!')"
    echo ""
fi

echo "🎯 Starting FastAPI server..."
echo "   Server will be available at: http://localhost:8000"
echo "   API docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start server
python3 main.py
