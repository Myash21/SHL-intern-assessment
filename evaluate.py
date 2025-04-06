import numpy as np

# Sample test queries with ground-truth relevant assessments (use real ones in production)
test_queries = [
    {
        "query": "Java developer with 3 years experience in web apps and RESTful APIs",
        "relevant_assessments": [
            "Java (Coding)", "Java SE 8", "Java Spring", "REST API Development"
        ]
    },
    {
        "query": "Entry-level .NET developer with MVC skills",
        "relevant_assessments": [
            ".NET MVC (New)", ".NET Framework 4.5"
        ]
    },
    {
        "query": "Looking for personality and situational judgement tests",
        "relevant_assessments": [
            "SHL Personality Questionnaire", "Situational Judgement Test"
        ]
    }
]

K = 10

# ⬇️ Replace this function to get results from your actual API/backend
def get_recommendations(query):
    """
    Dummy function: Replace this with actual call to your model/backend.
    Return a list of assessment names (strings) as predicted.
    """
    if "java" in query.lower():
        return ["Java (Coding)", "Java Spring", "Java SE 8", "C++", "REST API Development"]
    elif ".net" in query.lower():
        return [".NET MVC (New)", ".NET Framework 4.5", "C#", "HTML5"]
    elif "personality" in query.lower():
        return ["SHL Personality Questionnaire", "Situational Judgement Test", "Cognitive Aptitude"]
    else:
        return []

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
