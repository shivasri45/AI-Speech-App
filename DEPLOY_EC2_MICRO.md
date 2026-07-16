# Deploy on AWS EC2 t3.micro (1 GB RAM)

Yes! Works on t3.micro with cloud-first configuration. Uses Groq API for AI
services instead of local models, keeping RAM under 500MB.

## Total Cost

- **EC2 t3.micro:** FREE (12 months) or ~$8.50/mo after
- **EBS 20GB:** ~$2/mo
- **Groq API:** FREE (20K seconds/day)
- **Firebase:** FREE (Spark tier)
- **Total:** $0-10/mo

## What Works vs What's Disabled

| Feature | Status | Notes |
|---------|--------|-------|
| Pronunciation Practice | ✅ Works | Uses Groq Whisper |
| 1v1 Battle | ✅ Works | Groq ASR |
| Group Debate | ✅ Works | Groq ASR + LLM |
| Group Discussion | ✅ Works | Groq ASR + LLM |
| Voice Cruise Control | ✅ Works | Browser-only WPM |
| Admin Panel | ✅ Works | Full functionality |
| Interview Studio | ❌ Disabled | Needs MediaPipe (too heavy) |

## Setup on EC2 t3.micro

### 1. Launch Instance

```
AMI: Ubuntu 22.04 LTS
Instance: t3.micro (1 vCPU, 1 GB RAM)
Storage: 20 GB gp3
Security Group:
  - SSH (22) from your IP
  - HTTP (80) from anywhere
  - HTTPS (443) from anywhere
  - Custom TCP (8080) from anywhere (or use nginx)
```

### 2. SSH and Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y

# Python 3.11
sudo apt install -y python3.11 python3.11-venv python3-pip

# ffmpeg (audio processing)
sudo apt install -y ffmpeg

# Node.js 20 (for frontend build)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Nginx (reverse proxy)
sudo apt install -y nginx

# Git
sudo apt install -y git

# Increase swap (helps with builds)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 3. Clone and Setup

```bash
cd /home/ubuntu
git clone <your-repo-url> softskills
cd softskills

# Backend setup
python3.11 -m venv venv
source venv/bin/activate

# Install minimal requirements (no torch/whisper local!)
pip install --no-cache-dir \
    fastapi uvicorn python-multipart \
    firebase-admin pydantic \
    httpx python-dotenv \
    numpy scipy pydub

# Skip these heavy packages:
# - torch (700MB)
# - openai-whisper (large)
# - transformers (Wav2Vec2)
# - mediapipe (ss3)

# Frontend build
cd frontend
npm ci --production=false
npm run build
cd ..
```

### 4. Configure Environment

```bash
cat > .env <<'EOF'
# Disable heavy features
PRONUNCIATION_PROVIDER=mock
INTERVIEW_STUDIO_ENABLED=false

# Groq for ASR + LLM (FREE)
GROQ_API_KEY=gsk_your_key_here

# Firebase
FIREBASE_SERVICE_ACCOUNT_JSON=<paste-json-here>
AUTH_BYPASS=false

# Storage
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs

# Teachers
TEACHER_EMAILS=teacher@kiet.edu
EOF
```

### 5. Systemd Service

```bash
sudo tee /etc/systemd/system/softskills.service > /dev/null <<'EOF'
[Unit]
Description=Soft Skills FastAPI Backend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/softskills
Environment="PATH=/home/ubuntu/softskills/venv/bin"
ExecStart=/home/ubuntu/softskills/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable softskills
sudo systemctl start softskills
sudo systemctl status softskills
```

### 6. Nginx Reverse Proxy

```bash
sudo tee /etc/nginx/sites-available/softskills > /dev/null <<'EOF'
server {
    listen 80;
    server_name _;
    client_max_body_size 20M;

    # WebSocket support for battles/debates/GD
    location ~ ^/(gd|debate|battle)/ws/ {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/softskills /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. HTTPS with Let's Encrypt (Optional)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 8. Firebase Console

Add domain to authorized:
- `your-ec2-public-ip.compute.amazonaws.com`
- OR your custom domain

## Memory Optimization Tips

### Reduce Python Memory

```python
# In app/main.py - Add these
import gc
import os

# Limit worker memory
os.environ["PYTHONHASHSEED"] = "0"

# Aggressive GC
gc.set_threshold(700, 10, 10)
```

### Uvicorn Config

```bash
# Use only 1 worker on t3.micro
uvicorn app.main:app --workers 1 --limit-max-requests 1000
```

### Monitor Memory

```bash
# Check memory usage
free -h
htop  # Install: sudo apt install htop
```

## Performance Expectations

**Concurrent Users:** 20-30 comfortable, 50 max  
**Response Time:**
- Groq Whisper: ~500ms
- Groq LLM: ~1s
- Everything else: < 200ms

**Bottlenecks on t3.micro:**
1. CPU credits (burstable) - watch out during peaks
2. Network bandwidth
3. Disk I/O for JSONL

## Scaling Beyond t3.micro

If you outgrow:
- **t3.small** (2GB): $17/mo, can enable local Whisper
- **t3.medium** (4GB): $34/mo, full features + Interview Studio
- **RDS PostgreSQL free tier**: Replace JSONL storage
- **CloudFront CDN**: For frontend static files

## Troubleshooting

**"Out of memory" during pip install:**
- Use `pip install --no-cache-dir`
- Install packages one at a time
- Add more swap: `sudo fallocate -l 4G /swapfile2`

**"Service won't start":**
- `sudo journalctl -u softskills -n 100`
- Check `.env` file exists
- Verify Groq API key is valid

**High memory usage:**
- `top -o %MEM` to see culprits
- Check if Whisper accidentally loaded locally
- Ensure `PRONUNCIATION_PROVIDER=mock`
