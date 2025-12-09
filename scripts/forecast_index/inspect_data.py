import pandas as pd

try:
    df = pd.read_csv('scripts/forecast_index/baltic_exchange_index_history.csv')
    print("Columns:", df.columns.tolist())
    print("\nShape:", df.shape)
    
    # Check date column
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        print("\nDate Range:", df['date'].min(), "to", df['date'].max())
        print("Missing dates:", df['date'].isnull().sum())
        
        # Check BDI column
        df['BDI'] = pd.to_numeric(df['BDI'], errors='coerce')
        print("\nBDI Stats:")
        print(df['BDI'].describe())
        print("Missing BDI:", df['BDI'].isnull().sum())
        
        # Sort by date
        df = df.sort_values('date')
        print("\nLast 5 rows:")
        print(df[['date', 'BDI']].tail())
        
    else:
        print("No 'date' column found.")

except Exception as e:
    print(f"Error: {e}")
