#!/bin/bash

# ========================================
# Voice Clone Userbot - AWS Ubuntu Deployment Script
# Run from Termux to deploy to AWS Ubuntu 24/7
# ========================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="voice-clone-userbot"
REMOTE_USER="ubuntu"
REMOTE_HOST=""  # Will be set via parameter
REMOTE_PORT="22"
LOCAL_PROJECT_PATH="$(pwd)"
REMOTE_PROJECT_PATH="/home/ubuntu/${PROJECT_NAME}"

print_header() {
    echo -e "${BLUE}"
    echo "========================================"
    echo "  Voice Clone Userbot AWS Deployment"
    echo "========================================"
    echo -e "${NC}"
}

print_step() {
    echo -e "${YELLOW}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_termux_dependencies() {
    print_step "Checking Termux dependencies..."
    
    # Check if openssh is installed
    if ! command -v ssh &> /dev/null; then
        echo "Installing openssh..."
        pkg update && pkg install -y openssh
    fi
    
    # Check if rsync is installed
    if ! command -v rsync &> /dev/null; then
        echo "Installing rsync..."
        pkg install -y rsync
    fi
    
    print_success "Termux dependencies ready"
}

upload_project() {
    print_step "Uploading project files to AWS..."
    
    # Create remote directory
    ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} "mkdir -p ${REMOTE_PROJECT_PATH}"
    
    # Upload project files
    rsync -avz -e "ssh -p ${REMOTE_PORT}" \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.env' \
        --exclude='*.session' \
        --exclude='*.session-journal' \
        ${LOCAL_PROJECT_PATH}/ \
        ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PROJECT_PATH}/
    
    print_success "Project uploaded successfully"
}

setup_aws_environment() {
    print_step "Setting up AWS Ubuntu environment..."
    
    ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} << 'EOF'
        # Update system
        sudo apt update && sudo apt upgrade -y
        
        # Install Python and pip
        sudo apt install -y python3 python3-pip python3-venv
        
        # Install audio system dependencies
        sudo apt install -y pulseaudio pulseaudio-utils alsa-utils
        sudo apt install -y portaudio19-dev python3-pyaudio
        
        # Install system dependencies for audio processing
        sudo apt install -y build-essential libasound2-dev
        
        # Install screen for background process management
        sudo apt install -y screen htop git
        
        # Create virtual environment
        cd /home/ubuntu/voice-clone-userbot
        python3 -m venv venv
        source venv/bin/activate
        
        # Upgrade pip
        pip install --upgrade pip
        
        # Install requirements
        pip install -r requirements.txt
        
        echo "AWS environment setup completed!"
EOF
    
    print_success "AWS environment ready"
}

create_systemd_service() {
    print_step "Creating systemd service for 24/7 operation..."
    
    ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} << 'EOF'
        # Create systemd service file
        sudo tee /etc/systemd/system/voice-clone-userbot.service > /dev/null << 'SERVICE'
[Unit]
Description=Voice Clone Userbot
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/voice-clone-userbot
Environment=PATH=/home/ubuntu/voice-clone-userbot/venv/bin
Environment=PYTHONPATH=/home/ubuntu/voice-clone-userbot
Environment=PULSE_RUNTIME_PATH=/tmp/pulse-ubuntu
ExecStartPre=/bin/bash -c 'pulseaudio --start --daemonize || true'
ExecStart=/home/ubuntu/voice-clone-userbot/venv/bin/python voice_clone_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=voice-clone-userbot

[Install]
WantedBy=multi-user.target
SERVICE

        # Reload systemd and enable service
        sudo systemctl daemon-reload
        sudo systemctl enable voice-clone-userbot.service
        
        echo "Systemd service created and enabled!"
EOF
    
    print_success "Systemd service configured"
}

create_monitoring_script() {
    print_step "Creating monitoring and management scripts..."
    
    ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} << 'EOF'
        cd /home/ubuntu/voice-clone-userbot
        
        # Create management script
        cat > manage_bot.sh << 'SCRIPT'
#!/bin/bash

case "$1" in
    start)
        echo "Starting Voice Clone Userbot..."
        sudo systemctl start voice-clone-userbot.service
        echo "Bot started!"
        ;;
    stop)
        echo "Stopping Voice Clone Userbot..."
        sudo systemctl stop voice-clone-userbot.service
        echo "Bot stopped!"
        ;;
    restart)
        echo "Restarting Voice Clone Userbot..."
        sudo systemctl restart voice-clone-userbot.service
        echo "Bot restarted!"
        ;;
    status)
        sudo systemctl status voice-clone-userbot.service
        ;;
    logs)
        sudo journalctl -u voice-clone-userbot.service -f
        ;;
    install)
        echo "Installing/Updating dependencies..."
        source venv/bin/activate
        pip install -r requirements.txt --upgrade
        echo "Dependencies updated!"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|install}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the userbot"
        echo "  stop    - Stop the userbot" 
        echo "  restart - Restart the userbot"
        echo "  status  - Show service status"
        echo "  logs    - Show real-time logs"
        echo "  install - Update dependencies"
        ;;
esac
SCRIPT
        
        chmod +x manage_bot.sh
        
        # Create auto-restart script
        cat > auto_restart.sh << 'SCRIPT'
#!/bin/bash
# Auto-restart script - runs every 5 minutes via cron

SERVICE_NAME="voice-clone-userbot.service"

if ! systemctl is-active --quiet $SERVICE_NAME; then
    echo "$(date): Service is down, restarting..." >> /home/ubuntu/voice-clone-userbot/restart.log
    sudo systemctl restart $SERVICE_NAME
    sleep 10
    
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "$(date): Service restarted successfully!" >> /home/ubuntu/voice-clone-userbot/restart.log
    else
        echo "$(date): Failed to restart service!" >> /home/ubuntu/voice-clone-userbot/restart.log
    fi
fi
SCRIPT
        
        chmod +x auto_restart.sh
        
        # Add to crontab
        (crontab -l 2>/dev/null; echo "*/5 * * * * /home/ubuntu/voice-clone-userbot/auto_restart.sh") | crontab -
        
        echo "Management scripts created!"
EOF
    
    print_success "Monitoring scripts ready"
}

start_userbot() {
    print_step "Starting Voice Clone Userbot..."
    
    ssh -p ${REMOTE_PORT} ${REMOTE_USER}@${REMOTE_HOST} << 'EOF'
        cd /home/ubuntu/voice-clone-userbot
        
        # Start PulseAudio for audio processing
        pulseaudio --start --daemonize || true
        
        # Start the service
        sudo systemctl start voice-clone-userbot.service
        
        # Wait a moment and check status
        sleep 3
        sudo systemctl status voice-clone-userbot.service --no-pager
        
        echo ""
        echo "🎉 Voice Clone Userbot is now running 24/7!"
        echo ""
        echo "Management commands:"
        echo "  ./manage_bot.sh start    - Start bot"
        echo "  ./manage_bot.sh stop     - Stop bot"
        echo "  ./manage_bot.sh restart  - Restart bot"
        echo "  ./manage_bot.sh status   - Check status"
        echo "  ./manage_bot.sh logs     - View logs"
EOF
    
    print_success "Userbot started and running 24/7!"
}

show_usage() {
    echo "Usage: $0 <AWS_IP_ADDRESS> [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -p PORT     SSH port (default: 22)"
    echo "  -u USER     Remote user (default: ubuntu)"
    echo "  -h          Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 52.91.123.456"
    echo "  $0 52.91.123.456 -p 2222"
    echo "  $0 52.91.123.456 -u admin"
}

# Main execution
main() {
    # Parse arguments
    if [ $# -eq 0 ]; then
        show_usage
        exit 1
    fi
    
    REMOTE_HOST=$1
    shift
    
    while getopts "p:u:h" opt; do
        case $opt in
            p)
                REMOTE_PORT="$OPTARG"
                ;;
            u)
                REMOTE_USER="$OPTARG"
                ;;
            h)
                show_usage
                exit 0
                ;;
            \?)
                echo "Invalid option: -$OPTARG" >&2
                show_usage
                exit 1
                ;;
        esac
    done
    
    print_header
    
    echo -e "Target Server: ${GREEN}${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PORT}${NC}"
    echo -e "Project Path:  ${GREEN}${REMOTE_PROJECT_PATH}${NC}"
    echo ""
    
    # Confirm before proceeding
    read -p "Continue with deployment? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment cancelled."
        exit 0
    fi
    
    # Execute deployment steps
    check_termux_dependencies
    upload_project
    setup_aws_environment
    create_systemd_service
    create_monitoring_script
    start_userbot
    
    print_success "🎉 Deployment completed successfully!"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo "1. SSH to your server: ssh ${REMOTE_USER}@${REMOTE_HOST}"
    echo "2. Check bot status: ./manage_bot.sh status"
    echo "3. View logs: ./manage_bot.sh logs"
    echo ""
    echo -e "${YELLOW}The bot is now running 24/7 on your AWS server!${NC}"
}

# Run main function with all arguments
main "$@"
