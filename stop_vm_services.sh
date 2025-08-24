#!/bin/bash
# Trivia Factory VM Services Stop Script

echo "🛑 Stopping Trivia Factory Services..."

# Function to stop service
stop_service() {
    local name=$1
    local pid_file="logs/${name}.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 $pid 2>/dev/null; then
            echo "  🛑 Stopping $name (PID: $pid)..."
            kill $pid
            
            # Wait for graceful shutdown
            local count=0
            while kill -0 $pid 2>/dev/null && [ $count -lt 10 ]; do
                sleep 1
                count=$((count + 1))
            done
            
            # Force kill if still running
            if kill -0 $pid 2>/dev/null; then
                echo "    ⚠️  Force killing $name..."
                kill -9 $pid
            fi
            
            echo "    ✅ $name stopped"
        else
            echo "  ℹ️  $name not running"
        fi
        rm -f "$pid_file"
    else
        echo "  ℹ️  No PID file for $name"
    fi
}

# Stop all services
stop_service "api"
stop_service "worker"
stop_service "ui"

echo ""
echo "✅ All services stopped"
echo "📝 Logs remain available in logs/ directory"
