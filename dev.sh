#!/bin/bash

# Trivia Factory Development Environment Setup
# This script sets up the complete development environment

set -e

echo "🚀 Setting up Trivia Factory Development Environment"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python $PYTHON_VERSION found"
    else
        print_error "Python 3 not found. Please install Python 3.9+"
        exit 1
    fi
    
    # Check Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js $NODE_VERSION found"
    else
        print_warning "Node.js not found. Will install via nvm"
        install_nodejs
    fi
    
    # Check FFmpeg
    if command -v ffmpeg &> /dev/null; then
        print_success "FFmpeg found"
    else
        print_warning "FFmpeg not found. Installing..."
        install_ffmpeg
    fi
}

install_nodejs() {
    print_status "Installing Node.js via nvm..."
    
    if [ ! -d "$HOME/.nvm" ]; then
        curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
        export NVM_DIR="$HOME/.nvm"
        [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    fi
    
    nvm install 18
    nvm use 18
    print_success "Node.js 18 installed"
}

install_ffmpeg() {
    print_status "Installing FFmpeg..."
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    elif command -v brew &> /dev/null; then
        brew install ffmpeg
    else
        print_error "Package manager not found. Please install FFmpeg manually"
        exit 1
    fi
    
    print_success "FFmpeg installed"
}

# Setup backend
setup_backend() {
    print_status "Setting up backend..."
    
    cd backend
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    print_status "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        print_status "Creating .env file..."
        cp .env.example .env
        print_warning "Please edit backend/.env with your API keys and settings"
    fi
    
    cd ..
    print_success "Backend setup complete"
}

# Setup frontend
setup_frontend() {
    print_status "Setting up frontend..."
    
    cd frontend
    
    # Install dependencies
    print_status "Installing Node.js dependencies..."
    npm install
    
    # Create .env.local if it doesn't exist
    if [ ! -f ".env.local" ]; then
        print_status "Creating .env.local file..."
        cat > .env.local << 'ENV'
REACT_APP_API_URL=http://localhost:8000
REACT_APP_ENVIRONMENT=development
ENV
    fi
    
    cd ..
    print_success "Frontend setup complete"
}

# Setup assets
setup_assets() {
    print_status "Setting up assets..."
    
    if [ ! -d "assets" ]; then
        mkdir -p assets
        print_warning "Assets directory created. Please add your video templates and fonts."
    fi
    
    # Create sample assets structure
    mkdir -p assets/{templates,fonts,audio,images}
    
    print_status "Assets directory structure created:"
    echo "  assets/"
    echo "  ├── templates/     # Video templates (1.mp4, 2.mp4, 3.mp4)"
    echo "  ├── fonts/         # Font files (.ttf, .otf)"
    echo "  ├── audio/         # Audio assets (timer, ticking, ding)"
    echo "  └── images/        # Branding and UI images"
    
    print_success "Assets setup complete"
}

# Start development servers
start_dev_servers() {
    print_status "Starting development servers..."
    
    # Start backend in background
    print_status "Starting backend server..."
    cd backend
    source venv/bin/activate
    nohup uvicorn src.ui:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
    BACKEND_PID=$!
    cd ..
    
    # Wait for backend to start
    sleep 5
    
    # Start frontend in background
    print_status "Starting frontend server..."
    cd frontend
    nohup npm start > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    
    # Save PIDs for cleanup
    echo $BACKEND_PID > .backend.pid
    echo $FRONTEND_PID > .frontend.pid
    
    print_success "Development servers started!"
    echo ""
    echo "🌐 Frontend: http://localhost:3000"
    echo "�� Backend API: http://localhost:8000"
    echo "📚 API Docs: http://localhost:8000/docs"
    echo ""
    echo "📝 Logs:"
    echo "  Backend: tail -f backend.log"
    echo "  Frontend: tail -f frontend.log"
    echo ""
    echo "🛑 To stop servers: ./dev.sh stop"
}

# Stop development servers
stop_dev_servers() {
    print_status "Stopping development servers..."
    
    if [ -f ".backend.pid" ]; then
        BACKEND_PID=$(cat .backend.pid)
        kill $BACKEND_PID 2>/dev/null || true
        rm .backend.pid
    fi
    
    if [ -f ".frontend.pid" ]; then
        FRONTEND_PID=$(cat .frontend.pid)
        kill $FRONTEND_PID 2>/dev/null || true
        rm .frontend.pid
    fi
    
    print_success "Development servers stopped"
}

# Main execution
case "${1:-start}" in
    "start")
        check_prerequisites
        setup_backend
        setup_frontend
        setup_assets
        start_dev_servers
        ;;
    "stop")
        stop_dev_servers
        ;;
    "restart")
        stop_dev_servers
        sleep 2
        start_dev_servers
        ;;
    "setup")
        check_prerequisites
        setup_backend
        setup_frontend
        setup_assets
        print_success "Setup complete! Run './dev.sh start' to start servers"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|setup}"
        echo ""
        echo "Commands:"
        echo "  start   - Start development servers (default)"
        echo "  stop    - Stop development servers"
        echo "  restart - Restart development servers"
        echo "  setup   - Setup environment without starting servers"
        exit 1
        ;;
esac
