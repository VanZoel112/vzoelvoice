#!/bin/bash

# =============================================================
# Voice Clone Bot - AWS Ubuntu Deploy Script
# Auto-deploy and run 24/7 with auto-restart capabilities
# =============================================================

set -e  # Exit on any error

# Configuration
SSH_KEY="~/keys/vzoel-key.pem"
SERVER="ubuntu@13.236.95.51"
REPO_NAME="vzoelvoice"
MAIN_FILE="main.py"
SERVICE_NAME="vzoelvoice-bot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if SSH key exists
check_ssh_key() {
    if [ ! -f "$SSH_KEY" ]; then
        error "SSH key not found at $SSH_KEY"
        exit 1
    fi
    chmod 600 "$SSH_KEY"
    log "SSH key verified ✅"
}

# Test SSH connection
test_connection() {
    log "Testing SSH connection..."
    if ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SERVER" "echo 'Connection successful'"; then
        log "SSH connection successful ✅"
    else
        error "Failed to connect to server"
        exit 1
    fi
}

# Deploy application to server
deploy_app() {
    log "Starting deployment process..."
    
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
#!/bin/bash

# Server-side deployment script
set -e

REPO_NAME="vzoelvoice"
MAIN_FILE="main.py"
SERVICE_NAME="vzoelvoice-bot"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "🚀 Starting server-side deployment..."

# Update system
log "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system packages
log "📦 Installing system dependencies..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    htop \
    tmux \
    supervisor \
    portaudio19-dev \
    python3-pyaudio \
    pulseaudio \
    alsa-utils \
    ffmpeg

# Create application directory
log "📁 Setting up application directory..."
cd /home/ubuntu
if [ -d "$REPO_NAME" ]; then
    log "Removing existing repository..."
    rm -rf "$REPO_NAME"
fi

# Clone or create repository
if [ ! -d "$REPO_NAME" ]; then
    log "📥 Creating application directory..."
    mkdir -p "$REPO_NAME"
fi

cd "$REPO_NAME"

# Create virtual environment
log "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and install dependencies
log "📦 Installing Python dependencies..."
pip install --upgrade pip setuptools wheel

# Install required packages
pip install \
    pyrogram \
    tgcrypto \
    scipy \
    sounddevice \
    numpy \
    aiohttp \
    aiofiles \
    psutil \
    requests

# Create main.py if it doesn't exist (placeholder)
if [ ! -f "$MAIN_FILE" ]; then
    log "⚠️  main.py not found, creating placeholder..."
    cat > main.py << 'EOF'
#!/usr/bin/env python3
"""
Voice Clone UserBot - Placeholder
Replace this file with your actual main.py
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    print("🤖 Voice Clone Bot - Placeholder")
    print("Please upload your actual main.py file")
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
EOF
    chmod +x main.py
fi

# Create startup script
log "📜 Creating startup script..."
cat > start_bot.sh << 'EOF'
#!/bin/bash

REPO_DIR="/home/ubuntu/vzoelvoice"
VENV_DIR="$REPO_DIR/venv"
MAIN_FILE="$REPO_DIR/main.py"
LOG_FILE="$REPO_DIR/bot.log"

cd "$REPO_DIR"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Set environment variables
export PYTHONPATH="$REPO_DIR:$PYTHONPATH"
export DISPLAY=:0

# Start the bot with logging
exec python3 "$MAIN_FILE" 2>&1 | tee -a "$LOG_FILE"
EOF

chmod +x start_bot.sh

# Create systemd service for 24/7 running
log "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=Voice Clone UserBot
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=5
User=ubuntu
WorkingDirectory=/home/ubuntu/$REPO_NAME
Environment=PATH=/home/ubuntu/$REPO_NAME/venv/bin
ExecStart=/home/ubuntu/$REPO_NAME/start_bot.sh
StandardOutput=append:/home/ubuntu/$REPO_NAME/service.log
StandardError=append:/home/ubuntu/$REPO_NAME/service.log
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF

# Create supervisor configuration as backup
log "⚙️  Creating supervisor configuration..."
sudo tee /etc/supervisor/conf.d/${SERVICE_NAME}.conf > /dev/null << EOF
[program:${SERVICE_NAME}]
command=/home/ubuntu/$REPO_NAME/start_bot.sh
directory=/home/ubuntu/$REPO_NAME
user=ubuntu
autostart=true
autorestart=true
startsecs=10
startretries=3
stdout_logfile=/home/ubuntu/$REPO_NAME/supervisor.log
stderr_logfile=/home/ubuntu/$REPO_NAME/supervisor.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
redirect_stderr=true
killasgroup=true
stopasgroup=true
EOF

# Create monitoring script
log "📊 Creating monitoring script..."
cat > monitor_bot.sh << 'EOF'
#!/bin/bash

SERVICE_NAME="vzoelvoice-bot"
LOG_FILE="/home/ubuntu/vzoelvoice/monitor.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

check_and_restart() {
    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        log_message "⚠️  Service $SERVICE_NAME is not running. Restarting..."
        sudo systemctl start "$SERVICE_NAME"
        log_message "✅ Service $SERVICE_NAME restarted"
    else
        log_message "✅ Service $SERVICE_NAME is running"
    fi
}

# Run check
check_and_restart
EOF

chmod +x monitor_bot.sh

# Create cron job for monitoring
log "⏰ Setting up monitoring cron job..."
(crontab -l 2>/dev/null; echo "*/5 * * * * /home/ubuntu/$REPO_NAME/monitor_bot.sh") | crontab -

# Create management script
log "🛠️  Creating management script..."
cat > manage_bot.sh << 'EOF'
#!/bin/bash

SERVICE_NAME="vzoelvoice-bot"
REPO_DIR="/home/ubuntu/vzoelvoice"

case "$1" in
    start)
        echo "🚀 Starting Voice Clone Bot..."
        sudo systemctl start "$SERVICE_NAME"
        sudo systemctl enable "$SERVICE_NAME"
        ;;
    stop)
        echo "🛑 Stopping Voice Clone Bot..."
        sudo systemctl stop "$SERVICE_NAME"
        ;;
    restart)
        echo "🔄 Restarting Voice Clone Bot..."
        sudo systemctl restart "$SERVICE_NAME"
        ;;
    status)
        echo "📊 Voice Clone Bot Status:"
        sudo systemctl status "$SERVICE_NAME"
        ;;
    logs)
        echo "📝 Recent logs:"
        tail -n 50 "$REPO_DIR/service.log"
        ;;
    live-logs)
        echo "📝 Live logs (Ctrl+C to exit):"
        tail -f "$REPO_DIR/service.log"
        ;;
    update)
        echo "📥 Updating bot..."
        cd "$REPO_DIR"
        git pull || echo "No git repository found"
        sudo systemctl restart "$SERVICE_NAME"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|live-logs|update}"
        echo ""
        echo "Commands:"
        echo "  start      - Start the bot service"
        echo "  stop       - Stop the bot service"
        echo "  restart    - Restart the bot service"
        echo "  status     - Show service status"
        echo "  logs       - Show recent logs"
        echo "  live-logs  - Show live logs"
        echo "  update     - Update and restart bot"
        exit 1
        ;;
esac
EOF

chmod +x manage_bot.sh

# Reload systemd and start services
log "🔄 Reloading systemd and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

# Update supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Create deployment info
log "📋 Creating deployment info..."
cat > deployment_info.txt << EOF
Voice Clone Bot Deployment Info
===============================
Deployed: $(date)
Repository: $REPO_NAME
Main File: $MAIN_FILE
Service Name: $SERVICE_NAME

Management Commands:
./manage_bot.sh start    - Start bot
./manage_bot.sh stop     - Stop bot
./manage_bot.sh status   - Check status
./manage_bot.sh logs     - View logs

Files Created:
- main.py (placeholder - upload your actual file)
- start_bot.sh
- manage_bot.sh
- monitor_bot.sh
- /etc/systemd/system/${SERVICE_NAME}.service

Logs Location:
- Service logs: ~/vzoelvoice/service.log
- Bot logs: ~/vzoelvoice/bot.log
- Monitor logs: ~/vzoelvoice/monitor.log

Monitoring:
- Cron job checks service every 5 minutes
- Auto-restart on failure
- Persistent across reboots
EOF

log "✅ Server-side deployment completed!"
log "📁 Working directory: /home/ubuntu/$REPO_NAME"
log "🛠️  Management script: ./manage_bot.sh"

ENDSSH

    log "✅ Deployment completed successfully!"
}

# Upload your main.py file
upload_main_file() {
    log "📤 Uploading main.py file..."
    
    if [ -f "./main.py" ]; then
        scp -i "$SSH_KEY" -o StrictHostKeyChecking=no "./main.py" "$SERVER:/home/ubuntu/$REPO_NAME/"
        log "✅ main.py uploaded successfully!"
    else
        warning "main.py not found in current directory"
        warning "Please upload your main.py manually:"
        warning "scp -i $SSH_KEY main.py $SERVER:/home/ubuntu/$REPO_NAME/"
    fi
}

# Start the bot service
start_service() {
    log "🚀 Starting bot service..."
    ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" << 'ENDSSH'
cd /home/ubuntu/vzoelvoice
./manage_bot.sh start
sleep 3
./manage_bot.sh status
ENDSSH
    log "✅ Bot service started!"
}

# Show deployment summary
show_summary() {
    log "🎉 Deployment Summary:"
    echo ""
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    echo ""
    echo -e "${BLUE}SSH Connection:${NC}"
    echo "  ssh -i $SSH_KEY $SERVER"
    echo ""
    echo -e "${BLUE}Bot Management:${NC}"
    echo "  ssh -i $SSH_KEY $SERVER 'cd /home/ubuntu/$REPO_NAME && ./manage_bot.sh status'"
    echo "  ssh -i $SSH_KEY $SERVER 'cd /home/ubuntu/$REPO_NAME && ./manage_bot.sh logs'"
    echo "  ssh -i $SSH_KEY $SERVER 'cd /home/ubuntu/$REPO_NAME && ./manage_bot.sh restart'"
    echo ""
    echo -e "${BLUE}Upload main.py:${NC}"
    echo "  scp -i $SSH_KEY main.py $SERVER:/home/ubuntu/$REPO_NAME/"
    echo ""
    echo -e "${BLUE}Features:${NC}"
    echo "  • 24/7 running with auto-restart"
    echo "  • Persistent across reboots"
    echo "  • Automatic monitoring every 5 minutes"
    echo "  • Comprehensive logging"
    echo "  • Easy management commands"
    echo ""
    echo -e "${GREEN}Bot is now running 24/7! 🚀${NC}"
}

# Main execution
main() {
    log "🤖 Voice Clone Bot - AWS Deployment Script"
    log "================================================="
    
    check_ssh_key
    test_connection
    deploy_app
    upload_main_file
    start_service
    show_summary
    
    log "🎯 Deployment process completed!"
}

# Handle script arguments
case "${1:-deploy}" in
    deploy)
        main
        ;;
    upload)
        check_ssh_key
        upload_main_file
        ;;
    restart)
        check_ssh_key
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "cd /home/ubuntu/$REPO_NAME && ./manage_bot.sh restart"
        ;;
    status)
        check_ssh_key
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "cd /home/ubuntu/$REPO_NAME && ./manage_bot.sh status"
        ;;
    logs)
        check_ssh_key
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "cd /home/ubuntu/$REPO_NAME && ./manage_bot.sh logs"
        ;;
    connect)
        check_ssh_key
        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER"
        ;;
    *)
        echo "Usage: $0 [deploy|upload|restart|status|logs|connect]"
        echo ""
        echo "Commands:"
        echo "  deploy   - Full deployment (default)"
        echo "  upload   - Upload main.py only"
        echo "  restart  - Restart bot service"
        echo "  status   - Check bot status"
        echo "  logs     - View bot logs"
        echo "  connect  - SSH into server"
        exit 1
        ;;
esac
