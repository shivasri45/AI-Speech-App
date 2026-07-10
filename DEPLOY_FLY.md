# Deploy to Fly.io

Single Fly.io app that runs the whole stack: FastAPI backend + built React SPA
+ ss3 gesture microservice. One domain, one Firebase authorized entry, no
CORS gymnastics. ~$5-15/month depending on machine size.

## What you'll have when this is done

- Public URL: `https://softskills-kiet-12.fly.dev` (your team opens this)
- Firebase Google Sign-In gated on `@kiet.edu`
- Pronunciation, 1v1 Battle, Group Debate, Voice CruiseControl, Interview
  Studio (with real posture scoring), and the Admin Panel for teachers
- Persistent JSONL stores + HuggingFace model cache on a Fly volume
- WebSocket support for battles + debate rooms

## Prerequisites (one-time)

1. **`flyctl`** installed. On Windows PowerShell:
   ```powershell
   iwr https://fly.io/install.ps1 -useb | iex
   ```
   Restart the terminal after install so `flyctl` is on PATH.

2. **Fly.io account** with a payment method attached (free tier still needs
   card verification). Sign up at <https://fly.io/app/sign-up>.

3. **Firebase project already configured.** You did this in Task 1 of the
   handoff — `.firebase-admin.json` at the repo root, `frontend/.env.production`
   filled in. Nothing else to do here.

4. **A machine with ≥8 GB free disk** to run the initial `fly deploy` build.
   Fly builds the image locally by default (much faster on decent internet
   than remote builds).

## First deploy (10 commands total)

Run these from the repo root (`c:\Users\avira\Projects\softskills2`) in an
elevated PowerShell:

### 1. Log in

```powershell
flyctl auth login
```

Opens a browser, pick the Google account you want the org owned by.

### 2. Create the app (no deploy yet)

App name is already set to `softskills-kiet-12` in `fly.toml`. If Fly
reports that name is taken, edit `fly.toml` and pick a different one
(e.g. `softskills-kiet-13`), then keep going.

```powershell
flyctl apps create softskills-kiet-12
```

### 3. Create the persistent volume (10 GB is a comfortable ceiling)

```powershell
flyctl volumes create softskills_data --region sin --size 10 -a softskills-kiet-12
```

Answer "yes" when Fly warns about single-region volumes. The volume name
`softskills_data` MUST match the `source` field in `fly.toml` under
`[[mounts]]`.

### 4. Set the secrets

Firebase service-account credentials go in as an inline JSON string. The
easiest way on Windows: read the file into a variable, pipe it into `flyctl`.

```powershell
$firebaseJson = Get-Content -Raw .\.firebase-admin.json

flyctl secrets set `
    FIREBASE_SERVICE_ACCOUNT_JSON="$firebaseJson" `
    TEACHER_EMAILS="teacher1@kiet.edu,teacher2@kiet.edu" `
    -a softskills-kiet-12
```

Replace the `TEACHER_EMAILS` list with the real teacher accounts (comma-
separated, no spaces around commas). Every other setting is already baked
into `fly.toml`'s `[env]` block.

### 5. Deploy

```powershell
flyctl deploy
```

First deploy takes 8-15 minutes:
- Docker image builds (frontend `npm run build`, Python `pip install`,
  ss3 install, ~4 GB image before layer sharing).
- Image uploads to Fly's registry.
- The first `/analyze` call after deploy downloads Whisper (`small`,
  ~140 MB) + Wav2Vec2 phoneme (`facebook/wav2vec2-lv-60-espeak-cv-ft`,
  ~1.26 GB) into the volume. Only the first call is slow.

Watch build progress with `flyctl logs -a softskills-kiet-12` in a second
terminal if you want.

### 6. Firebase Console: add the Fly domain to Authorized Domains

Go to <https://console.firebase.google.com> → your project → **Build →
Authentication → Settings → Authorized domains → Add domain**.

Add: `softskills-kiet-12.fly.dev` (no `https://` prefix).

Without this Google Sign-In will refuse to redirect back and you'll see a
generic "auth/unauthorized-domain" error in the browser console.

### 7. Smoke-test

```powershell
curl https://softskills-kiet-12.fly.dev/health
# {"status":"running","service":"speech-platform"}

# Verify ss3 loopback is reachable from inside the machine:
flyctl ssh console -a softskills-kiet-12
# inside the ssh shell:
curl http://127.0.0.1:8001/modules
```

If either returns a non-200, check `flyctl logs`.

### 8. Pre-warm the pronunciation model (optional but recommended)

The first real `/analyze` call from a student blocks 60-90 seconds while
Whisper + Wav2Vec2 download. Warm them up with a fake call:

```powershell
# Generate the fixture WAV locally if you haven't already:
python .\scripts\generate_sample_audio.py

curl -X POST https://softskills-kiet-12.fly.dev/analyze `
    -F "file=@tests/fixtures/short_sample.wav" `
    -F "expected_text=hello world" `
    -H "Authorization: Bearer <a-real-firebase-id-token>"
```

Getting the ID token: log into the deployed frontend, open DevTools →
Application → Local Storage → find the Firebase entry — the `stsTokenManager.accessToken`
value is the ID token. Copy-paste. Not strictly required; a team member's
first practice attempt will pay this cost once.

### 9. Share the URL

```
https://softskills-kiet-12.fly.dev
```

Team members sign in with their `@kiet.edu` Google accounts. Teachers
(anyone in the `TEACHER_EMAILS` secret) see the **Admin Panel** tile in
the main menu.

## Rolling out updates

```powershell
git pull
flyctl deploy
```

Subsequent deploys are much faster (2-4 min) because Docker layers cache.
Fly does a rolling update — old machine keeps serving until the new one
is healthy.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| 500 on startup, logs say `Auth is enabled but no Firebase credentials` | `FIREBASE_SERVICE_ACCOUNT_JSON` secret not set or malformed | `flyctl secrets list`, re-run step 5 with the raw JSON |
| `auth/unauthorized-domain` in browser | Missing step 7 | Add domain in Firebase Console, hard refresh |
| Interview Studio hangs on "Analyzing…" | ss3 process crashed inside the machine | `flyctl ssh console -a softskills-kiet-12` → `ps -ef` — is `uvicorn backend.main` running? If not, check `flyctl logs` for the mediapipe import error |
| Debate room `paused` never resumes | WebSocket cut when a machine restarted; Fly's rolling deploy drops in-memory room state | Expected — rooms are process-local by design. Teams should restart the debate. |
| 402/413 on turn upload | Fly's default 20 MB request limit vs a long 120s turn upload | Add `[http_service.http_options] max_body_size = "50mb"` to `fly.toml` and redeploy |
| Machine OOM'd during `/analyze` | 2 GB not enough with all three models resident | Bump `[[vm]] memory_mb = 4096` in `fly.toml`, redeploy |

## Scaling down for cost

If you want to run cheaper while nobody's using it:

```powershell
# Stop the machine but keep the app + volume:
flyctl scale count 0 -a softskills-kiet-12

# Wake it back up:
flyctl scale count 1 -a softskills-kiet-12
```

Or edit `fly.toml`:
```toml
[[services]]
  auto_stop_machines = true
  min_machines_running = 0
```
This stops the machine when it's idle. First request after idle takes
~30 seconds to boot. Not great for debate rooms but fine for practice.

## What if you outgrow this

| Signal | Next step |
|---|---|
| >50 concurrent users | Bump memory to 4-8 GB, add a second machine (`flyctl scale count 2`), migrate JSONL → Postgres |
| Battles / debates need cross-machine state | Add Redis for room manager state (currently in-memory) |
| ss3 is a bottleneck | Split ss3 into its own Fly app with `.internal` networking; update `CSA_SERVICE_URL` |

None of those are needed for a team demo.
