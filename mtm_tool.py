import streamlit as st
import pandas as pd

# Sample medication database with Beers and renal info
med_db = pd.DataFrame([
    {"Medication": "Lisinopril", "Class": "ACE Inhibitor", "Used For": "Hypertension", "Beers": False, "Renal Warning": False},
    {"Medication": "Metformin", "Class": "Biguanide", "Used For": "Diabetes", "Beers": False, "Renal Warning": "Avoid if eGFR < 30"},
    {"Medication": "Atorvastatin", "Class": "Statin", "Used For": "Hyperlipidemia", "Beers": False, "Renal Warning": False},
    {"Medication": "Amlodipine", "Class": "Calcium Channel Blocker", "Used For": "Hypertension", "Beers": False, "Renal Warning": False},
    {"Medication": "Simvastatin", "Class": "Statin", "Used For": "Hyperlipidemia", "Beers": False, "Renal Warning": "Caution in renal impairment"},
    {"Medication": "Carvedilol", "Class": "Beta Blocker", "Used For": "Heart Failure", "Beers": False, "Renal Warning": False},
    {"Medication": "Metoprolol", "Class": "Beta Blocker", "Used For": "Hypertension", "Beers": False, "Renal Warning": False},
    {"Medication": "Diphenhydramine", "Class": "Antihistamine", "Used For": "Allergies", "Beers": True, "Renal Warning": False}
])

# Known interaction pairs and messages
interactions = {
    ("Simvastatin", "Amlodipine"): "Increased risk of myopathy; limit simvastatin dose",
    ("Lisinopril", "Metoprolol"): "Risk of hypotension, monitor BP",
    ("Metformin", "Lisinopril"): "Increased risk of lactic acidosis",
    ("Diphenhydramine", "Metoprolol"): "Additive CNS depression"
}

# Recommended medication classes by condition
condition_recommendations = {
    "Diabetes": ["Biguanide", "Statin", "ACE Inhibitor"],
    "Hypertension": ["ACE Inhibitor", "Calcium Channel Blocker", "Beta Blocker"],
    "Heart Failure": ["Beta Blocker", "ACE Inhibitor"],
    "Hyperlipidemia": ["Statin"],
    "ASCVD": ["Statin"]
}

st.title("MTM Support Tool with Interaction, Beers, and Renal Checks")

# User Inputs
meds_input = st.text_area("Enter Patient's Medications (comma-separated):", "Lisinopril, Metformin, Diphenhydramine")
conditions_input = st.multiselect("Select Patient's Conditions:", list(condition_recommendations.keys()))
age = st.number_input("Enter Patient Age:", min_value=0, max_value=120, value=70)
egfr = st.number_input("Enter Patient eGFR (ml/min/1.73m²):", min_value=0, max_value=200, value=60)

# Process medication input
input_meds = [m.strip().title() for m in meds_input.split(",")]
selected = med_db[med_db["Medication"].isin(input_meds)]
med_classes = selected["Class"].tolist()

# Therapeutic duplication check
duplicates = selected.groupby("Class").filter(lambda x: len(x) > 1)

# Gaps in care check
missing_classes = []
for condition in conditions_input:
    for required_class in condition_recommendations[condition]:
        if required_class not in med_classes:
            missing_classes.append((condition, required_class))

# Beers Criteria check
beers_flags = selected[selected["Beers"] == True] if age >= 65 else pd.DataFrame()

# Renal adjustment check
renal_flags = selected[selected["Renal Warning"] != False]
renal_flags = renal_flags.copy()
renal_flags["Renal Risk"] = renal_flags["Renal Warning"].apply(
    lambda x: "⚠️ Caution" if isinstance(x, str) and (
        ("<" in x and egfr < 30) or ("impairment" in x.lower())
    ) else "✅ Safe"
)

# Drug interaction check
interaction_warnings = []
for i in range(len(input_meds)):
    for j in range(i + 1, len(input_meds)):
        pair = (input_meds[i], input_meds[j])
        rev_pair = (input_meds[j], input_meds[i])
        if pair in interactions:
            interaction_warnings.append((pair[0], pair[1], interactions[pair]))
        elif rev_pair in interactions:
            interaction_warnings.append((rev_pair[0], rev_pair[1], interactions[rev_pair]))

# Display Results
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

st.subheader("Beers Criteria Alerts")
if not beers_flags.empty:
    st.dataframe(beers_flags[["Medication", "Class", "Used For"]])
else:
    st.write("✅ No Beers Criteria concerns for this patient.")

st.subheader("Renal Adjustment Warnings")
if not renal_flags.empty:
    st.dataframe(renal_flags[["Medication", "Class", "Renal Warning", "Renal Risk"]])
else:
    st.write("✅ No renal dosing concerns for current eGFR.")

st.subheader("Drug Interaction Alerts")
if interaction_warnings:
    for med1, med2, note in interaction_warnings:
        st.write(f"⚠️ Interaction between **{med1}** and **{med2}**: {note}")
else:
    st.write("✅ No known interactions found among listed medications.")
