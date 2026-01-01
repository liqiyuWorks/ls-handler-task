import pandas as pd

file_path = '/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task/scripts/data_handle/tradetapeEEX_2025.10.20(1).xlsx'

try:
    df = pd.read_excel(file_path, sheet_name='2016-2025', nrows=50)
    print("Sample Data from 2016-2025:")
    print(df[['Date', 'Product', 'Contract', 'Price', 'Quantity']].head(10))
    print("\nProduct Unique (sample):", df['Product'].unique())
    print("Contract Unique (sample):", df['Contract'].unique())
except Exception as e:
    print(e)
