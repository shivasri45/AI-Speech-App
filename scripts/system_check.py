"""System health check script."""
import sys, os
sys.path.insert(0, "/home/ubuntu/softskills")
os.chdir("/home/ubuntu/softskills")

from dotenv import load_dotenv
load_dotenv()

print("=" * 50)
print("SYSTEM HEALTH CHECK")
print("=" * 50)

# 1. Python packages
print("\n--- PACKAGES ---")
try:
    import torch
    print(f"  torch: {torch.__version__}")
except Exception as e:
    print(f"  torch: ERROR - {e}")

try:
    import transformers
    print(f"  transformers: {transformers.__version__}")
except Exception as e:
    print(f"  transformers: ERROR - {e}")

try:
    import whisper
    print(f"  whisper: {whisper.__version__}")
except Exception as e:
    print(f"  whisper: ERROR - {e}")

try:
    import phonemizer
    print(f"  phonemizer: {phonemizer.__version__}")
except Exception as e:
    print(f"  phonemizer: ERROR - {e}")

# 2. Groq
print("\n--- GROQ API ---")
groq_key = os.getenv("GROQ_API_KEY", "")
print(f"  Key set: {'YES' if groq_key.startswith('gsk') else 'NO'}")

# 3. Wav2Vec2 model
print("\n--- PRONUNCIATION MODEL ---")
try:
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    proc = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-lv-60-espeak-cv-ft")
    print("  Processor: OK (cached)")
    model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-lv-60-espeak-cv-ft")
    print(f"  Model: OK ({sum(p.numel() for p in model.parameters())//1000000}M params)")
except Exception as e:
    print(f"  ERROR: {e}")

# 4. Whisper
print("\n--- WHISPER ---")
try:
    model = whisper.load_model("small")
    print("  Whisper small: OK (loaded)")
except Exception as e:
    print(f"  ERROR: {e}")

# 5. ffmpeg
print("\n--- FFMPEG ---")
import shutil
ffmpeg_path = shutil.which("ffmpeg")
print(f"  ffmpeg: {ffmpeg_path or 'NOT FOUND'}")
espeak_path = shutil.which("espeak-ng")
print(f"  espeak-ng: {espeak_path or 'NOT FOUND'}")

# 6. App import test
print("\n--- APP MODULES ---")
try:
    from app.main import app
    print("  app.main: OK")
except Exception as e:
    print(f"  app.main: ERROR - {e}")

try:
    from app.storage.users import users_store
    print(f"  users_store.upsert: {hasattr(users_store, 'upsert')}")
except Exception as e:
    print(f"  users_store: ERROR - {e}")

try:
    from app.asr.groq_whisper import is_groq_configured
    print(f"  Groq whisper configured: {is_groq_configured()}")
except Exception as e:
    print(f"  groq_whisper: ERROR - {e}")

try:
    from app.debate.content_scoring import score_debate_content
    print("  content_scoring: OK")
except Exception as e:
    print(f"  content_scoring: ERROR - {e}")

try:
    from app.gd.room_manager import gd_room_manager
    print("  gd_room_manager: OK")
except Exception as e:
    print(f"  gd_room_manager: ERROR - {e}")

print("\n" + "=" * 50)
print("CHECK COMPLETE")
print("=" * 50)
