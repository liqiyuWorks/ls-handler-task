import pandas as pd
import os

file_path = '/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task/scripts/data_handle/tradetapeEEX_2025.10.20(1).xlsx'

try:
    # Read all sheets to see what's available
    xls = pd.ExcelFile(file_path)
    print(f"Sheet names: {xls.sheet_names}")

    # Inspect the first sheet (usually the data sheet)
    df = pd.read_excel(file_path, sheet_name=0, nrows=20)
    print("\nFirst 20 rows of Sheet 1:")
    print(df.head(20))
    print("\nColumns:")
    print(df.columns.tolist())
    
    # Check if there are other sheets that look relevant
    if len(xls.sheet_names) > 1:
        df2 = pd.read_excel(file_path, sheet_name=1, nrows=5)
        print("\nFirst 5 rows of Sheet 2:")
        print(df2.head())

except Exception as e:
    print(f"Error reading excel: {e}")
