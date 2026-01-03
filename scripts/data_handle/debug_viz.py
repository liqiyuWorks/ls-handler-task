import pandas as pd
import os

DATA_DIR = 'scripts/data_handle'
FILE_4H = os.path.join(DATA_DIR, 'tradetape_standardized_4h.csv')

try:
    df = pd.read_csv(FILE_4H)
    # Pick a popular product
    print("Products:", df['Product'].unique())
    prod = df['Product'].unique()[0]
    
    subset = df[df['Product'] == prod]
    print(f"\nAnalyzing Product: {prod}")
    
    # Pick a contract
    subset['Contract_Label'] = subset['Contract Month'] + " (" + subset['Contract Type'] + ")"
    contract = subset['Contract_Label'].unique()[0]
    print(f"Analyzing Contract: {contract}")
    
    df_chart = subset[subset['Contract_Label'] == contract].copy()
    df_chart['DateTime'] = pd.to_datetime(df_chart['Date'])
    df_chart = df_chart.sort_values('DateTime')
    
    print(f"Total rows: {len(df_chart)}")
    print("Date Range:", df_chart['DateTime'].min(), "to", df_chart['DateTime'].max())
    
    # Calculate gaps
    df_chart['diff'] = df_chart['DateTime'].diff()
    print("\nTime Difference Description:")
    print(df_chart['diff'].describe())
    
    # Check big gaps (> 1 day)
    big_gaps = df_chart[df_chart['diff'] > pd.Timedelta(days=1)]
    print(f"\nNumber of gaps > 1 day: {len(big_gaps)}")
    if len(big_gaps) > 0:
        print(big_gaps[['Date', 'diff']].head())

except Exception as e:
    print(e)
