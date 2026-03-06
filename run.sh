#!/bin/bash
# Start both frontend and backend services for Voice Chatbot

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}Starting Lenskart Voice Chatbot${NC}"
echo "=================================="

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Check for required files
if [ ! -f "$PROJECT_DIR/vital-octagon-svc.json" ]; then
    echo -e "${RED}Error: vital-octagon-svc.json not found${NC}"
    echo "Please ensure the service account file is in the project root."
    exit 1
fi

# Set Google credentials
export GOOGLE_APPLICATION_CREDENTIALS="$PROJECT_DIR/vital-octagon-svc.json"

# Start backend
echo -e "\n${GREEN}Starting backend server...${NC}"
cd "$PROJECT_DIR/backend"

# Check if uv is available
if command -v uv &> /dev/null; then
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        uv venv
    fi

    # Install dependencies
    echo "Installing backend dependencies..."
    uv pip install -r requirements.txt

    # Activate and run
    source .venv/bin/activate
    python main.py &
    BACKEND_PID=$!
else
    echo -e "${RED}Error: uv not found. Please install uv package manager.${NC}"
    exit 1
fi

# Wait for backend to start
echo "Waiting for backend to start..."
sleep 3

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Backend failed to start${NC}"
    exit 1
fi

echo -e "${GREEN}Backend running on ws://localhost:8765${NC}"

# Start frontend
echo -e "\n${GREEN}Starting frontend server...${NC}"
cd "$PROJECT_DIR/frontend"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

# Start dev server
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 3

# Check if frontend is running
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}Frontend failed to start${NC}"
    cleanup
fi

echo -e "${GREEN}Frontend running on http://localhost:5173${NC}"
echo ""
echo "=================================="
echo -e "${GREEN}Voice Chatbot is ready!${NC}"
echo ""
echo "  Frontend: http://localhost:5173"
echo "  Backend:  ws://localhost:8765"
echo ""
echo "Press Ctrl+C to stop all services"
echo "=================================="

# Wait for processes
wait
