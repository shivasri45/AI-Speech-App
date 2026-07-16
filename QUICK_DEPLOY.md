# 🚀 Quick Deploy Guide - AWS EC2

**Total Time:** 30 minutes | **Cost:** $37/month or free with credits

## Prerequisites Checklist

- [ ] AWS account with $100 credits activated
- [ ] Groq API key from https://console.groq.com/keys
- [ ] Firebase project setup (already done)
- [ ] Repository pushed to GitHub

## Part 1: Launch EC2 Instance (5 min)

### Step 1: Login to AWS Console
Go to https://console.aws.amazon.com

### Step 2: Launch Instance
```
EC2 → Launch Instance
```

**Configuration:**
```
Name: softskills-kiet
AMI: Ubuntu Server 22.04 LTS (64-bit x86)
Instance type: t3.medium ⭐
Key pair: Create new "softskills-key" (download .pem)
Network settings: 
  - VPC: Default
  - Auto-assign public IP: Enable
  - Security group: Create new "softskills-sg"
    - Allow SSH (22) from My IP
    - Allow HTTP (80) from Anywhere
    - Allow HTTPS (443) from Anywhere
Storage: 30 GB gp3
```

Click **Launch Instance**.

### Step 3: Wait for Running (30 sec)

Note down the **Public IPv4 address** - example: `3.109.45.123`

## Part 2: Deploy Application (25 min)

### Step 4: SSH into Instance

**Windows (PowerShell):**
```powershell
# Move key to safer location
Move-Item ~/Downloads/softskills-key.pem ~/.ssh/

# Fix permissions
icacls ~/.ssh/softskills-key.pem /reset
icacls ~/.ssh/softskills-key.pem /grant:r "$env:USERNAME:(R)"
icacls ~/.ssh/softskills-key.pem /inheritance:r

# Connect
ssh -i ~/.ssh/softskills-key.pem ubuntu@YOUR_IP
```

### Step 5: Run Deploy Script

**On EC2 instance (SSH session):**
```bash
# Set your repo URL (or push code first)
export REPO_URL="https://github.com/YOUR_USERNAME/softskills2.git"

# Clone and run deploy
git clone $REPO_URL softskills
cd softskills
bash scripts/deploy.sh
```

**The script will:**
1. ✅ Install all dependencies (Python 3.11, Node 20, ffmpeg, nginx)
2. ✅ Add 2GB swap for larger builds
3. ✅ Set up virtual environment
4. ✅ Install Python packages
5. ✅ Build React frontend
6. ✅ Setup ss3 gesture service
7. ⏸️ **Pause for .env configuration** (see next step)

### Step 6: Configure Environment

When script pauses for .env, edit it:
```bash
nano .env
```

**Fill in these:**
```env
GROQ_API_KEY=gsk_YourGroqKeyHere

FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}

TEACHER_EMAILS=your.email@kiet.edu
```

Save (Ctrl+X, Y, Enter), then re-run:
```bash
bash scripts/deploy.sh
```

Script continues:
7. ✅ Configure systemd services
8. ✅ Setup Nginx reverse proxy
9. ✅ Verify deployment

### Step 7: Add Firebase Authorized Domain

Firebase Console → Authentication → Settings → Authorized Domains

Add:
```
YOUR_EC2_IP
YOUR_EC2_IP.compute.amazonaws.com
```

### Step 8: Test It!

Open browser: `http://YOUR_EC2_IP`

Login with your Google account. Try all features!

## Part 3: Cost Management

### Save Money - Stop When Not Testing

**Option A: AWS Console**
```
EC2 → Instances → Select → Instance state → Stop
```

**Option B: AWS CLI (from your PC)**
```powershell
# One-time setup
aws configure

# Stop
aws ec2 stop-instances --instance-ids i-YOUR_ID

# Start later
aws ec2 start-instances --instance-ids i-YOUR_ID
```

### Get New IP After Restart

Every time you stop/start, the public IP changes:
```powershell
aws ec2 describe-instances --instance-ids i-YOUR_ID --query "Reservations[].Instances[].PublicIpAddress" --output text
```

**Update Firebase authorized domains** with new IP.

### Optional: Elastic IP (Static IP)

Prevents IP changes ($3.60/mo when instance is stopped):
```
EC2 → Elastic IPs → Allocate → Associate with instance
```

## Part 4: Team Sharing

Send your team:
```
URL: http://YOUR_EC2_IP
Login: Sign in with Google (@kiet.edu email)
Features: 
  - Pronunciation practice
  - 1v1 Battle
  - Group Debate
  - Group Discussion (PTT)
  - Voice Cruise Control
  - Interview Studio
```

## Troubleshooting

### App not loading
```bash
sudo systemctl status softskills-backend
sudo journalctl -u softskills-backend -n 50
```

### Google Sign-In fails
- Check Firebase authorized domains includes your IP
- Hard refresh browser (Ctrl+Shift+R)

### Out of memory
```bash
free -h  # Check memory
htop     # Watch usage
sudo systemctl restart softskills-backend  # Restart if leak
```

### Update deployment
```bash
cd ~/softskills
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
cd frontend && npm ci && npm run build && cd ..
sudo systemctl restart softskills-backend softskills-ss3
```

## Cost Breakdown ($100 Budget)

| Scenario | Monthly | Duration |
|----------|---------|----------|
| 24/7 | $37 | 2.7 months |
| 12 hrs/day | $19 | 5.3 months |
| Weekends only | $12 | 8.3 months |
| **8 hrs/day weekdays** | **$8** | **12.5 months** |

**Recommended:** Start instance when testing/demo, stop when done.

## What You Get

✅ All 8 features working  
✅ Interview Studio with gesture analysis  
✅ Group Debate with content scoring  
✅ Group Discussion with PTT  
✅ Full admin panel with CSV exports  
✅ Real-time WebSockets  
✅ Firebase Auth  
✅ Nginx reverse proxy  
✅ Auto-restart on failure  

---

**Ready?** Follow the steps above in order. Total time: ~30 minutes.
