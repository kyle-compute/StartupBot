#!/bin/bash

# Discord Bot Deployment Script for Digital Ocean
# Make sure to run: chmod +x deploy.sh

set -e

# Configuration
DROPLET_IP="YOUR_DROPLET_IP_HERE"
SSH_KEY="~/.ssh/id_rsa"
REMOTE_USER="root"
APP_DIR="/opt/discord-bot"
REPO_URL="https://github.com/yourusername/discord-bot.git"

echo "🚀 Starting deployment to Digital Ocean..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required variables are set
if [[ "$DROPLET_IP" == "YOUR_DROPLET_IP_HERE" ]]; then
    print_error "Please set your DROPLET_IP in the script"
    exit 1
fi

# Check if SSH key exists
if [[ ! -f "$SSH_KEY" ]]; then
    print_error "SSH key not found at $SSH_KEY"
    exit 1
fi

# Check if Docker is installed on droplet
print_status "Checking Docker installation on droplet..."
ssh -i "$SSH_KEY" "$REMOTE_USER@$DROPLET_IP" "docker --version" || {
    print_error "Docker is not installed on the droplet"
    print_status "Installing Docker..."
    ssh -i "$SSH_KEY" "$REMOTE_USER@$DROPLET_IP" "
        apt-get update &&
        apt-get install -y docker.io docker-compose &&
        systemctl start docker &&
        systemctl enable docker
    "
}

# Check if Docker Compose is installed
print_status "Checking Docker Compose installation..."
ssh -i "$SSH_KEY" "$REMOTE_USER@$DROPLET_IP" "docker-compose --version" || {
    print_error "Docker Compose is not installed on the droplet"
    print_status "Installing Docker Compose..."
    ssh -i "$SSH_KEY" "$REMOTE_USER@$DROPLET_IP" "
        curl -L \"https://github.com/docker/compose/releases/download/v2.20.2/docker-compose-linux-x86_64\" -o /usr/local/bin/docker-compose &&
        chmod +x /usr/local/bin/docker-compose
    "
}

# Create app directory
print_status "Creating application directory..."
ssh -i "$SSH_KEY" "$REMOTE_USER@$DROPLET_IP" "mkdir -p $APP_DIR"

# Copy files to droplet
print_status "Copying application files..."
scp -i "$SSH_KEY" -r . "$REMOTE_USER@$DROPLET_IP:$APP_DIR/"

# Set up environment file
print_status "Setting up environment file..."
ssh -i "$SSH_KEY" "$REMOTE_USER@$DROPLET_IP" "
    cd $APP_DIR &&
    if [[ ! -f .env ]]; then
        cp .env.example .env
        echo 'Please update the .env file with your actual values:'
        echo '1. DISCORD_BOT_TOKEN'
        echo '2. POSTGRES_PASSWORD'
        echo 'Then run: ./deploy.sh'
        exit 1
    fi
"

# Create necessary directories
print_status "Creating data directories..."
ssh -i "$SSH_KEY" "$REMOTE_USER@$DROPLET_IP" "
    cd $APP_DIR &&
    mkdir -p data logs
"

# Build and start the containers
print_status "Building and starting containers..."
ssh -i "$SSH_KEY" "$REMOTE_USER@$DROPLET_IP" "
    cd $APP_DIR &&
    docker-compose down &&
    docker-compose build &&
    docker-compose up -d
"

# Check if containers are running
print_status "Checking container status..."
ssh -i "$SSH_KEY" "$REMOTE_USER@$DROPLET_IP" "
    cd $APP_DIR &&
    docker-compose ps
"

# Set up automatic restart
print_status "Setting up automatic restart..."
ssh -i "$SSH_KEY" "$REMOTE_USER@$DROPLET_IP" "
    cd $APP_DIR &&
    # Create systemd service for auto-restart
    cat > /etc/systemd/system/discord-bot.service << 'EOF'
[Unit]
Description=Discord Accountability Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable discord-bot
"

# Display final status
print_status "Deployment completed!"
print_status "Bot should be running at: $DROPLET_IP"
print_status "To check logs: ssh -i $SSH_KEY $REMOTE_USER@$DROPLET_IP 'cd $APP_DIR && docker-compose logs -f'"
print_status "To restart: ssh -i $SSH_KEY $REMOTE_USER@$DROPLET_IP 'cd $APP_DIR && docker-compose restart'"

echo ""
print_warning "Don't forget to:"
print_warning "1. Configure your Discord bot token in the .env file"
print_warning "2. Set up your database password"
print_warning "3. Configure firewall rules if needed"
print_warning "4. Set up monitoring and backups"