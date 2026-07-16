# Project Audit & Improvement Report

## 🗑️ Unwanted / Removable Items

### High Priority Removals

| Item | Size | Reason |
|------|------|--------|
| `video-feature/` | ~50MB+ | Separate old project, not integrated |
| `speedometer/` | ~30MB+ | Old prototype, superseded by main app |
| `.hypothesis/` | 8.5MB | Test cache, regeneratable |
| `.pytest_cache/` | small | Test cache, regeneratable |
| `uploads/` | 120 files | Old audio uploads, can archive |
| `temp/` | 44 files | Temporary files |

### Duplicate Convert Scripts

Multiple markdown-to-PDF converters (redundant):
- `convert_md_to_html.py`
- `convert_md_to_pdf.py`
- `convert_to_pdf_simple.py`
- `convert_to_pdf.py`

**Recommendation:** Keep only `convert_md_to_html.py`, delete rest.

### Duplicate Docker Files

- `Dockerfile` (main)
- `Dockerfile.fly` (Fly.io)
- `docker-compose.yml`
- `docker-compose.https.yml`

**Recommendation:** Keep `Dockerfile.fly` (production) + `docker-compose.yml` (dev). Others can go.

### Duplicate Deployment Docs

- `DEPLOY_FLY.md` ✅ (keep - current)
- `DEPLOYMENT.md` ❌ (old)
- `LAPTOP_BACKEND_VERCEL_FRONTEND.md` ❌ (outdated approach)
- `FREE_PRONUNCIATION_ARCHITECTURE.md` ❌ (implemented)
- `TEAM_SPLIT.md` ❌ (planning doc, no longer needed)
- `ROADMAP.md` ⚠️ (review if needed)

---

## 🐛 Code Improvements Needed

### 1. Debate Bug Fixes (Applied ✅)

- ✅ "Submit early" 2nd user bug - FIXED
- ✅ 4-6 people join issue - FIXED with grace period
- ✅ Content scoring - ADDED

### 2. Remaining Issues in Debate

**Issue A: Turn recording auto-start**  
Location: `frontend/src/components/DebateArenaView.tsx`
- Race condition potential when audioBlob check
- Fix: Already applied recorder.reset() before start

**Issue B: WebSocket reconnect on network hiccup**  
- Current: Exponential backoff works
- Improvement: Add heartbeat/ping every 30s

### 3. Group Discussion Improvements Needed

**Missing Features:**
1. **Speaker diarization** - Currently trusts client (user could fake speech times)
2. **Voice activity detection** - Auto-detect silence
3. **Interruption etiquette** - Warn user when others speaking
4. **My-sessions history UI** - Endpoint exists but no frontend

**UX Improvements:**
1. Show remaining time for each speech (max 90s)
2. Better visualization of who spoke when (timeline)
3. "Raise hand" indicator before speaking

### 4. Backend Architecture

**Issues:**
- ❌ In-memory rooms → lost on restart (fly.io redeploy = lost state)
- ❌ No admin panel for GD (only debate has it)
- ❌ Whisper model loaded per request (slow)

**Improvements:**
- ✅ Add Redis for room state (optional, for production scale)
- ✅ Preload Whisper model on startup
- ✅ Add GD admin panel

### 5. Security & Auth

**Issues:**
- ⚠️ `AUTH_BYPASS=false` in .env but no rate limiting
- ⚠️ Firebase JSON in repo (needs .gitignore check)

**Improvements:**
- Add rate limiting (slowapi or fastapi-limiter)
- Add request ID logging
- Add error tracking (Sentry free tier)

---

## 🎯 Performance Improvements

### Backend

| Issue | Current | Fix |
|-------|---------|-----|
| Whisper load time | Per request | Preload on startup |
| JSONL scan | Full file read | Add indexing |
| CORS | Wildcard | Explicit domains |
| Static files | Not cached | Add cache headers |

### Frontend

| Issue | Current | Fix |
|-------|---------|-----|
| Bundle size | Not measured | Add build analyzer |
| Image assets | Full size | WebP/optimization |
| Code splitting | None | React.lazy for routes |

---

## 📁 Recommended Cleanup Actions

### Immediate (Safe)

```powershell
# Delete unwanted folders
Remove-Item -Recurse -Force video-feature
Remove-Item -Recurse -Force speedometer
Remove-Item -Recurse -Force .hypothesis
Remove-Item -Recurse -Force .pytest_cache

# Delete old PDF converters (keep only one)
Remove-Item convert_md_to_pdf.py
Remove-Item convert_to_pdf_simple.py
Remove-Item convert_to_pdf.py

# Delete outdated docs
Remove-Item DEPLOYMENT.md
Remove-Item LAPTOP_BACKEND_VERCEL_FRONTEND.md
Remove-Item FREE_PRONUNCIATION_ARCHITECTURE.md
Remove-Item TEAM_SPLIT.md
```

### Review Before Delete

```powershell
# These need review first:
# uploads/ - contains user audio (backup first)
# temp/ - transient files
# outputs/ - production data (keep!)
# ROADMAP.md - planning doc
# Caddyfile - reverse proxy config
```

### Update .gitignore

Add these if missing:
```
.hypothesis/
.pytest_cache/
uploads/
temp/
outputs/
venv/
node_modules/
dist/
.firebase-admin.json
.env
```

---

## 🚀 Feature Additions Recommended

### 1. Analytics Dashboard
- Weekly usage stats
- Popular features
- Score distributions
- Student progress tracking

### 2. Practice Modes for GD
- Solo practice against AI participants
- Recorded sessions replay
- Detailed feedback per contribution

### 3. Notifications
- Email results after GD/Debate
- Weekly progress report
- Teacher notifications

### 4. Better Onboarding
- Tutorial mode for first-time users
- Sample debates/GDs to watch
- Practice topics

---

## 💰 Deployment Cost Optimization

### Current: Fly.io ($5-15/month)

**Optimizations:**
1. Enable auto-stop when idle (save 70% cost)
2. Use HuggingFace Inference API instead of local models
3. Store audio in S3-compatible (Cloudflare R2 free tier)
4. Move JSONL → Supabase free tier (500MB)

### Groq API (FREE)
✅ Already integrated for content scoring

### Estimated Savings
- Current: ~$15/month
- Optimized: ~$5/month or FREE (with limits)

---

## 📊 Priority Matrix

| Task | Priority | Effort | Impact |
|------|----------|--------|--------|
| Delete unwanted files | HIGH | LOW | HIGH |
| Fix .gitignore | HIGH | LOW | HIGH |
| Preload Whisper | MEDIUM | LOW | MEDIUM |
| Add rate limiting | HIGH | MEDIUM | HIGH |
| GD Admin Panel | MEDIUM | HIGH | MEDIUM |
| Analytics Dashboard | LOW | HIGH | LOW |
| Speaker Diarization | LOW | HIGH | HIGH |
