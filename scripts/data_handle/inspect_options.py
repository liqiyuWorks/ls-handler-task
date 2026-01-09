import pandas as pd
import numpy as np

INPUT_FILE = '/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task/scripts/data_handle/tradetapeEEX_2025.10.20(1).xlsx'
SHEET_MAIN = '2016-2025'

def inspect():
    print("Loading data...")
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_MAIN)
    
    print(f"Columns: {df.columns.tolist()}")
    
    # Check for 'Option' in Contract column
    print("\n--- Rows with 'Option' in Contract/Product? ---")
    if 'Contract' in df.columns:
        options = df[df['Contract'].astype(str).str.contains('Option', case=False, na=False)]
        print(f"Rows with 'Option' in Contract column: {len(options)}")
        if not options.empty:
            # Try to find Price column
            price_col = 'Price' if 'Price' in df.columns else 'Trade Price'
            if price_col not in df.columns:
                 # Fallback
                 cols = [c for c in df.columns if 'Price' in c]
                 price_col = cols[0] if cols else 'Price'
            
            print(options[['Contract', 'Product', price_col]].head())
            
    
    # Check OptionType and AssetClass
    print("\n--- AssetClass and OptionType Analysis ---")
    if 'AssetClass' in df.columns:
        print(f"Unique AssetClass: {df['AssetClass'].unique()}")
    if 'OptionType' in df.columns:
        print(f"Unique OptionType: {df['OptionType'].unique()}")
        # Check if low price rows have OptionType set
        low_price_options = df[(df['Product'] == 'Baltic Capesize 5TC Avg') & (df['Price'] < 5000)]
        print("\nOptionType for low price rows:")
        print(low_price_options['OptionType'].value_counts(dropna=False))
        
        non_low_price_options = df[(df['Product'] == 'Baltic Capesize 5TC Avg') & (df['Price'] >= 5000)]
        print("\nOptionType for normal price rows:")
        print(non_low_price_options['OptionType'].value_counts(dropna=False))

        
    
    # Check OptionStrikePrice
    if 'OptionStrikePrice' in df.columns:
        print("\n--- OptionStrikePrice Analysis ---")
        # Check if rows with OptionStrikePrice are options
        with_strike = df[df['OptionStrikePrice'].notna()]
        print(f"Rows with non-NaN OptionStrikePrice: {len(with_strike)}")
        
        # Check intersection with OptionType
        if 'OptionType' in df.columns:
            print("Strike Price vs Option Type:")
            print(with_strike['OptionType'].value_counts(dropna=False))

        # Check the 153 outliers (Low price, NaN OptionType)
        price_col = 'Price' if 'Price' in df.columns else 'Trade Price'
        if price_col not in df.columns: # fetch again locally
             cols = [c for c in df.columns if 'Price' in c]
             price_col = cols[0] if cols else 'Price'
             
        metric = pd.to_numeric(df[df['Product'] == 'Baltic Capesize 5TC Avg'][price_col], errors='coerce')
        outliers = df[(df['Product'] == 'Baltic Capesize 5TC Avg') & (pd.to_numeric(df[price_col], errors='coerce') < 5000) & (df['OptionType'].isna())]
        print(f"\n--- Analysis of {len(outliers)} Low Price Outliers (NaN OptionType) ---")
        if not outliers.empty:
            print(outliers[['Contract', price_col, 'OptionStrikePrice', 'Date']].head(20))
            if 'OptionStrikePrice' in outliers.columns:
                 print(f"Outliers with Strike Price: {outliers['OptionStrikePrice'].notna().sum()}")



    # Check Panamax
    print("\n--- Low Price Analysis for Baltic Panamax 4TC Avg ---")
    panamax = df[df['Product'] == 'Baltic Panamax 4TC Avg']
    if not panamax.empty:
        price_col = 'Price' if 'Price' in df.columns else 'Trade Price'
        if price_col not in df.columns:
             cols = [c for c in df.columns if 'Price' in c]
             price_col = cols[0] if cols else 'Price'
        
        metric_p = pd.to_numeric(panamax[price_col], errors='coerce')
        # Threshold guess for Panamax? Maybe 3000? Normal seems to be 6000-15000 based on user screen.
        low_price_p = panamax[metric_p < 2000] 
        print(f"Total Panamax rows: {len(panamax)}")
        print(f"Rows < 2000: {len(low_price_p)}")
        if not low_price_p.empty:
            print(low_price_p[['Contract', price_col, 'Date']].head(10))
            if 'OptionType' in low_price_p.columns:
                 print(f"Low Price NaN OptionType: {low_price_p['OptionType'].isna().sum()}")

if __name__ == "__main__":
    inspect()
