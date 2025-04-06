import pandas as pd
import json

# Load the CSV file
df = pd.read_csv("shl_table2_individual_test_solutions.csv")

# Helper function to convert duration
def clean_duration(duration_str):
    if isinstance(duration_str, str) and duration_str.strip().upper() == "N/A":
        return None
    try:
        return int(duration_str)
    except:
        return None

# Preprocess fields
df["Remote Testing Support"] = df["Remote Testing Support"].map({"Yes": True, "No": False})
df["Adaptive/IRT Support"] = df["Adaptive/IRT Support"].map({"Yes": True, "No": False})
df["Duration"] = df["Duration"].apply(clean_duration)

# Rename columns for easier code usage (optional)
df = df.rename(columns={
    "Assessment Name": "name",
    "Assessment URL": "url",
    "Remote Testing Support": "remote_testing",
    "Adaptive/IRT Support": "adaptive_support",
    "Duration": "duration",
    "Test Type": "test_type"
})

# Convert to list of dictionaries
assessment_list = df.to_dict(orient="records")

# Save as cleaned JSON file
with open("assessments_clean.json", "w") as f:
    json.dump(assessment_list, f, indent=2)

print(f"✅ Preprocessing complete. {len(assessment_list)} records saved to 'assessments_clean.json'.")
