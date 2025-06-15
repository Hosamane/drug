# import streamlit as st
# import pandas as pd
# import requests

# # Load datasets
# med_df = pd.read_csv("dataset/Disease_Medication_Age_MatchedDosage.csv")
# precautions_df = pd.read_csv("dataset/precautions_df.csv")

# # Function to match age to Age Group
# def get_age_group(age):
#     for group in med_df["Age Group"].unique():
#         try:
#             low, high = map(int, group.replace('–', '-').split('-'))
#             if low <= age <= high:
#                 return group
#         except:
#             continue
#     return None

# # Function to query the GROQ LLaMA-4 model
# def query_medical_ai(symptoms_input):
#     headers = {
#         "Authorization": f"Bearer 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",
#         "Content-Type": "application/json"
#     }
#     data = {
#         "model": "meta-llama/llama-4-scout-17b-16e-instruct",
#         "messages": [
#             {
#                 "role": "system",
#                 "content": """You are a professional medical diagnosis assistant. 
# Given symptoms from a user, provide a structured output in exactly this format:

# 1. Disease Name: <Name of the likely disease>
# 2. Disease Description: <Brief explanation of the disease>
# 3. Recommended Medicine: <List of suggested medicine(s) or treatment>

# Do not add any extra text outside these 3 points."""
#             },
#             {"role": "user", "content": symptoms_input}
#         ]
#     }
#     response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
#     if response.status_code == 200:
#         return response.json()["choices"][0]["message"]["content"]
#     else:
#         return f"⚠ API Error: {response.text}"

# # Streamlit UI
# st.set_page_config(page_title="SymptoDiagnoser", layout="centered")
# st.title("🤖 SymptoDiagnoser - AI Medical Assistant")

# symptoms = st.text_area("Enter your symptoms:")
# age = st.number_input("Enter your age", min_value=0, max_value=120, step=1)
# duration = st.number_input("Duration of symptoms (in days)", min_value=0, step=1)

# if st.button("Get Diagnosis"):
#     if not symptoms.strip():
#         st.warning("Please enter symptoms.")
#     elif age < 18 or age > 70:
#         st.error("Your age is not in the supported range (18-70). Please consult a doctor.")
#     else:
#         with st.spinner("Diagnosing..."):
#             result = query_medical_ai(symptoms)

#         st.subheader("📝 AI Diagnosis")
#         st.text(result)

#         # Extract disease from result
#         try:
#             disease_line = [line for line in result.split('\n') if "Disease Name:" in line][0]
#             disease = disease_line.split(":", 1)[1].strip()
#         except:
#             disease = None

#         if not disease:
#             st.error("❌ Could not extract disease from AI response.")
#         elif duration > 2:
#             st.warning("Symptoms are present for more than 2 days. Please follow the precautions below:")
#             precaution_row = precautions_df[precautions_df["Disease"].str.lower() == disease.lower()]
#             if not precaution_row.empty:
#                 st.write("**Precautions:**")
#                 st.markdown(f"- {precaution_row.iloc[0]['Precautions']}")
#             else:
#                 st.info("Precaution data not found for this disease. Please consult a doctor.")
#         else:
#             age_group = get_age_group(age)
#             med_info = med_df[(med_df["Disease"].str.lower() == disease.lower()) & (med_df["Age Group"] == age_group)]
#             if not med_info.empty:
#                 st.success("🎯 Medication and Dosage Recommendation:")
#                 st.write("**Medications:**", med_info.iloc[0]["Medications"])
#                 st.write("**Dosage:**", med_info.iloc[0]["Dosage"])
#             else:
#                 st.warning("No medication found for your age group. Please consult a doctor.")

import streamlit as st
import pandas as pd
import requests

# Load datasets
med_df = pd.read_csv("dataset/Disease_Medication_Age_MatchedDosage.csv")
precautions_df = pd.read_csv("dataset/precautions_df.csv")

# Function to match age to Age Group
def get_age_group(age):
    for group in med_df["Age Group"].unique():
        try:
            low, high = map(int, group.replace('–', '-').split('-'))
            if low <= age <= high:
                return group
        except:
            continue
    return None


# Function to query the GROQ LLaMA-4 model
def query_medical_ai(symptoms_input):
    headers = {
        "Authorization": f"Bearer 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",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [
            {
                "role": "system",
                "content": """You are a professional medical diagnosis assistant. 
Given symptoms from a user, provide a structured output in exactly this format:

1. Disease Name: <Name of the likely disease>
2. Disease Description: <Brief explanation of the disease>
3. Recommended Medicine: <List of suggested medicine(s) or treatment>

Do not add any extra text outside these 4 points."""
            },
            {"role": "user", "content": f"Symptoms: {symptoms_input}"}
        ]
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    print("API Response Status:", response.status_code)
    print("API Response JSON:", response.json())
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"⚠ API Error: {response.text}"

def query_medical_ai_precautions(disease_name):
    headers = {
        "Authorization": f"Bearer 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",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [
            {
                "role": "system",
                "content": "You are a professional medical assistant."
            },
            {
                "role": "user",
                "content": f"""You are a professional medical diagnosis assistant. 
Given disease from a user, provide a structured output in exactly this format:

4. Precautions: <List of suggested precautions to be taken by the patient>

Do not add any extra text outside these 4 points.

Disease: {disease_name}"""
            }
        ]
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        return None
# Streamlit UI
st.set_page_config(page_title="SymptoDiagnoser", layout="centered")
st.title("🤖 SymptoDiagnoser - AI Medical Assistant")

symptoms = st.text_area("Enter your symptoms:")
age = st.number_input("Enter your age", min_value=0, max_value=120, step=1)
duration = st.number_input("Duration of symptoms (in days)", min_value=0, step=1)
if st.button("Get Diagnosis"):
    if not symptoms.strip():
        st.warning("Please enter symptoms.")
    elif age < 18 or age > 70:
        st.error("Your age is not in the supported range (18–70). Please consult a doctor.")
    else:
        with st.spinner("Diagnosing..."):
            # For duration <= 2 days: Get medication & diagnosis from AI
            if duration <= 2:
                result = query_medical_ai(symptoms)
                st.subheader("📝 AI Diagnosis")
                st.text(result)

                # Extract disease name from AI response
                disease = None
                try:
                    for line in result.split("\n"):
                        if "Disease Name:" in line:
                            disease = line.split(":", 1)[1].strip()
                            break
                except:
                    disease = None

                if not disease:
                    st.error("❌ Could not extract disease from AI response.")
                else:
                    age_group = get_age_group(age)
                    med_info = med_df[(med_df["Disease"].str.lower() == disease.lower()) & (med_df["Age Group"] == age_group)]
                    if not med_info.empty:
                        st.success("🎯 Medication and Dosage Recommendation:")
                        st.write("*Medications:*", med_info.iloc[0]["Medications"])
                        st.write("*Dosage:*", med_info.iloc[0]["Dosage"])
                    else:
                        st.warning("No medication found for your age group. Please consult a doctor.")
            
            # For duration > 2 days: Show only precautions
            else:
    # First get disease name using diagnosis API
                diagnosis_result = query_medical_ai(symptoms)
                disease = None
                try:
                    for line in diagnosis_result.split("\n"):
                        if "Disease Name:" in line:
                            disease = line.split(":", 1)[1].strip()
                            break
                except:
                    disease = None

                if not disease:
                    st.error("❌ Could not extract disease from AI response.")
                else:
                    st.warning("Symptoms have lasted more than 2 days. Please follow these precautions:")

                    precaution_row = precautions_df[precautions_df["Disease"].str.lower() == disease.lower()]
                    if not precaution_row.empty:
                        st.write("*Precautions (from local dataset):*")
                        st.markdown(f"- {precaution_row.iloc[0]['Precautions']}")
                    else:
                        # Call AI precautions API with disease name
                        ai_precautions = query_medical_ai_precautions(disease)
                        if ai_precautions:
                            st.info("Precautions not found locally. Showing AI-generated precautions:")
                            st.markdown(f"- {ai_precautions}")
                        else:
                            st.info("Precaution data not available. Please consult a doctor.")