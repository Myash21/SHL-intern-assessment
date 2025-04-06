from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
import faiss
import json
import numpy as np
import os

app = Flask(__name__)

# Load model locally (make sure it's downloaded beforehand)
model = SentenceTransformer("./all-MiniLM-L6-v2")

# Load the FAISS index
index = faiss.read_index("embedding_index/index.faiss")

# Load the metadata associated with embeddings
with open("embedding_index/assessments.json", "r", encoding="utf-8") as f:
    assessments = json.load(f)

@app.route("/")
def home():
    return "SHL Assessment Recommender API is running."

@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json()
    query = data.get("query", "")

    if not query:
        return jsonify({"error": "Query not provided."}), 400

    # Compute the embedding of the input query
    query_embedding = model.encode([query])
    query_embedding = np.array(query_embedding).astype("float32")

    # Perform similarity search
    k = min(10, len(assessments))
    distances, indices = index.search(query_embedding, k)

    results = []
    for idx in indices[0]:
        assessment = assessments[idx]
        results.append({
            "name": assessment["name"],
            "url": assessment["url"],
            "remote_testing": assessment["remote_testing"],
            "adaptive_support": assessment["adaptive_support"],
            "duration": assessment["duration"],
            "test_type": assessment["test_type"]
        })

    return jsonify({"recommendations": results})

if __name__ == '__main__':
    app.run(debug=True)
