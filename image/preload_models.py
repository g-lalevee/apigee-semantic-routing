import os
from fastembed import TextEmbedding

MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")
CACHE_DIR = os.getenv("FASTEMBED_CACHE_PATH", "/app/model_cache")

print(f"[BUILD] Pre-downloading model '{MODEL_NAME}' into '{CACHE_DIR}'...")
os.makedirs(CACHE_DIR, exist_ok=True)

# Initialize FastEmbed to download and persist ONNX files
_ = TextEmbedding(model_name=MODEL_NAME, cache_dir=CACHE_DIR)
print("[BUILD] Model downloaded and validated successfully.")
