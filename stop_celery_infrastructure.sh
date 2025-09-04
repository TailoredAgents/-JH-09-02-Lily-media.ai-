#!/bin/bash

# Celery Infrastructure Cleanup Script
# 2025 Production Best Practices for Autonomous Social Media AI

set -e  # Exit on any error

echo "🛑 Stopping Celery Infrastructure for Autonomous Social Media AI..."
echo "=================================================================="

# Function to gracefully stop a process
stop_process() {
    local name=$1
    local pid=$2
    
    if [ -n "$pid" ] && kill -0 $pid 2>/dev/null; then
        echo "🔄 Stopping $name (PID: $pid)..."
        kill -TERM $pid
        
        # Wait up to 10 seconds for graceful shutdown
        for i in {1..10}; do
            if ! kill -0 $pid 2>/dev/null; then
                echo "✅ $name stopped gracefully"
                return 0
            fi
            sleep 1
        done
        
        # Force kill if still running
        if kill -0 $pid 2>/dev/null; then
            echo "⚠️  Force killing $name..."
            kill -KILL $pid 2>/dev/null || true
            sleep 1
            if ! kill -0 $pid 2>/dev/null; then
                echo "✅ $name force stopped"
            else
                echo "❌ Failed to stop $name"
            fi
        fi
    else
        echo "ℹ️  $name is not running"
    fi
}

# Load PIDs if available
if [ -f "logs/celery.pids" ]; then
    source logs/celery.pids
    echo "📂 Loaded saved PIDs"
fi

# Stop Flower Dashboard
if [ -n "$FLOWER_PID" ]; then
    stop_process "Flower Dashboard" $FLOWER_PID
else
    # Fallback: find and kill flower process
    FLOWER_PID=$(pgrep -f "flower" 2>/dev/null || echo "")
    if [ -n "$FLOWER_PID" ]; then
        stop_process "Flower Dashboard" $FLOWER_PID
    fi
fi

# Stop Celery Beat Scheduler
if [ -n "$BEAT_PID" ]; then
    stop_process "Celery Beat" $BEAT_PID
else
    # Fallback: find and kill beat process
    BEAT_PID=$(pgrep -f "celery.*beat" 2>/dev/null || echo "")
    if [ -n "$BEAT_PID" ]; then
        stop_process "Celery Beat" $BEAT_PID
    fi
fi

# Stop Celery Worker
if [ -n "$WORKER_PID" ]; then
    stop_process "Celery Worker" $WORKER_PID
else
    # Fallback: find and kill worker process
    WORKER_PID=$(pgrep -f "celery.*worker" 2>/dev/null || echo "")
    if [ -n "$WORKER_PID" ]; then
        stop_process "Celery Worker" $WORKER_PID
    fi
fi

# Clean up any remaining celery processes
echo "🧹 Cleaning up any remaining Celery processes..."
pkill -f "celery" 2>/dev/null || true

# Remove PID files
if [ -f "logs/celery.pids" ]; then
    rm logs/celery.pids
    echo "🗑️  Removed PID file"
fi

if [ -f "logs/celerybeat.pid" ]; then
    rm logs/celerybeat.pid
    echo "🗑️  Removed beat PID file"
fi

if [ -f "logs/celerybeat-schedule" ]; then
    rm logs/celerybeat-schedule
    echo "🗑️  Removed beat schedule file"
fi

# Optional: Stop Redis (uncomment if you want to stop Redis too)
# echo "🔄 Stopping Redis..."
# brew services stop redis

# Final verification
echo ""
echo "🔍 Verifying shutdown..."
echo "========================"

if pgrep -f "celery.*worker" > /dev/null 2>&1; then
    echo "⚠️  Some Celery worker processes may still be running"
else
    echo "✅ Celery workers stopped"
fi

if pgrep -f "celery.*beat" > /dev/null 2>&1; then
    echo "⚠️  Some Celery beat processes may still be running"
else
    echo "✅ Celery beat stopped"
fi

if pgrep -f "flower" > /dev/null 2>&1; then
    echo "⚠️  Some Flower processes may still be running"
else
    echo "✅ Flower stopped"
fi

echo ""
echo "🎉 Celery Infrastructure Shutdown Complete!"
echo "==========================================="
echo "📁 Log files preserved in ./logs/ directory"
echo "🔄 To restart, run: ./start_celery_infrastructure.sh"
echo ""
echo "✅ All autonomous social media operations stopped!"