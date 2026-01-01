import pandas as pd

file_path = '/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task/scripts/data_handle/tradetapeEEX_2025.10.20(1).xlsx'

try:
    xls = pd.ExcelFile(file_path)
    for sheet_name in xls.sheet_names:
        print(f"\n--- Sheet: {sheet_name} ---")
        df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=5)
        print(f"Columns: {df.columns.tolist()}")
        print(df.head(2))
except Exception as e:
    print(e)
