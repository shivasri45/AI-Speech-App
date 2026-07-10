# Quick Demo Setup: Laptop Backend + Vercel Frontend

**Best for:** 1-2 week team demo jahan tumhara laptop available hai demo time pe.

**Total time:** ~15 minutes setup

---

## Part 1: Backend on Laptop (with ngrok tunnel)

### 1. Start backend locally

```powershell
cd c:\Users\avira\Projects\softskills2

# Activate virtual environment if you have one
# .venv\Scripts\Activate.ps1

# Start FastAPI backend
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Backend runs on `http://localhost:8080`

### 2. Start ss3 microservice (separate terminal)

```powershell
cd c:\Users\avira\Projects\softskills2\ss3

# Start ss3 on port 8001 (Interview Studio needs this)
python -m backend.main
```

ss3 runs on `http://localhost:8001`

### 3. Create ngrok tunnel (separate terminal)

**Install ngrok (one-time):**
```powershell
winget install ngrok
# OR download from https://ngrok.com/download
```

**Start tunnel:**
```powershell
ngrok http 8080
```

Output me dikhega:
```
Forwarding   https://abc123.ngrok-free.app -> http://localhost:8080
```

**Copy the HTTPS URL** (`https://abc123.ngrok-free.app`) — yeh tumhara public backend URL hai.

**IMPORTANT:** Free ngrok URLs change every time you restart ngrok. Agar stable URL chahiye:
- Sign up at https://ngrok.com (free tier)
- Get your authtoken: `ngrok config add-authtoken <your-token>`
- Use a reserved domain (paid) OR accept that URL changes on every restart

---

## Part 2: Frontend on Vercel

### 1. Update frontend config to point to ngrok backend

Create `frontend/.env.production.local`:

```bash
# Point Vite build to your ngrok backend URL
VITE_API_URL=https://abc123.ngrok-free.app

# Keep existing Firebase config
VITE_AUTH_BYPASS=false
VITE_FIREBASE_API_KEY=AIzaSyBdaN8xxmT8pq-JftL08UfXeDMdKJmYoyk
VITE_FIREBASE_AUTH_DOMAIN=kiet-softskills.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=kiet-softskills
VITE_FIREBASE_STORAGE_BUCKET=kiet-softskills.firebasestorage.app
VITE_FIREBASE_MESSAGING_SENDER_ID=63966974230
VITE_FIREBASE_APP_ID=1:63966974230:web:b12460152adcb2115e0037
```

Replace `https://abc123.ngrok-free.app` with your actual ngrok URL.

### 2. Enable CORS in backend

Backend ko ngrok + Vercel domains allow karni hogi.

Edit `app/main.py`, add CORS middleware **before** `app.include_router(router)`:

```python
from fastapi.middleware.cors import CORSMiddleware

# ... existing code ...

# Add after app = FastAPI(...) and before app.include_router(router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local Vite dev
        "https://*.vercel.app",   # Vercel preview + production
        "https://*.ngrok-free.app",  # ngrok tunnel
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Restart backend (Ctrl+C in terminal 1, then `uvicorn app.main:app --host 0.0.0.0 --port 8080` again).

### 3. Deploy frontend to Vercel

**Install Vercel CLI (one-time):**
```powershell
npm install -g vercel
```

**Deploy:**
```powershell
cd frontend
vercel --prod
```

Prompts:
- "Set up and deploy?" → **Y**
- "Which scope?" → Pick your account
- "Link to existing project?" → **N**
- "What's your project name?" → `kiet-softskills` (or kuch bhi)
- "In which directory is your code?" → **./** (current dir)
- "Want to override settings?" → **N**

Vercel builds (`npm run build`) aur deploy karega. Output me final URL dikhega:
```
✅ Production: https://kiet-softskills.vercel.app
```

### 4. Add Vercel domain to Firebase Authorized Domains

Go to https://console.firebase.google.com → your project → **Authentication → Settings → Authorized domains → Add domain**

Add: `kiet-softskills.vercel.app` (no `https://`)

---

## Part 3: Test

1. Open `https://kiet-softskills.vercel.app` in browser
2. Sign in with `@kiet.edu` Google account
3. Try Pronunciation practice — audio upload goes to ngrok → laptop backend
4. Try Battle / Debate — WebSocket connects to ngrok → laptop backend

**Tumhara laptop must be running with ngrok tunnel active jab bhi team try kare.**

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Vercel frontend loads, but API calls fail | Check CORS middleware in `app/main.py`, restart backend |
| `ERR_CONNECTION_REFUSED` | Backend ya ngrok band hai — dono running check karo |
| `auth/unauthorized-domain` | Vercel domain Firebase Console me add nahi kiya |
| Interview Studio hangs | ss3 microservice (terminal 2) band hai — restart karo |
| Debate room disconnects | ngrok free tier ke saath occasionally timeouts — upgrade to paid ($8/month for stable domain) |
| WebSocket fails after 1 hour | ngrok free tier 1-hour session limit — restart ngrok |

---

## Cost

- **Vercel frontend:** $0 (free tier)
- **ngrok free tier:** $0 (but unstable URL + 1-hour sessions)
- **ngrok paid (optional):** $8/month (stable domain, no timeouts)

**Total: $0-8/month** vs Fly.io's $6-8/month for full deployment.

---

## Limitations

1. **Laptop must stay on + connected** during demo time
2. **ngrok URL changes on restart** (free tier) — Vercel redeploy needed
3. **No uptime if laptop sleeps** — team can't access 24/7
4. **Electricity + internet** tumhare laptop pe

---

## When to move to Fly.io

Agar yeh setup kaam kar gaya aur team happy hai, **proper deployment ke liye Fly.io migrate karo** taaki:
- Laptop dependency khatam ho
- 24/7 uptime mile
- Stable URLs rahe

Migration: Just run `flyctl deploy` — deployment docs already ready hain (`DEPLOY_FLY.md`).

---

**Ready to start?** Run the 3 terminals (backend, ss3, ngrok), then deploy frontend to Vercel.
