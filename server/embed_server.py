import sys
import json
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("./bge-m3", device="cpu")
# model.save("./bge-m3")

print("READY", flush=True)

for line in sys.stdin:
    text = line.strip()

    formatted = f"Represent this sentence for searching relevant passages: {text}"

    embedding = model.encode(
        formatted,
        normalize_embeddings=True,
    )

    print(json.dumps(embedding.tolist()), flush=True)
