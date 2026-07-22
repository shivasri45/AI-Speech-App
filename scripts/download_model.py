"""Download Wav2Vec2 pronunciation model on server."""
import sys
print("Downloading Wav2Vec2 model (facebook/wav2vec2-lv-60-espeak-cv-ft)...")
print("This may take 5-10 minutes on first run (~1.3GB download)")
sys.stdout.flush()

from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

print("Downloading processor...")
sys.stdout.flush()
p = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-lv-60-espeak-cv-ft")
print("Processor OK")

print("Downloading model...")
sys.stdout.flush()
m = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-lv-60-espeak-cv-ft")
params = sum(param.numel() for param in m.parameters()) // 1_000_000
print(f"Model OK: {params}M parameters")
print("Done! Model cached for future use.")
