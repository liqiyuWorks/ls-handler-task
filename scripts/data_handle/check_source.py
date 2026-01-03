import pandas as pd

FILE_PATH = '/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task/scripts/data_handle/tradetapeEEX_2025.10.20(1).xlsx'
SHEET_MAIN = '2016-2025'

try:
    print(f"Reading {SHEET_MAIN}...")
    df = pd.read_excel(FILE_PATH, sheet_name=SHEET_MAIN)
    
    # Filter
    # Product: Baltic Panamax 4TC Avg
    # Date: 2022-04-28 to 2022-04-30
    
    df['Date'] = pd.to_datetime(df['Date'])
    
    mask = (
        (df['Product'] == 'Baltic Panamax 4TC Avg') & 
        (df['Date'] >= '2022-04-28') & 
        (df['Date'] <= '2022-04-30')
    )
    
    subset = df[mask]
    print(f"Found {len(subset)} rows in source.")
    if len(subset) > 0:
        print("First 20 rows:")
        print(subset[['Date', 'Price', 'Quantity']].head(20))
        print("\nStatistics of Price:")
        print(subset['Price'].describe())
        
        # Check for small prices
        print("\nPrices < 1000:")
        print(subset[subset['Price'] < 1000][['Date', 'Price']])

except Exception as e:
    print(e)
