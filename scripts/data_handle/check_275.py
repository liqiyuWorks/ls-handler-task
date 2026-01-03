import pandas as pd

FILE_PATH = '/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task/scripts/data_handle/tradetapeEEX_2025.10.20(1).xlsx'
SHEET_MAIN = '2016-2025'

try:
    print(f"Reading {SHEET_MAIN}...")
    df = pd.read_excel(FILE_PATH, sheet_name=SHEET_MAIN)
    
    # Check for Price == 275
    outliers = df[df['Price'] == 275]
    print(f"Found {len(outliers)} rows with Price == 275:")
    if len(outliers) > 0:
        print(outliers[['Date', 'Product', 'Contract', 'Price', 'Quantity']])
        
except Exception as e:
    print(e)
