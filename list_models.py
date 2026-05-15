#!/usr/bin/env python3
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from openai import OpenAI

client = OpenAI(
    base_url="https://llm.ai.e-infra.cz/v1",
    api_key=os.getenv("CERIT_API_KEY"),
)

models = client.models.list()
print("=== Available Models ===")
for m in sorted(models.data, key=lambda x: x.id):
    print(f"  {m.id}")

# Test embedding capability
print("\n=== Testing embedding models ===")
embedding_candidates = [m.id for m in models.data if "embed" in m.id.lower() or "bge" in m.id.lower() or "gte" in m.id.lower() or "e5" in m.id.lower()]
print(f"Embedding model candidates: {embedding_candidates}")

# If no dedicated embedding model, test if a chat model can do embeddings
if not embedding_candidates:
    print("No dedicated embedding model found. Testing chat model embedding endpoint...")
    test_models = [m.id for m in models.data][:5]
    for model_name in test_models:
        try:
            resp = client.embeddings.create(model=model_name, input=["test"])
            print(f"  ✅ {model_name} supports embeddings! Dimension: {len(resp.data[0].embedding)}")
        except Exception as e:
            err_msg = str(e)[:100]
            print(f"  ❌ {model_name}: {err_msg}")
