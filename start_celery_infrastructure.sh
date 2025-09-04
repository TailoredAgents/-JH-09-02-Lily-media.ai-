#!/bin/bash

# Celery Infrastructure Startup Script
# 2025 Production Best Practices for Autonomous Social Media AI

set -e  # Exit on any error

echo "🚀 Starting Celery Infrastructure for Autonomous Social Media AI..."
echo "==============================================================="

# Function to check if service is running
check_service() {
    local name=$1
    local port=$2
    if lsof -i:$port > /dev/null 2>&1; then
        echo "✅ $name is running on port $port"
        return 0
    else
        echo "❌ $name is not running on port $port"
        return 1
    fi
}

# Function to start service in background
start_background_service() {
    local name=$1
    local command=$2
    echo "🔄 Starting $name..."
    nohup $command > logs/${name}.log 2>&1 &
    sleep 2
    echo "✅ $name started (PID: $!)"
}

# Create logs directory
mkdir -p logs

# 1. Verify Redis is running
echo "🔍 Checking Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "🔄 Starting Redis..."
    brew services start redis
    sleep 2
fi

if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is running"
else
    echo "❌ Redis failed to start"
    exit 1
fi

# 2. Start Celery Worker with Production Config
echo "🔄 Starting Celery Worker..."
nohup celery -A backend.tasks.celery_app worker \
    --loglevel=info \
    --queues=autonomous,reports,metrics,posting,research,token_health,x_polling,webhook_watchdog \
    --concurrency=1 \
    --max-tasks-per-child=5 \
    --max-memory-per-child=200000 \
    --pool=threads \
    --hostname=worker1@%h > logs/celery-worker.log 2>&1 &
WORKER_PID=$!
sleep 3
echo "✅ Celery Worker started (PID: $WORKER_PID)"

# 3. Start Celery Beat Scheduler
echo "🔄 Starting Celery Beat Scheduler..."
nohup celery -A backend.tasks.celery_app beat \
    --loglevel=info \
    --pidfile=logs/celerybeat.pid \
    --schedule=logs/celerybeat-schedule > logs/celery-beat.log 2>&1 &
BEAT_PID=$!
sleep 2
echo "✅ Celery Beat started (PID: $BEAT_PID)"

# 4. Start Flower Monitoring Dashboard
echo "🔄 Starting Flower Monitoring Dashboard..."
nohup celery -A backend.tasks.celery_app flower \
    --port=5555 \
    --basic_auth=admin:flower2025 \
    --url_prefix=flower > logs/flower.log 2>&1 &
FLOWER_PID=$!
sleep 3

# 5. Verify all services are running
echo ""
echo "🔍 Verifying all services..."
echo "================================="

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: Running"
else
    echo "❌ Redis: Not responding"
fi

# Check if processes are still running
if kill -0 $WORKER_PID 2>/dev/null; then
    echo "✅ Celery Worker: Running (PID: $WORKER_PID)"
else
    echo "❌ Celery Worker: Failed to start"
fi

if kill -0 $BEAT_PID 2>/dev/null; then
    echo "✅ Celery Beat: Running (PID: $BEAT_PID)"
else
    echo "❌ Celery Beat: Failed to start"
fi

if kill -0 $FLOWER_PID 2>/dev/null; then
    echo "✅ Flower Dashboard: Running (PID: $FLOWER_PID)"
else
    echo "❌ Flower Dashboard: Failed to start"
fi

# 6. Display status and access information
echo ""
echo "🎉 Celery Infrastructure Successfully Started!"
echo "=============================================="
echo "📊 Monitoring Dashboard: http://localhost:5555"
echo "🔐 Flower Credentials: admin / flower2025"
echo "📁 Logs Directory: ./logs/"
echo ""
echo "🔧 Available Queues:"
echo "   • autonomous    - Daily/weekly content generation cycles"
echo "   • reports       - Performance and analytics reports"
echo "   • metrics       - System metrics collection"
echo "   • posting       - Scheduled content posting"
echo "   • research      - Lightweight research tasks"
echo "   • token_health  - OAuth token management"
echo "   • x_polling     - Twitter/X mentions polling"
echo "   • webhook_watchdog - Webhook monitoring"
echo ""
echo "📈 Scheduled Tasks:"
echo "   • Daily content generation: Every 24 hours"
echo "   • Weekly reports: Every 7 days"
echo "   • Metrics collection: Every 24 hours"
echo "   • Content posting: Every 15 minutes"
echo "   • Research tasks: Every 8 hours"
echo "   • Token health audit: Every 24 hours"
echo "   • X mentions polling: Every 15 minutes"
echo "   • DLQ watchdog: Every hour"
echo ""
echo "🛑 To stop all services, run: ./stop_celery_infrastructure.sh"
echo ""

# Save PIDs for cleanup script
echo "WORKER_PID=$WORKER_PID" > logs/celery.pids
echo "BEAT_PID=$BEAT_PID" >> logs/celery.pids
echo "FLOWER_PID=$FLOWER_PID" >> logs/celery.pids

echo "✅ Infrastructure ready for autonomous social media operations!"