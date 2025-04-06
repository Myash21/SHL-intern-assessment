import numpy as np
import requests

# Sample test queries with ground-truth relevant assessments
test_queries = [
    {
        "query": "Entry-level .NET developer with MVC skills",
        "relevant_assessments": [
            ".NET MVC (New)", ".NET Framework 4.5"
        ]
    }
]

K = 10

# 🧠 Boost the query locally before hitting API
def enrich_query(query):
    query = query.lower()

    boosts = {
        "java": " java backend spring coding programming",
        ".net": " dotnet mvc microsoft web development",
        "rest": " restful apis backend integration",
        "personality": " psychological traits behavior profile",
        "situational": " judgement scenarios decision making",
        "aptitude": " logical reasoning numerical analysis thinking",
        "skills": " knowledge competency capability"
    }

    for key, value in boosts.items():
        if key in query:
            query += " " + value

    return query

# 🌐 Live API call
def get_recommendations(query):
    enriched_query = enrich_query(query)
    url = "https://shl-intern-assessment-4.onrender.com/recommend"
    response = requests.post(url, json={"query": enriched_query})
    if response.status_code == 200:
        data = response.json()
        return [item["name"] for item in data["recommendations"]]
    else:
        return []

# 📊 Evaluation metrics
def recall_at_k(true_labels, predicted, k):
    predicted_top_k = predicted[:k]
    true_positives = sum(1 for item in true_labels if item in predicted_top_k)
    return true_positives / len(true_labels) if true_labels else 0

def average_precision_at_k(true_labels, predicted, k):
    score = 0.0
    num_hits = 0
    for i, p in enumerate(predicted[:k]):
        if p in true_labels:
            num_hits += 1
            score += num_hits / (i + 1)
    return score / min(len(true_labels), k) if true_labels else 0

# 🧮 Evaluation loop
recalls = []
average_precisions = []

for item in test_queries:
    query = item["query"]
    relevant = item["relevant_assessments"]
    predicted = get_recommendations(query)

    r_at_k = recall_at_k(relevant, predicted, K)
    ap_at_k = average_precision_at_k(relevant, predicted, K)

    recalls.append(r_at_k)
    average_precisions.append(ap_at_k)

    print(f"\nQuery: {query}")
    print(f"Recall@{K}: {r_at_k:.4f}")
    print(f"AP@{K}: {ap_at_k:.4f}")

mean_recall = np.mean(recalls)
map_k = np.mean(average_precisions)

print("\n=====================")
print(f"Mean Recall@{K}: {mean_recall:.4f}")
print(f"MAP@{K}: {map_k:.4f}")
print("=====================")
