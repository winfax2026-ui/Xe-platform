#!/bin/bash
cd "$(dirname "$0")/backend"
source venv/bin/activate 2>/dev/null || true
export FLASK_APP=app.py
export FLASK_DEBUG=True
echo "🚀 Starting XE Platform..."
echo "📋 Visit: http://localhost:5000"
python app.py
