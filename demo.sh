#!/bin/bash
# Run the complete demo test suite

echo "🧪 AI-Driven Outreach Engine - Demo Test Suite"
echo "=============================================="
echo ""

# Check if server is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Server is not running!"
    echo ""
    echo "Please start the server first:"
    echo "   Terminal 1: ./start.sh (or python main.py)"
    echo "   Terminal 2: ./demo.sh"
    echo ""
    exit 1
fi

echo "✅ Server is running!"
echo ""
echo "Running demo workflow..."
echo ""

# Run demo script
python3 demo.py

echo ""
echo "Demo complete! Check the output above."
