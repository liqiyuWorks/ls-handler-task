import pandas as pd

FILE_PATH = '/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task/scripts/data_handle/tradetapeEEX_2025.10.20(1).xlsx'
SHEET_NAME = '2016-2025'

try:
    df = pd.read_excel(FILE_PATH, sheet_name=SHEET_NAME)
    product_name = 'Baltic Capesize 5TC Avg'
    subset = df[df['Product'] == product_name]
    print(f"Product: {product_name}")
    print("Unique Contracts (first 10):", subset['Contract'].unique()[:10])
except Exception as e:
    print(e)
