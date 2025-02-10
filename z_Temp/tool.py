import pandas as pd

# File path
file_path = '/Users/liangzhisong/Dropbox/script/Bara Integration/Init Files/3/12NEO52RSW.csv'

# Read the CSV file
df = pd.read_csv(file_path)

# Safely transform columns
try:
    # Change the fifth column (index 4) from text to float
    df[df.columns[4]] = df[df.columns[4]].astype(
        str).str.replace(',', '').astype(float)

    # Change the third column (index 2) from text to float
    df[df.columns[2]] = df[df.columns[2]].astype(
        str).str.replace(',', '').astype(float)

    # Change the seventh column (index 6) from text to int
    df[df.columns[6]] = df[df.columns[6]].astype(
        str).str.replace(',', '').astype(int)
except ValueError as e:
    print(f"Error while converting data: {e}")
except KeyError as e:
    print(f"Missing column: {e}")

# Write back to the file
df.to_csv(file_path, index=False)
print("File updated successfully!")
