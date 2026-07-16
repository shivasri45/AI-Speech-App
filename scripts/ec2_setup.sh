#!/bin/bash
# Automated EC2 setup script for Soft Skills Platform
# Runs completely non-interactive

set -e

# ═══════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════
REPO_URL="https://github.com/aviralMadhvan24/AI-Speech-App.git"
APP_DIR="/home/ubuntu/softskills"
LOG_FILE="/tmp/deploy.log"

echo "===================================================================" | tee -a $LOG_FILE
echo "Soft Skills Platform - AWS EC2 Auto-Deploy" | tee -a $LOG_FILE
echo "Started: $(date)" | tee -a $LOG_FILE
echo "===================================================================" | tee -a $LOG_FILE

# ═══════════════════════════════════════════════════════════════════
# 1. System Updates
# ═══════════════════════════════════════════════════════════════════
echo ">>> Step 1/10: System updates..." | tee -a $LOG_FILE
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -qq -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

# ═══════════════════════════════════════════════════════════════════
# 2. Install Dependencies
# ═══════════════════════════════════════════════════════════════════
echo ">>> Step 2/10: Installing dependencies..." | tee -a $LOG_FILE
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3.11 python3.11-venv python3.11-dev python3-pip \
    ffmpeg \
    nginx \
    git \
    build-essential \
    curl \
    htop \
    unzip

# Node.js 20
if ! command -v node > /dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - > /dev/null 2>&1
    sudo apt-get install -y -qq nodejs
fi

echo "Python: $(python3.11 --version)" | tee -a $LOG_FILE
echo "Node: $(node --version)" | tee -a $LOG_FILE

# ═══════════════════════════════════════════════════════════════════
# 3. Setup 4GB Swap
# ═══════════════════════════════════════════════════════════════════
echo ">>> Step 3/10: Setting up 4GB swap..." | tee -a $LOG_FILE
if [ ! -f /swapfile ]; then
    sudo fallocate -l 4G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile > /dev/null 2>&1
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null
fi

# ═══════════════════════════════════════════════════════════════════
# 4. Clone Repository
# ═══════════════════════════════════════════════════════════════════
echo ">>> Step 4/10: Cloning repository..." | tee -a $LOG_FILE
if [ ! -d "$APP_DIR" ]; then
    git clone $REPO_URL $APP_DIR
else
    cd $APP_DIR && git pull
fi
cd $APP_DIR

# ═══════════════════════════════════════════════════════════════════
# 5. Python Environment
# ═══════════════════════════════════════════════════════════════════
echo ">>> Step 5/10: Setting up Python environment..." | tee -a $LOG_FILE
cd $APP_DIR
if [ ! -d "venv" ]; then
    python3.11 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip --quiet

echo "Installing Python packages (10-15 min)..." | tee -a $LOG_FILE
pip install --no-cache-dir -r requirements.txt 2>&1 | tail -5 | tee -a $LOG_FILE

# ═══════════════════════════════════════════════════════════════════
# 6. Frontend Build
# ═══════════════════════════════════════════════════════════════════
echo ">>> Step 6/10: Building frontend..." | tee -a $LOG_FILE
cd $APP_DIR/frontend
if [ ! -d "node_modules" ]; then
    npm ci --silent 2>&1 | tail -3 | tee -a $LOG_FILE
fi
npm run build --silent 2>&1 | tail -3 | tee -a $LOG_FILE

# ═══════════════════════════════════════════════════════════════════
# 7. SS3 Service Setup
# ═══════════════════════════════════════════════════════════════════
echo ">>> Step 7/10: Setting up ss3 gesture service..." | tee -a $LOG_FILE
cd $APP_DIR/ss3
if [ ! -d "venv-ss3" ]; then
    python3.11 -m venv venv-ss3
fi
source venv-ss3/bin/activate
pip install --upgrade pip --quiet
pip install --no-cache-dir -r requirements.txt 2>&1 | tail -3 | tee -a $LOG_FILE
deactivate

# ═══════════════════════════════════════════════════════════════════
# 8. Systemd Services
# ═══════════════════════════════════════════════════════════════════
echo ">>> Step 8/10: Setting up systemd services..." | tee -a $LOG_FILE

sudo tee /etc/systemd/system/softskills-ss3.service > /dev/null <<'EOF'
[Unit]
Description=Soft Skills SS3 Gesture Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/softskills/ss3
Environment="PATH=/home/ubuntu/softskills/ss3/venv-ss3/bin"
ExecStart=/home/ubuntu/softskills/ss3/venv-ss3/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8001
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo tee /etc/systemd/system/softskills-backend.service > /dev/null <<'EOF'
[Unit]
Description=Soft Skills FastAPI Backend
After=network.target softskills-ss3.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/softskills
Environment="PATH=/home/ubuntu/softskills/venv/bin"
EnvironmentFile=/home/ubuntu/softskills/.env
ExecStart=/home/ubuntu/softskills/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable softskills-ss3 softskills-backend 2>&1 | tee -a $LOG_FILE

# ═══════════════════════════════════════════════════════════════════
# 9. Nginx Configuration
# ═══════════════════════════════════════════════════════════════════
echo ">>> Step 9/10: Configuring Nginx..." | tee -a $LOG_FILE

sudo tee /etc/nginx/sites-available/softskills > /dev/null <<'EOF'
client_max_body_size 50M;

server {
    listen 80 default_server;
    server_name _;

    # WebSocket routes
    location ~ ^/(gd|debate|battle)/ws/ {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
}
EOF

sudo ln -sf /etc/nginx/sites-available/softskills /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t 2>&1 | tee -a $LOG_FILE
sudo systemctl reload nginx

# ═══════════════════════════════════════════════════════════════════
# 10. Final Setup
# ═══════════════════════════════════════════════════════════════════
echo ">>> Step 10/10: Deployment complete!" | tee -a $LOG_FILE
echo "===================================================================" | tee -a $LOG_FILE
echo "SUCCESS! Now:" | tee -a $LOG_FILE
echo "1. Upload .env file with your API keys" | tee -a $LOG_FILE
echo "2. Run: sudo systemctl start softskills-ss3 softskills-backend" | tee -a $LOG_FILE
echo "===================================================================" | tee -a $LOG_FILE

echo "Deployment finished at $(date)"
