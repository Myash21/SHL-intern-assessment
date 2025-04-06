import streamlit as st
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# ✅ Set page config at the very top!
st.set_page_config(page_title="SHL Assessment Recommender", layout="wide")

# Load FAISS index and assessment metadata
INDEX_PATH = "embedding_index/index.faiss"
ASSESSMENT_DATA_PATH = "embedding_index/assessments.json"

@st.cache_resource
def load_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

@st.cache_resource
def load_index():
    return faiss.read_index(INDEX_PATH)

@st.cache_data
def load_assessments():
    with open(ASSESSMENT_DATA_PATH, "r") as f:
        return json.load(f)

model = load_model()
index = load_index()
assessments = load_assessments()

# Streamlit UI
st.title("🔍 SHL Assessment Recommendation System")

query = st.text_area("Enter Job Description or Hiring Requirement", height=200)

if st.button("Get Recommendations"):
    if not query.strip():
        st.warning("Please enter a valid query.")
    else:
        # Embed the query
        query_embedding = model.encode([query])
        query_embedding = np.array(query_embedding).astype("float32")

        # Search FAISS index
        k = min(10, len(assessments))  # Recommend up to 10
        distances, indices = index.search(query_embedding, k)

        st.subheader("🎯 Top Recommended Assessments")
        results = []

        for i in indices[0]:
            a = assessments[i]
            results.append({
                "Assessment Name": f"[{a['name']}]({a['url']})",
                "Remote Testing Support": "✅" if a["remote_testing"] else "❌",
                "Adaptive/IRT Support": "✅" if a["adaptive_support"] else "❌",
                "Duration": a["duration"] if a["duration"] else "N/A",
                "Test Type": a["test_type"]
            })

        st.table(results)

st.markdown("""---  
**Test Type Legend:**  
A - Ability & Aptitude  
B - Biodata & Situational Judgement  
C - Competencies  
D - Development & 360  
E - Assessment Exercises  
K - Knowledge & Skills  
P - Personality & Behavior  
S - Simulations  
""")