# KIET Soft Skills Platform - Complete Project Context

## Executive Summary

KIET Soft Skills Platform ek comprehensive speech training application hai jo students ki pronunciation, fluency, aur communication skills ko AI-powered feedback ke through improve karti hai. Platform me multiple practice modes hain including individual practice, 1v1 battles, group debates, voice cruise control, aur interview studio.

**Tech Stack:**
- **Backend:** Python 3.11+, FastAPI, Pydantic v2
- **Frontend:** React 18, TypeScript, Vite, TailwindCSS
- **AI/ML:** OpenAI Whisper (ASR), HuggingFace Wav2Vec2 (pronunciation), MediaPipe (gestures)
- **Auth:** Firebase Authentication (Google Sign-In, @kiet.edu restricted)
- **Storage:** JSONL files (no external DB), Local file storage
- **Deployment:** Fly.io (single container with backend + frontend + ss3)

---

## Project Structure

```
softskills2/
├── app/                          # FastAPI Backend
│   ├── main.py                   # App entry point
│   ├── api/                      # Core API routes
│   │   ├── analysis_routes.py    # Main /analyze endpoint
│   │   ├── health_routes.py
│   │   └── routes.py
│   ├── admin/                    # Teacher admin panel APIs
│   ├── asr/                      # Whisper ASR service
│   │   ├── whisper_service.py    # Transcription
│   │   └── schemas.py
│   ├── audio/                    # Audio handling
│   │   ├── preprocessing.py      # WAV conversion, normalization
│   │   ├── storage.py
│   │   └── schemas.py
│   ├── auth/                     # Firebase auth
│   │   ├── dependencies.py       # require_user, require_teacher
│   │   ├── firebase_admin.py
│   │   └── models.py
│   ├── battles/                  # 1v1 Battle mode
│   │   ├── room_manager.py       # WebSocket battle rooms
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── debate/                   # Group Debate mode (4-6 players)
│   │   ├── room_manager.py       # WebSocket debate rooms
│   │   ├── routes.py
│   │   ├── schemas.py
│   │   ├── service.py            # Turn analysis
│   │   └── scoring.py            # Winner computation
│   ├── fluency/                  # Fluency analysis
│   │   ├── service.py            # WPM, clarity score
│   │   └── schemas.py
│   ├── pronunciation/            # Pronunciation scoring
│   │   ├── service.py
│   │   ├── providers/
│   │   │   ├── hf_phoneme.py     # HuggingFace Wav2Vec2
│   │   │   ├── local.py
│   │   │   └── mock.py
│   │   └── acoustic/
│   ├── interview/                # Interview Studio
│   │   ├── routes.py
│   │   ├── service.py
│   │   └── schemas.py
│   ├── storage/                  # JSONL persistence
│   │   ├── _jsonl.py             # Base JSONL abstraction
│   │   ├── debates.py            # Debate records
│   │   └── debate_turns.py       # Turn records
│   ├── core/                     # Config, logging
│   │   ├── config.py
│   │   └── logging_helpers.py
│   └── data/                     # Static data files
│       ├── pronunciation_prompts.json
│       └── debate_motions.json
│
├── frontend/                     # React Frontend
│   ├── src/
│   │   ├── App.tsx               # Main app + view state machine
│   │   ├── main.tsx
│   │   ├── api.ts                # Pronunciation API client
│   │   ├── battleApi.ts          # Battle API client
│   │   ├── debateApi.ts          # Debate API client
│   │   ├── components/
│   │   │   ├── MainMenuView.tsx          # Home screen tiles
│   │   │   ├── PronunciationView.tsx     # Solo practice
│   │   │   ├── BattleArenaView.tsx       # 1v1 battles
│   │   │   ├── DebateArenaView.tsx       # Group debate
│   │   │   ├── VoiceCruiseView.tsx       # Voice speed control
│   │   │   ├── InterviewStudioView.tsx   # Interview practice
│   │   │   ├── AdminPanelView.tsx        # Teacher dashboard
│   │   │   └── admin/
│   │   │       ├── debates/
│   │   │       │   ├── PendingDebatesList.tsx
│   │   │       │   └── DebateReviewPanel.tsx
│   │   │       └── interviews/
│   │   └── hooks/
│   │       ├── useAuth.ts                # Firebase auth hook
│   │       ├── useAudioRecorder.ts       # MediaRecorder wrapper
│   │       ├── useBattleSocket.ts        # Battle WebSocket
│   │       └── useDebateSocket.ts        # Debate WebSocket
│   ├── .env.development
│   └── .env.production
│
├── ss3/                          # Gesture Analysis Microservice
│   └── backend/
│       ├── main.py
│       ├── routes_sessions.py
│       ├── modules/body_language/
│       └── feedback.py
│
├── tests/                        # Test suite
├── docker/                       # Docker configs
└── .kiro/specs/                  # Feature specifications
    └── group-debate/
        ├── requirements.md
        ├── design.md
        └── tasks.md
```

---

## Known Bug: "I am Done Speaking" Not Working for 2nd+ User

### Bug Description
Group Debate me pehle user ke turn submit hone ke baad, dusre user ka "Submit early" button click karne par kuch nahi hota. Recording chal rahi hoti hai, button enable dikhta hai, but click par response nahi milta.

### Root Cause Analysis

**File: `frontend/src/components/DebateArenaView.tsx`**

```typescript
// Line ~843 - handleManualStop function
const handleManualStop = useCallback(async () => {
  if (!recorder.isRecording || uploadingTurn) return;
  autoUploadRef.current = true;
  const blob = await recorder.stop();
  if (blob && blob.size > 0) {
    await handleUploadTurn(blob);
  }
}, [recorder, uploadingTurn, handleUploadTurn]);
```

**Problem Areas:**

1. **State Reset Issue (Line ~357-361):**
```typescript
// Clear per-turn state when the active turn changes
useEffect(() => {
  autoUploadRef.current = false;
  setUploadError(null);
  recorder.reset();  // <-- This may be resetting recorder prematurely
}, [state?.active_turn_index]);
```

2. **Auto-start Recording Condition (Line ~311-320):**
```typescript
useEffect(() => {
  if (!state) return;
  if (state.state !== "speaking") return;
  if (state.paused) return;
  if (!isMyTurn) return;
  if (recorder.isRecording) return;
  if (recorder.audioBlob) return;  // <-- May be stale from previous turn
  if (uploadingTurn) return;
  autoUploadRef.current = false;
  void recorder.start();
}, [state?.state, state?.paused, isMyTurn]);
```

3. **Possible Race Condition:**
   - Jab `active_turn_index` change hota hai, `recorder.reset()` call hota hai
   - Lekin agar broadcast late aaye, new speaker ki recording start nahi hoti
   - Ya phir `autoUploadRef` true reh jaata hai from previous attempt

### Suggested Fix

```typescript
// In useEffect for turn index change, ensure proper sequencing:
useEffect(() => {
  // Only reset if WE are NOT the new active speaker
  if (myParticipant && state?.active_turn_index !== myParticipant.turn_index) {
    autoUploadRef.current = false;
    setUploadError(null);
    setLastTurnResult(null);
    recorder.reset();
  }
}, [state?.active_turn_index, myParticipant]);

// Separate effect for starting recording
useEffect(() => {
  if (!state || state.state !== "speaking" || state.paused) return;
  if (!isMyTurn) return;
  if (recorder.isRecording || uploadingTurn) return;
  
  // Small delay to ensure state is settled
  const timer = setTimeout(() => {
    if (!recorder.isRecording && isMyTurn) {
      autoUploadRef.current = false;
      void recorder.start();
    }
  }, 100);
  
  return () => clearTimeout(timer);
}, [state?.state, state?.paused, isMyTurn, state?.active_turn_index]);
```

---

## Missing Feature: Content Scoring for Debates

### Current Scoring System

```python
# app/debate/service.py - compute_ai_score()
def compute_ai_score(pronunciation, fluency) -> tuple[float, bool]:
    """
    Current: avg(pronunciation.overall_score, fluency.clarity_score)
    Missing: Content/relevance scoring
    """
    pron = pronunciation.overall_score if pronunciation.available else None
    clarity = fluency.clarity_score
    
    if pron is not None and clarity is not None:
        return (pron + clarity) / 2.0, False
    if clarity is not None:
        return clarity, False
    return 0.0, True
```

### Proposed Content Scoring Integration

Content scoring ke liye local LLM integration needed hai:

```python
# NEW: app/debate/content_scoring.py

from typing import Optional
import httpx

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5-coder:7b"  # or "qwen2.5:7b" for general

async def score_content_relevance(
    transcript: str,
    motion_text: str,
    motion_title: str,
) -> tuple[float, str]:
    """
    Score how relevant the speaker's content is to the debate motion.
    
    Returns:
        (score 0-100, brief feedback)
    """
    prompt = f"""You are a debate judge. Score this speech's relevance to the motion.

Motion: {motion_title}
"{motion_text}"

Speaker's Transcript:
"{transcript}"

Rate the speech on these criteria (each 0-25 points):
1. Topic Relevance: Does it address the motion directly?
2. Argument Quality: Are points logical and supported?
3. Structure: Is there clear intro, body, conclusion?
4. Persuasiveness: How convincing is the argument?

Output format (JSON only):
{{"score": <total 0-100>, "feedback": "<one sentence>"}}
"""
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(OLLAMA_URL, json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
            })
            result = response.json()
            # Parse the response...
            return parse_llm_score(result["response"])
    except Exception as e:
        logger.warning(f"Content scoring failed: {e}")
        return None, "Content scoring unavailable"
```

### Updated AI Score Computation

```python
# Updated app/debate/service.py

async def compute_ai_score_with_content(
    pronunciation: PronunciationResult,
    fluency: FluencyResult,
    transcript: str,
    motion: Motion,
) -> tuple[float, bool, dict]:
    """
    Enhanced scoring with content analysis.
    
    Weights:
    - Pronunciation: 30%
    - Fluency: 30%
    - Content: 40%
    """
    pron_score = pronunciation.overall_score if pronunciation.available else None
    fluency_score = fluency.clarity_score
    
    # Get content score from local LLM
    content_score, content_feedback = await score_content_relevance(
        transcript=transcript,
        motion_text=motion.text,
        motion_title=motion.title,
    )
    
    scores = {
        "pronunciation": pron_score,
        "fluency": fluency_score,
        "content": content_score,
        "content_feedback": content_feedback,
    }
    
    # Calculate weighted average
    available_scores = []
    weights = []
    
    if pron_score is not None:
        available_scores.append(pron_score * 0.3)
        weights.append(0.3)
    if fluency_score is not None:
        available_scores.append(fluency_score * 0.3)
        weights.append(0.3)
    if content_score is not None:
        available_scores.append(content_score * 0.4)
        weights.append(0.4)
    
    if not available_scores:
        return 0.0, True, scores
    
    # Normalize weights
    total_weight = sum(weights)
    final_score = sum(available_scores) / total_weight * 100
    
    return round(final_score, 2), False, scores
```

---

## Group Debate State Machine

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   waiting ──────────► prep ──────────► speaking ──────────► scoring     │
│     │                  │                  │                    │        │
│     │   (all ready)    │   (60s timer)    │   (all turns)      │        │
│     │                  │                  │                    ▼        │
│     │                  │                  │               complete      │
│     │                  │                  │                             │
│     │                  ▼                  ▼                             │
│     │               [PAUSED OVERLAY - 30s reconnect grace]              │
│     │                  │                  │                             │
│     │                  ▼                  ▼                             │
│     └──────────────► abandoned ◄─────────────────────────────────┘      │
│                    (< 2 connected)                                      │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key State Transitions

| From | To | Trigger |
|------|----|---------|
| waiting | prep | All participants ready (min 4) |
| prep | speaking | 60 second timer expires |
| speaking | speaking | Turn submitted, next speaker |
| speaking | scoring | Last turn submitted |
| scoring | complete | All turns analyzed |
| any | paused | Participant disconnects |
| paused | previous | Participant reconnects (30s) |
| paused | abandoned | No reconnect + <2 remaining |

---

## WebSocket Protocol

### Server → Client Messages

```typescript
// State update (most common)
{
  type: "state",
  state: {
    code: "ABC123",
    state: "speaking",
    paused: false,
    motion: { id, title, text },
    participants: [
      {
        participant_id: "abc123",
        display_name: "Rahul",
        is_ready: true,
        turn_index: 0,
        is_forfeit: false
      }
    ],
    active_turn_index: 1,
    prep_deadline: null,
    turn_deadline: 1720000000.0,
    reconnect_deadline: null,
    winner_participant_id: null
  }
}

// Error message
{ type: "error", detail: "room_not_found" }

// Pong response
{ type: "pong" }
```

### Client → Server Messages

```typescript
// Only ping is accepted
{ type: "ping" }
```

---

## API Endpoints

### Debate Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /debate/rooms | Create new room |
| POST | /debate/rooms/{code}/join | Join existing room |
| POST | /debate/rooms/{code}/ready | Toggle ready status |
| POST | /debate/rooms/{code}/turn | Upload turn audio |
| GET | /debate/rooms/{code} | Get room state |
| GET | /debate/motions | List all motions |
| GET | /debate/my-debates | User's debate history |
| WS | /debate/ws/{code} | Live room updates |

### Admin Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /admin/debates | List debates (filterable) |
| GET | /admin/debates/{id} | Debate details |
| POST | /admin/debates/{id}/turns/{tid}/review | Override score |

---

## Local LLM Setup (Ollama)

### Installation

```powershell
# Install Ollama
winget install Ollama.Ollama

# Pull recommended model
ollama pull qwen2.5:7b

# Or for coding-focused
ollama pull qwen2.5-coder:7b

# Test
ollama run qwen2.5:7b "Hello"
```

### System Requirements

- **RAM:** 16GB (your system: ✓)
- **GPU:** RTX 3050 6GB (your system: ✓)
- **Model size:** ~4.5GB for 7B model

### Integration Code

```python
# app/core/llm_client.py

import httpx
import asyncio
from typing import Optional

OLLAMA_BASE = "http://localhost:11434"

class LocalLLM:
    def __init__(self, model: str = "qwen2.5:7b"):
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def generate(self, prompt: str) -> str:
        response = await self.client.post(
            f"{OLLAMA_BASE}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
        )
        return response.json()["response"]
    
    async def close(self):
        await self.client.aclose()

# Singleton instance
llm = LocalLLM()
```

---

## Environment Variables

### Backend (.env)

```env
# Auth
AUTH_BYPASS=true  # For local dev
FIREBASE_SERVICE_ACCOUNT_JSON=...

# Storage
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
TEMP_DIR=temp

# Pronunciation
PRONUNCIATION_PROVIDER=hf_phoneme
HF_PHONEME_MODEL_NAME=facebook/wav2vec2-lv-60-espeak-cv-ft

# Interview Studio (ss3)
CSA_SERVICE_URL=http://127.0.0.1:8001
CSA_DATA_DIR=outputs/ss3
CSA_ANALYZE_TIMEOUT_SECONDS=180

# Teachers (comma-separated)
TEACHER_EMAILS=teacher1@kiet.edu,teacher2@kiet.edu

# Local LLM (new)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

### Frontend (.env.development)

```env
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=...
VITE_API_URL=  # Empty for same-origin proxy
```

---

## Running the Project

### Development

```powershell
# Terminal 1: Backend
cd c:\Users\avira\Projects\softskills2
python -m uvicorn app.main:app --reload --port 8080

# Terminal 2: Frontend
cd c:\Users\avira\Projects\softskills2\frontend
npm run dev -- --host

# Terminal 3: Local LLM (optional)
ollama serve
```

### Production (Fly.io)

```powershell
flyctl deploy
```

---

## Testing

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test
pytest tests/test_debate.py -v
```

---

## Key Files to Modify for Bug Fix

1. **`frontend/src/components/DebateArenaView.tsx`**
   - Fix `handleManualStop` function
   - Fix turn reset logic in useEffect
   - Ensure recorder state syncs with turn changes

2. **`frontend/src/hooks/useAudioRecorder.ts`**
   - Check if reset() properly clears all state
   - Ensure no stale references

## Key Files for Content Scoring Feature

1. **NEW: `app/debate/content_scoring.py`**
   - LLM integration for content analysis

2. **MODIFY: `app/debate/service.py`**
   - Update `compute_ai_score` to include content

3. **MODIFY: `app/debate/schemas.py`**
   - Add content score fields to DebateTurn

4. **MODIFY: `app/debate/room_manager.py`**
   - Pass motion context to scoring

5. **MODIFY: `frontend/src/components/DebateArenaView.tsx`**
   - Display content feedback in results

---

## Summary for AI Assistant

**Tum (new AI model) ko ye karna hai:**

1. **Bug Fix Priority:**
   - "Submit early" button 2nd user ke baad work nahi kar raha
   - `DebateArenaView.tsx` me `handleManualStop` aur turn reset logic check karo
   - Race condition ho sakti hai between state broadcast aur recorder reset

2. **Content Scoring Feature:**
   - Local Ollama LLM se content relevance score add karna hai
   - Current scoring sirf pronunciation + fluency hai
   - Content scoring 40% weight ke saath add karna hai

3. **Important Constraints:**
   - `/app/pronunciation/`, `/app/battles/`, `/app/asr/`, etc. ko modify NAHI karna
   - Sirf debate-related files aur frontend components modify karo
   - No new external dependencies (Postgres, Redis, etc.)

4. **Local LLM:**
   - System: 16GB RAM, RTX 3050 6GB, i5-12500HX
   - Model: Ollama with qwen2.5:7b (ya qwen2.5-coder:7b)
   - Already installed nahi hai, pehle setup karna padega


---

## Action Plan for New AI Model

### Phase 1: Bug Fix - "Submit Early" Not Working (Priority HIGH)

**Problem:** Second user ke turn me "Submit early" button click karne par kuch nahi hota.

**Files to Investigate:**
```
frontend/src/components/DebateArenaView.tsx  (lines 311-361, 843-851)
frontend/src/hooks/useAudioRecorder.ts
frontend/src/hooks/useDebateSocket.ts
```

**Steps:**
1. Open `DebateArenaView.tsx`
2. Find the `useEffect` that resets state on turn change (line ~357)
3. Find `handleManualStop` function (line ~843)
4. Add console.log statements to debug:
   ```typescript
   console.log('handleManualStop called', {
     isRecording: recorder.isRecording,
     uploadingTurn,
     autoUploadRef: autoUploadRef.current,
     isMyTurn,
   });
   ```
5. Check if `recorder.reset()` is being called prematurely
6. Check if `autoUploadRef.current` is stuck at `true`

**Likely Fix:**
```typescript
// Replace the turn reset useEffect with:
useEffect(() => {
  // Reset only for non-active speakers
  const isNewActivePlayer = myParticipant && 
    state?.active_turn_index === myParticipant.turn_index;
  
  if (!isNewActivePlayer) {
    autoUploadRef.current = false;
    setUploadError(null);
    setLastTurnResult(null);
    if (recorder.isRecording) {
      void recorder.stop();
    }
    recorder.reset();
  }
}, [state?.active_turn_index]);
```

### Phase 2: Content Scoring with Local LLM

**Prerequisites:**
1. Install Ollama: `winget install Ollama.Ollama`
2. Pull model: `ollama pull qwen2.5:7b`
3. Start service: `ollama serve`

**New Files to Create:**
```
app/debate/content_scoring.py     # LLM integration
app/core/llm_client.py            # Ollama client wrapper
```

**Files to Modify:**
```
app/debate/service.py             # Add content scoring call
app/debate/schemas.py             # Add content_score field
app/debate/room_manager.py        # Pass motion to scoring
app/core/config.py                # Add OLLAMA_* settings
frontend/src/components/DebateArenaView.tsx  # Show content feedback
```

**Implementation Steps:**

1. Create `app/core/llm_client.py`:
```python
import httpx
from app.core.config import settings

class OllamaClient:
    def __init__(self):
        self.base_url = settings.OLLAMA_URL or "http://localhost:11434"
        self.model = settings.OLLAMA_MODEL or "qwen2.5:7b"
    
    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False}
            )
            return resp.json()["response"]

ollama = OllamaClient()
```

2. Create `app/debate/content_scoring.py`:
```python
import json
import re
from app.core.llm_client import ollama
from app.core.logging_helpers import logger

async def score_debate_content(
    transcript: str,
    motion_title: str,
    motion_text: str,
) -> tuple[float | None, str]:
    """Score speech content relevance to debate motion."""
    
    if not transcript or len(transcript.strip()) < 20:
        return None, "Transcript too short for content analysis"
    
    prompt = f"""You are a debate judge evaluating a student's speech.

DEBATE MOTION: {motion_title}
"{motion_text}"

STUDENT'S SPEECH:
"{transcript}"

Score the speech on these criteria (0-25 each):
1. RELEVANCE: Does it directly address the motion?
2. ARGUMENTS: Are the points logical and supported?
3. STRUCTURE: Is there clear organization?
4. PERSUASION: How convincing is the argument?

Respond with ONLY valid JSON:
{{"total_score": <0-100>, "feedback": "<one short sentence>"}}"""

    try:
        response = await ollama.generate(prompt)
        # Extract JSON from response
        match = re.search(r'\{[^}]+\}', response)
        if match:
            data = json.loads(match.group())
            score = max(0, min(100, float(data.get("total_score", 0))))
            feedback = data.get("feedback", "")[:200]
            return score, feedback
        return None, "Could not parse LLM response"
    except Exception as e:
        logger.warning(f"Content scoring failed: {e}")
        return None, f"Content scoring error: {type(e).__name__}"
```

3. Update `app/debate/service.py`:
```python
# Add to compute_ai_score or create new function
async def compute_full_ai_score(
    pronunciation: PronunciationResult,
    fluency: FluencyResult,
    transcript: str,
    motion_title: str,
    motion_text: str,
) -> tuple[float, bool, dict]:
    """
    Enhanced scoring with content analysis.
    Weights: Pronunciation 30%, Fluency 30%, Content 40%
    """
    from app.debate.content_scoring import score_debate_content
    
    pron = pronunciation.overall_score if pronunciation and pronunciation.available else None
    clarity = fluency.clarity_score if fluency else None
    
    # Get content score
    content_score, content_feedback = await score_debate_content(
        transcript, motion_title, motion_text
    )
    
    breakdown = {
        "pronunciation": pron,
        "fluency": clarity,
        "content": content_score,
        "content_feedback": content_feedback,
    }
    
    # Calculate weighted score
    weighted_sum = 0.0
    total_weight = 0.0
    
    if pron is not None:
        weighted_sum += pron * 0.3
        total_weight += 0.3
    if clarity is not None:
        weighted_sum += clarity * 0.3
        total_weight += 0.3
    if content_score is not None:
        weighted_sum += content_score * 0.4
        total_weight += 0.4
    
    if total_weight == 0:
        return 0.0, True, breakdown
    
    final_score = round(weighted_sum / total_weight, 2)
    return final_score, False, breakdown
```

4. Update `app/debate/schemas.py` - Add to DebateTurn:
```python
class DebateTurn(BaseModel):
    # ... existing fields ...
    content_score: Optional[float] = None
    content_feedback: Optional[str] = None
    score_breakdown: Optional[dict] = None  # {pronunciation, fluency, content}
```

5. Update frontend to show content feedback in results

### Phase 3: Testing

```powershell
# Test bug fix
# 1. Open browser, create debate room
# 2. Join with 4 accounts (use incognito windows)
# 3. All ready, wait for prep
# 4. First person speaks and submits
# 5. Second person should see recording start
# 6. Click "Submit early" - should work now

# Test content scoring
curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"qwen2.5:7b","prompt":"Hello","stream":false}'
```

---

## Quick Reference Commands

```powershell
# Start project
cd c:\Users\avira\Projects\softskills2
python -m uvicorn app.main:app --reload --port 8080
cd frontend && npm run dev -- --host

# Start Ollama
ollama serve

# Pull model
ollama pull qwen2.5:7b

# Test model
ollama run qwen2.5:7b "Score this debate argument"

# Deploy
flyctl deploy

# Check logs
flyctl logs -a softskills-kiet-12
```

---

## Contact / Context

- **Project:** KIET Soft Skills Training Platform
- **Target Users:** KIET college students (@kiet.edu)
- **Current Status:** Deployed on Fly.io, debate feature has bug
- **User's System:** Windows, 16GB RAM, RTX 3050 6GB, i5-12500HX

Ye document dusre AI model ko dene ke liye ready hai. Copy karo aur paste karo!
