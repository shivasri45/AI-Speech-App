#!/bin/sh
# Startup wrapper for the Fly.io combined image.
#
# Layout:
#   /app          — main backend (`app.main`)
#   /app/ss3      — ss3 gesture microservice (`backend.main`)
#   /data         — Fly volume: HF cache, JSONL stores, ss3 session videos
#
# This script:
#   1. Symlinks app runtime dirs into the /data volume so they persist
#      across machine restarts and image rebuilds.
#   2. Starts the ss3 microservice on 127.0.0.1:8001 (loopback-only).
#   3. Execs the main backend on 0.0.0.0:8080 in the foreground so its
#      exit code becomes the container exit code.

set -e

echo "[fly-start] preparing /data volume layout"
mkdir -p /data/uploads /data/temp /data/outputs /data/cache/huggingface /data/ss3

# Redirect app runtime dirs into the persistent volume via symlinks. Fine
# even when /app/{uploads,temp,outputs} already exist as empty dirs — we
# clear them first.
for name in uploads temp outputs; do
    if [ ! -L "/app/$name" ]; then
        rm -rf "/app/$name"
        ln -s "/data/$name" "/app/$name"
    fi
done

# ss3's session_manager uses `./data` relative to CWD when uvicorn starts
# it from /app/ss3. Point that at the shared volume.
if [ ! -L /app/ss3/data ]; then
    rm -rf /app/ss3/data
    ln -s /data/ss3 /app/ss3/data
fi

# ---------------------------------------------------------------------------
# Start the ss3 microservice in the background.
# ---------------------------------------------------------------------------
echo "[fly-start] launching ss3 gesture microservice on 127.0.0.1:8001"
cd /app/ss3
uvicorn backend.main:app --host 127.0.0.1 --port 8001 --log-level info &
SS3_PID=$!

# Give ss3 a couple of seconds to bind its port before the main backend
# starts polling it. If ss3 dies during boot we'll see it in the logs.
sleep 3
if ! kill -0 "$SS3_PID" 2>/dev/null; then
    echo "[fly-start] FATAL: ss3 microservice failed to start" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Start the main backend in the foreground.
# ---------------------------------------------------------------------------
echo "[fly-start] launching main backend on 0.0.0.0:8080"
cd /app
exec uvicorn app.main:app --host 0.0.0.0 --port 8080 --log-level info
