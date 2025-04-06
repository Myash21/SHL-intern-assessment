import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Load the processed JSON file
with open("assessments_clean.json", "r") as f:
    assessments = json.load(f)

# Prepare texts for embedding
texts = [
    f"{item['name']} {item['test_type']} Remote:{item['remote_testing']} Adaptive:{item['adaptive_support']} Duration:{item['duration']}"
    for item in assessments
]

# Load SentenceTransformer model
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(texts, show_progress_bar=True)

# Convert to numpy array
embedding_array = np.array(embeddings).astype("float32")

# Create FAISS index
index = faiss.IndexFlatL2(embedding_array.shape[1])
index.add(embedding_array)

# Create directory if it doesn't exist
os.makedirs("embedding_index", exist_ok=True)

# Save index
faiss.write_index(index, "embedding_index/index.faiss")

# Save mapping to JSON for reference
with open("embedding_index/assessments.json", "w") as f:
    json.dump(assessments, f, indent=2)

print("✅ Embeddings and FAISS index saved successfully.")
