import streamlit as st
import pandas as pd

# Sample mini database
med_db = pd.DataFrame([
    {"Medication": "Lisinopril", "Class": "ACE Inhibitor", "Used For": "Hypertension"},
    {"Medication": "Metformin", "Class": "Biguanide", "Used For": "Diabetes"},
    {"Medication": "Atorvastatin", "Class": "Statin", "Used For": "Hyperlipidemia"},
    {"Medication": "Amlodipine", "Class": "Calcium Channel Blocker", "Used For": "Hypertension"},
    {"Medication": "Simvastatin", "Class": "Statin", "Used For": "Hyperlipidemia"},
    {"Medication": "Carvedilol", "Class": "Beta Blocker", "Used For": "Heart Failure"},
    {"Medication": "Metoprolol", "Class": "Beta Blocker", "Used For": "Hypertension"},
])

# Condition to required med class mapping
condition_recommendations = {
    "Diabetes": ["Biguanide", "Statin", "ACE Inhibitor"],
    "Hypertension": ["ACE Inhibitor", "Calcium Channel Blocker", "Beta Blocker"],
    "Heart Failure": ["Beta Blocker", "ACE Inhibitor"],
    "Hyperlipidemia": ["Statin"],
    "ASCVD": ["Statin"]
}

st.title("MTM Support Tool")

# User Input
meds_input = st.text_area("Enter Patient's Medications (comma-separated):", "Lisinopril, Metformin")
conditions_input = st.multiselect("Select Patient's Conditions:", list(condition_recommendations.keys()))

# Process inputs
input_meds = [m.strip().title() for m in meds_input.split(",")]
med_classes = med_db[med_db["Medication"].isin(input_meds)]["Class"].tolist()

# Check for therapeutic duplication
duplicates = med_db[med_db["Medication"].isin(input_meds)].groupby("Class").filter(lambda x: len(x) > 1)

# Check for gaps in care
missing_classes = []
for condition in conditions_input:
    for required_class in condition_recommendations[condition]:
        if required_class not in med_classes:
            missing_classes.append((condition, required_class))

# Results
st.subheader("Therapeutic Duplications")
if not duplicates.empty:
    st.dataframe(duplicates)
else:
    st.write("✅ No duplications found.")

st.subheader("Gaps in Care")
if missing_classes:
    for condition, drug_class in missing_classes:
        st.write(f"❌ {drug_class} may be indicated for {condition} but not found in current regimen.")
else:
    st.write("✅ No care gaps detected.")
