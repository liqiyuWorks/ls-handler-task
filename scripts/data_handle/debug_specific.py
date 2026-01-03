import pandas as pd
import os

DATA_DIR = 'scripts/data_handle'
FILE_4H = os.path.join(DATA_DIR, 'tradetape_standardized_4h.csv')

try:
    df = pd.read_csv(FILE_4H)
    
    # Target: Baltic Panamax 4TC Avg - CAL24 (PTC)
    product = "Baltic Panamax 4TC Avg"
    contract_month = "CAL24"
    contract_type = "PTC"
    
    print(f"Filtering for {product}, {contract_month} ({contract_type})...")
    
    subset = df[
        (df['Product'] == product) & 
        (df['Contract Month'] == contract_month) & 
        (df['Contract Type'] == contract_type)
    ].copy()
    
    if len(subset) == 0:
        print("No data found for this selection!")
        # Try finding partial matches
        print("Searching for variations...")
        print(df[df['Product'] == product]['Contract Month'].unique())
    else:
        print(f"Found {len(subset)} rows.")
        subset['Date'] = pd.to_datetime(subset['Date'])
        subset = subset.sort_values('Date')
        
        print("\n--- Statistics ---")
        print(subset[['Open', 'High', 'Low', 'Close', 'Volume']].describe())
        
        print("\n--- Anomalies Check ---")
        # Check for 0 or negative prices
        zeros = subset[subset['Close'] <= 0]
        if len(zeros) > 0:
            print(f"Found {len(zeros)} rows with Price <= 0:")
            print(zeros)
        
        # Check for huge wicks (High >> Close or Low << Close)
        subset['Wick_Up'] = (subset['High'] - subset[['Open', 'Close']].max(axis=1)) / subset['Close']
        subset['Wick_Down'] = (subset[['Open', 'Close']].min(axis=1) - subset['Low']) / subset['Close']
        
        huge_wicks = subset[(subset['Wick_Up'] > 0.1) | (subset['Wick_Down'] > 0.1)] # >10% wick
        if len(huge_wicks) > 0:
            print(f"Found {len(huge_wicks)} rows with huge wicks (>10%):")
            print(huge_wicks[['Date', 'Open', 'High', 'Low', 'Close', 'Wick_Up', 'Wick_Down']].head())
            
        # Check for suspicious price jumps
        subset['Prev_Close'] = subset['Close'].shift(1)
        subset['Jump'] = (subset['Close'] - subset['Prev_Close']).abs() / subset['Prev_Close']
        
        jumps = subset[subset['Jump'] > 0.2] # >20% jump
        if len(jumps) > 0:
            print(f"Found {len(jumps)} rows with >20% price jump:")
            print(jumps[['Date', 'Close', 'Prev_Close', 'Jump']].head())
            
        print("\n--- Head ---")
        print(subset.head())

except Exception as e:
    print(e)
