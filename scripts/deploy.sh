#!/bin/bash
# One-command deployment script for AWS EC2 Ubuntu 22.04
# 
# Usage:
#   1. Launch EC2 t3.medium with Ubuntu 22.04
#   2. SSH in: ssh -i key.pem ubuntu@your-ip
#   3. Run: curl -sL https://your-repo/deploy.sh | bash
#      OR: git clone repo && cd softskills && bash scripts/deploy.sh

set -e  # Exit on error

# ═══════════════════════════════════════════════════════════════════
# Configuration - EDIT THESE
# ═══════════════════════════════════════════════════════════════════

REPO_URL="${REPO_URL:-https://github.com/YOUR_USERNAME/softskills2.git}"
APP_DIR="/home/ubuntu/softskills"
DOMAIN="${DOMAIN:-}"  # Optional: leave empty for IP-based access

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }
log_err() { echo -e "${RED}[✗]${NC} $1"; }

# ═══════════════════════════════════════════════════════════════════
# Pre-flight checks
# ═══════════════════════════════════════════════════════════════════

if [ "$EUID" -eq 0 ]; then
    log_err "Do not run as root. Run as ubuntu user with sudo access."
    exit 1
fi

log_info "Starting Soft Skills Platform deployment..."
log_info "Instance: $(hostname), User: $(whoami)"

# ═══════════════════════════════════════════════════════════════════
# 1. System Updates & Dependencies
# ═══════════════════════════════════════════════════════════════════

log_info "Step 1/9: Updating system packages..."
sudo apt update -qq
sudo apt upgrade -y -qq

log_info "Installing system dependencies..."
sudo DEBIAN_FRONTEND=noninteractive apt install -y \
    python3.11 python3.11-venv python3-pip \
    ffmpeg \
    nginx \
    git \
    build-essential \
    htop curl \
    software-properties-common

# Node.js 20
if ! command -v node &> /dev/null || [ "$(node -v | cut -d. -f1)" != "v20" ]; then
    log_info "Installing Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - > /dev/null
    sudo apt install -y nodejs
fi

log_ok "Dependencies installed"
log_info "Python: $(python3.11 --version)"
log_info "Node: $(node --version)"

# ═══════════════════════════════════════════════════════════════════
# 2. Increase Swap (Helps builds on smaller instances)
# ═══════════════════════════════════════════════════════════════════

if [ ! -f /swapfile ]; then
    log_info "Step 2/9: Setting up 2GB swap file..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile > /dev/null
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null
    log_ok "Swap enabled"
else
    log_ok "Swap already configured"
fi

# ═══════════════════════════════════════════════════════════════════
# 3. Clone Repository
# ═══════════════════════════════════════════════════════════════════

if [ ! -d "$APP_DIR" ]; then
    log_info "Step 3/9: Cloning repository..."
    git clone "$REPO_URL" "$APP_DIR"
else
    log_info "Step 3/9: Repository exists, pulling latest..."
    cd "$APP_DIR" && git pull
fi
cd "$APP_DIR"
log_ok "Code ready at $APP_DIR"

# ═══════════════════════════════════════════════════════════════════
# 4. Python Virtual Environment + Dependencies
# ═══════════════════════════════════════════════════════════════════

log_info "Step 4/9: Setting up Python environment..."
cd "$APP_DIR"

if [ ! -d "venv" ]; then
    python3.11 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip --quiet

log_info "Installing Python dependencies (may take 5-10 min)..."
pip install --no-cache-dir -r requirements.txt --quiet

log_ok "Python environment ready"

# ═══════════════════════════════════════════════════════════════════
# 5. Frontend Build
# ═══════════════════════════════════════════════════════════════════

log_info "Step 5/9: Building frontend..."
cd "$APP_DIR/frontend"

if [ ! -d "node_modules" ]; then
    npm ci --silent
fi

npm run build --silent
log_ok "Frontend built to frontend/dist/"

# ═══════════════════════════════════════════════════════════════════
# 6. Setup ss3 Gesture Service
# ═══════════════════════════════════════════════════════════════════

log_info "Step 6/9: Setting up ss3 gesture service..."
cd "$APP_DIR/ss3"

if [ ! -d "venv-ss3" ]; then
    python3.11 -m venv venv-ss3
fi

source venv-ss3/bin/activate
pip install --upgrade pip --quiet
pip install --no-cache-dir -r requirements.txt --quiet
deactivate
log_ok "ss3 service ready"

# ═══════════════════════════════════════════════════════════════════
# 7. Environment Configuration
# ═══════════════════════════════════════════════════════════════════

log_info "Step 7/9: Checking environment configuration..."
cd "$APP_DIR"

if [ ! -f ".env" ]; then
    log_warn ".env file missing - creating template"
    cat > .env <<'EOF'
# EDIT THIS FILE - Add your API keys!

# Pronunciation provider (hf_phoneme = full, mock = lightweight)
PRONUNCIATION_PROVIDER=hf_phoneme
HF_PHONEME_MODEL_NAME=facebook/wav2vec2-lv-60-espeak-cv-ft

# Groq API (get free at https://console.groq.com/keys)
GROQ_API_KEY=

# Firebase (paste full JSON as single line)
FIREBASE_SERVICE_ACCOUNT_JSON=
AUTH_BYPASS=false

# Storage
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
TEMP_DIR=temp

# ss3 gesture service
CSA_SERVICE_URL=http://127.0.0.1:8001
CSA_DATA_DIR=/home/ubuntu/softskills/outputs/ss3
CSA_ANALYZE_TIMEOUT_SECONDS=180

# Teachers (comma-separated)
TEACHER_EMAILS=teacher@kiet.edu
EOF
    chmod 600 .env
    log_warn "IMPORTANT: Edit .env and add:"
    log_warn "  - GROQ_API_KEY"
    log_warn "  - FIREBASE_SERVICE_ACCOUNT_JSON"
    log_warn "  - TEACHER_EMAILS"
    log_warn "Run: nano .env"
    log_warn ""
    log_warn "After editing, re-run this script to finish setup"
    exit 1
fi

# Validate critical env vars
if grep -q "^GROQ_API_KEY=$" .env; then
    log_err "GROQ_API_KEY not set in .env"
    log_err "Get free key at: https://console.groq.com/keys"
    exit 1
fi

if grep -q "^FIREBASE_SERVICE_ACCOUNT_JSON=$" .env; then
    log_warn "FIREBASE_SERVICE_ACCOUNT_JSON empty - auth may fail"
fi

log_ok "Environment configured"

# ═══════════════════════════════════════════════════════════════════
# 8. Systemd Services
# ═══════════════════════════════════════════════════════════════════

log_info "Step 8/9: Setting up systemd services..."

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
sudo systemctl enable softskills-ss3 softskills-backend > /dev/null 2>&1
sudo systemctl restart softskills-ss3 softskills-backend

# Wait for services
sleep 5

if sudo systemctl is-active --quiet softskills-backend; then
    log_ok "Backend service running"
else
    log_err "Backend failed to start"
    sudo journalctl -u softskills-backend -n 20
    exit 1
fi

if sudo systemctl is-active --quiet softskills-ss3; then
    log_ok "ss3 service running"
else
    log_warn "ss3 failed to start (Interview Studio may not work)"
fi

# ═══════════════════════════════════════════════════════════════════
# 9. Nginx Reverse Proxy
# ═══════════════════════════════════════════════════════════════════

log_info "Step 9/9: Configuring Nginx..."

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

    # Everything else
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

if sudo nginx -t 2>&1 | grep -q "successful"; then
    sudo systemctl reload nginx
    log_ok "Nginx configured"
else
    log_err "Nginx config invalid"
    exit 1
fi

# ═══════════════════════════════════════════════════════════════════
# Verification
# ═══════════════════════════════════════════════════════════════════

log_info "Verifying deployment..."

PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "unknown")
sleep 3

if curl -sf http://localhost:8080/health > /dev/null; then
    log_ok "Backend health check passed"
else
    log_warn "Backend health check failed"
fi

# ═══════════════════════════════════════════════════════════════════
# Success!
# ═══════════════════════════════════════════════════════════════════

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              🎉 DEPLOYMENT COMPLETE! 🎉                        ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║                                                                 ║"
echo "║  App URL: http://$PUBLIC_IP                                     "
echo "║                                                                 ║"
echo "║  Next Steps:                                                    ║"
echo "║  1. Open Firebase Console                                       ║"
echo "║  2. Add authorized domain: $PUBLIC_IP                           "
echo "║  3. Test at: http://$PUBLIC_IP                                  "
echo "║                                                                 ║"
echo "║  Management Commands:                                           ║"
echo "║    View logs: sudo journalctl -u softskills-backend -f          ║"
echo "║    Restart:   sudo systemctl restart softskills-backend         ║"
echo "║    Status:    sudo systemctl status softskills-backend          ║"
echo "║                                                                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
