import pandas as pd

# Load your dataset
df = pd.read_csv("medication_dataset_updated.csv")

# Check for missing values
print(df[['Symptoms', 'Common Indications']].isnull().sum())

# Count how many complete rows are available
print("Valid rows:", df[['Symptoms', 'Common Indications']].dropna().shape[0])
