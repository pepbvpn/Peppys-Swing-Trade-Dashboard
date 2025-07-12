import streamlit as st
import pandas as pd
import requests

# Sample medication database
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

# Recommended medication classes by condition
condition_recommendations = {
    "Diabetes": ["Biguanide", "Statin", "ACE Inhibitor"],
    "Hypertension": ["ACE Inhibitor", "Calcium Channel Blocker", "Beta Blocker"],
    "Heart Failure": ["Beta Blocker", "ACE Inhibitor"],
    "Hyperlipidemia": ["Statin"],
    "ASCVD": ["Statin"]
}

# Function to get RxCUI from RxNav
def get_rxcui(drug_name):
    url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={drug_name}"
    r = requests.get(url)
    if r.status_code == 200:
        rx_data = r.json()
        return rx_data.get("idGroup", {}).get("rxnormId", [None])[0]
    return None

# Function to get interactions from RxNav
def get_rx_interactions(rxcui):
    interactions = []
    if not rxcui:
        return interactions
    url = f"https://rxnav.nlm.nih.gov/REST/interaction/interaction.json?rxcui={rxcui}"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        groups = data.get("interactionTypeGroup", [])
        for group in groups:
            for itype in group.get("interactionType", []):
                for pair in itype.get("interactionPair", []):
                    interactions.append({
                        "drug": pair["interactionConcept"][1]["minConceptItem"]["name"],
                        "description": pair["description"]
                    })
    return interactions

# Streamlit UI
st.title("MTM Tool with Real Interaction Checker (RxNav)")

# Inputs
meds_input = st.text_area("Enter Patient's Medications (comma-separated):", "Lisinopril, Metformin, Diphenhydramine")
conditions_input = st.multiselect("Select Patient's Conditions:", list(condition_recommendations.keys()))
age = st.number_input("Enter Patient Age:", min_value=0, max_value=120, value=70)
egfr = st.number_input("Enter Patient eGFR (ml/min/1.73m²):", min_value=0, max_value=200, value=60)

# Process inputs
input_meds = [m.strip().title() for m in meds_input.split(",")]
selected = med_db[med_db["Medication"].isin(input_meds)]
med_classes = selected["Class"].tolist()

# Duplication check
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

# RxNav Interactions
st.subheader("Checking RxNav for Interactions...")
rx_interactions = []
for med in input_meds:
    rxcui = get_rxcui(med)
    interactions = get_rx_interactions(rxcui)
    for i in interactions:
        rx_interactions.append((med, i["drug"], i["description"]))

# Display Results
st.subheader("Therapeutic Duplications")
if not duplicates.empty:
    st.dataframe(duplicates)
else:
    st.write("✅ No duplications found.")

st.subheader("Gaps in Care")
if missing_classes:
    for condition, drug_class in missing_classes:
        st.write(f"❌ {drug_class} may be indicated for {condition} but not found.")
else:
    st.write("✅ No care gaps detected.")

st.subheader("Beers Criteria Alerts")
if not beers_flags.empty:
    st.dataframe(beers_flags[["Medication", "Class", "Used For"]])
else:
    st.write("✅ No Beers Criteria issues.")

st.subheader("Renal Adjustment Warnings")
if not renal_flags.empty:
    st.dataframe(renal_flags[["Medication", "Class", "Renal Warning", "Renal Risk"]])
else:
    st.write("✅ No renal concerns.")

st.subheader("Drug Interaction Alerts from RxNav")
if rx_interactions:
    for med1, med2, note in rx_interactions:
        st.write(f"⚠️ **{med1}** interacts with **{med2}**: {note}")
else:
    st.write("✅ No known interactions found.")
