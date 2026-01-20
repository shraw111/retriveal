#!/bin/bash
# Run the Drug Claims Retrieval System with Streamlit

echo "🚀 Starting Drug Claims Retrieval System..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found"
    echo "💡 Creating .env from template..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo "📝 Please edit .env and add your ANTHROPIC_API_KEY"
    echo ""
fi

# Check if dependencies are installed
if ! python -c "import streamlit" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -q -r requirements.txt
    echo "✅ Dependencies installed"
    echo ""
fi

# Run Streamlit
echo "🌐 Starting Streamlit server..."
echo "📍 Open your browser to: http://localhost:8501"
echo ""
streamlit run streamlit_app.py
