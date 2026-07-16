# Optimal AWS Deployment - t3.medium

Recommended setup for the full KIET Soft Skills Platform with all features
including Interview Studio, using AWS free credits.

## Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│  Route 53 (DNS) → CloudFront (CDN, optional)               │
│         ↓                                                    │
│  EC2 t3.medium (Ubuntu 22.04)                              │
│  ├── Nginx (reverse proxy + SSL)                           │
│  ├── FastAPI backend (port 8080)                           │
│  ├── ss3 gesture service (port 8001)                       │
│  └── Frontend static files                                 │
│         ↓                                                    │
│  EBS gp3 30GB (models + data)                              │
│                                                              │
│  External Services:                                          │
│  ├── Firebase Auth (FREE)                                   │
│  ├── Groq API (FREE - ASR + LLM)                            │
│  └── S3 (optional, for audio backups)                       │
└────────────────────────────────────────────────────────────┘
```

## Total Monthly Cost

| Item | Cost |
|------|------|
| EC2 t3.medium (24/7) | $34 |
| EBS gp3 30GB | $2.40 |
| Elastic IP (in use) | $0 (free when attached) |
| Data transfer (out) | $1-5 |
| **Total** | **~$40/month** |

**With AWS credits:** ~$40 usage/month = 25 months on $1000 credits

## Prerequisites

1. AWS account with free credits activated
2. Domain (optional, can use EC2 public DNS)
3. Firebase project setup
4. Groq API key

## Step-by-Step Setup

### 1. Launch EC2 Instance

**AWS Console → EC2 → Launch Instance**

```
Name: softskills-kiet-prod
AMI: Ubuntu Server 22.04 LTS (ami-0c7217cdde317cfec)
Instance type: t3.medium
Key pair: Create new or use existing
Network:
  - VPC: Default
  - Subnet: Any AZ (ap-south-1a recommended for India)
  - Auto-assign public IP: Enable
Security group:
  - SSH (22) - Your IP only
  - HTTP (80) - 0.0.0.0/0
  - HTTPS (443) - 0.0.0.0/0
Storage:
  - 30 GB gp3 (root)
  - IOPS: 3000
```

### 2. Elastic IP (Recommended)

Attach an Elastic IP so the address doesn't change on restart:
```
EC2 → Elastic IPs → Allocate → Associate with instance
```

### 3. Connect and Setup

```bash
ssh -i your-key.pem ubuntu@your-elastic-ip

# System updates
sudo apt update && sudo apt upgrade -y

# Essential packages
sudo apt install -y \
    python3.11 python3.11-venv python3-pip \
    ffmpeg \
    nginx \
    git \
    build-essential \
    htop \
    curl

# Node.js 20 for frontend
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
python3.11 --version  # Should be 3.11.x
node --version        # Should be 20.x
ffmpeg -version       # Should show ffmpeg
```

### 4. Clone Repository

```bash
cd /home/ubuntu
git clone <your-repo-url> softskills
cd softskills
```

### 5. Backend Setup

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install FULL requirements (all features)
pip install --upgrade pip
pip install -r requirements.txt

# This includes:
# - torch, whisper (local backup)
# - transformers (Wav2Vec2)
# - mediapipe (ss3)
# Total: ~2GB in venv
```

### 6. Configure Environment

```bash
cat > .env <<'EOF'
# Enable all features
PRONUNCIATION_PROVIDER=hf_phoneme
HF_PHONEME_MODEL_NAME=facebook/wav2vec2-lv-60-espeak-cv-ft

# Cloud AI (10x faster than local)
GROQ_API_KEY=gsk_your_key_here

# Firebase Auth
FIREBASE_SERVICE_ACCOUNT_JSON=<paste-full-json-here>
AUTH_BYPASS=false

# Storage paths
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
TEMP_DIR=temp

# ss3 gesture service
CSA_SERVICE_URL=http://127.0.0.1:8001
CSA_DATA_DIR=/home/ubuntu/softskills/outputs/ss3
CSA_ANALYZE_TIMEOUT_SECONDS=180

# Teachers
TEACHER_EMAILS=teacher1@kiet.edu,teacher2@kiet.edu
EOF

chmod 600 .env
```

### 7. Build Frontend

```bash
cd frontend
npm ci
npm run build
cd ..

# Frontend built to frontend/dist/
```

### 8. Setup ss3 Gesture Service

```bash
cd ss3
python3.11 -m venv venv-ss3
source venv-ss3/bin/activate
pip install -r requirements.txt
deactivate
cd ..
```

### 9. Systemd Services

**Backend service:**
```bash
sudo tee /etc/systemd/system/softskills-backend.service > /dev/null <<'EOF'
[Unit]
Description=Soft Skills FastAPI Backend
After=network.target softskills-ss3.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/softskills
Environment="PATH=/home/ubuntu/softskills/venv/bin"
ExecStart=/home/ubuntu/softskills/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

**ss3 gesture service:**
```bash
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

[Install]
WantedBy=multi-user.target
EOF
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable softskills-ss3 softskills-backend
sudo systemctl start softskills-ss3 softskills-backend

# Check status
sudo systemctl status softskills-backend
sudo systemctl status softskills-ss3
```

### 10. Nginx Reverse Proxy

```bash
sudo tee /etc/nginx/sites-available/softskills > /dev/null <<'EOF'
# Increase body size for audio/video uploads
client_max_body_size 50M;

server {
    listen 80;
    server_name _;

    # WebSocket routes for real-time features
    location ~ ^/(gd|debate|battle)/ws/ {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # API and static files
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
}
EOF

sudo ln -sf /etc/nginx/sites-available/softskills /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 11. HTTPS with Let's Encrypt

```bash
# Only if you have a domain
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 12. Firebase Console Setup

Add your domain to authorized:
- `yourdomain.com`
- `www.yourdomain.com`
- OR `your-elastic-ip.compute.amazonaws.com`

### 13. Verify Deployment

```bash
# Check services
sudo systemctl status softskills-backend
sudo systemctl status softskills-ss3
sudo systemctl status nginx

# Test endpoints
curl http://localhost:8080/health
curl http://localhost:8001/modules  # ss3

# Test from browser
open https://yourdomain.com
```

## Monitoring & Maintenance

### Check Logs

```bash
# Backend logs
sudo journalctl -u softskills-backend -f

# ss3 logs
sudo journalctl -u softskills-ss3 -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Monitor Resources

```bash
htop  # CPU + RAM
df -h # Disk usage
free -h # Memory
```

### CloudWatch (Free tier: 10 alarms + 1M API requests)

Setup basic alarms:
- CPU > 80% for 5 min
- Memory > 90%
- Disk > 80%

### Update Deployment

```bash
cd /home/ubuntu/softskills
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
cd frontend && npm ci && npm run build && cd ..
sudo systemctl restart softskills-backend softskills-ss3
```

## Performance Tuning

### On t3.medium with all features

**Expected metrics:**
- Response time: 200-500ms (with Groq)
- Concurrent users: 50-100 comfortable
- CPU usage: 20-40% average, bursts to 80%
- RAM usage: 2.5-3.5 GB / 4 GB
- Disk usage: 5-10 GB total

### Optimizations Applied

1. **2 uvicorn workers** - Utilize both vCPUs
2. **Nginx gzip** - Reduce bandwidth
3. **Static file caching** - Frontend cached
4. **WebSocket keep-alive** - Reduce reconnections
5. **Groq API** - Skip local model inference

## Scaling Path

### When to scale up:

**Signs you need t3.large ($67/mo):**
- Sustained >70% CPU
- >100 concurrent users
- Memory pressure warnings

**Signs you need multiple instances:**
- >200 concurrent users
- Cross-region users needing low latency
- High availability requirement

### Migration Path

```
t3.medium (start)
    ↓ (>100 users)
t3.large (single big instance)
    ↓ (>200 users, need HA)
2x t3.medium behind ALB
    ↓ (>500 users)
Auto-scaling group + RDS
```

## Backup Strategy

### Daily EBS Snapshots

```bash
# AWS Console → EC2 → EBS Volumes → Actions → Create Snapshot
# Or via AWS CLI:
aws ec2 create-snapshot --volume-id vol-xxx --description "Daily backup"
```

### Sync to S3 (Optional)

```bash
sudo apt install -y awscli
aws configure

# Cron job: daily backup outputs to S3
sudo crontab -e
# Add:
0 2 * * * aws s3 sync /home/ubuntu/softskills/outputs s3://softskills-backup/outputs/
```

## Security Checklist

- ✅ SSH only from your IP (Security Group)
- ✅ HTTPS enabled (Let's Encrypt)
- ✅ .env file permissions 600
- ✅ Firebase Auth on all API endpoints
- ✅ Rate limiting active
- ✅ Nginx client_max_body_size limit
- ✅ Regular system updates: `sudo apt update && sudo apt upgrade`
- ⚠️ Setup automatic security updates:
  ```bash
  sudo apt install unattended-upgrades
  sudo dpkg-reconfigure -plow unattended-upgrades
  ```

## Cost Optimization Tips

### Stop instance when not in use

```bash
# Weekend/night shutdown (saves ~50%)
aws ec2 stop-instances --instance-ids i-xxx

# Start again
aws ec2 start-instances --instance-ids i-xxx
```

### Use Savings Plans

If committing to 1 year: ~40% discount on t3.medium
- Regular: $34/mo
- 1-year savings plan: ~$20/mo

### Alternative: Fly.io

If AWS credits run out, Fly.io is cheaper:
- Fly.io: $5-15/mo
- Simpler deployment
- Free Postgres, Redis
