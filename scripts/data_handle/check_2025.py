import pandas as pd
import os

DATA_DIR = 'scripts/data_handle'
FILE_DAILY = os.path.join(DATA_DIR, 'tradetape_standardized.csv')
FILE_4H = os.path.join(DATA_DIR, 'tradetape_standardized_4h.csv')

def check_file(name, path):
    print(f"\nChecking {name}...")
    try:
        df = pd.read_csv(path)
        df['Date_Dt'] = pd.to_datetime(df['Date'])
        
        min_date = df['Date_Dt'].min()
        max_date = df['Date_Dt'].max()
        
        print(f"Date Range: {min_date} to {max_date}")
        
        # Check specific year 2025
        df_2025 = df[df['Date_Dt'].dt.year == 2025]
        print(f"Rows in 2025: {len(df_2025)}")
        
        if len(df_2025) > 0:
            print("Sample 2025 data:")
            print(df_2025[['Date', 'Product', 'Contract Month']].head())
            print("Products in 2025:", df_2025['Product'].unique())
    except Exception as e:
        print(f"Error: {e}")

check_file("Daily CSV", FILE_DAILY)
check_file("4H CSV", FILE_4H)
