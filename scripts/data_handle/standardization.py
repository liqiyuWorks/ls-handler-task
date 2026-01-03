import pandas as pd
import numpy as np
from datetime import datetime

# Configuration
INPUT_FILE = '/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task/scripts/data_handle/tradetapeEEX_2025.10.20(1).xlsx'
OUTPUT_FILE = '/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task/scripts/data_handle/tradetape_standardized.csv'
SHEET_MAIN = '2016-2025'
SHEET_NEW = '2025.04.24'

def parse_contract_string(contract_str):
    """
    Parses 'CTC OCT16' -> Type: 'CTC', Month: 'Oct 2016'
    Standardizes month to MMM YYYY if possible.
    """
    if not isinstance(contract_str, str):
        return pd.Series([None, None])
    
    parts = contract_str.split()
    if len(parts) >= 2:
        c_type = parts[0]
        c_period_str = " ".join(parts[1:])
        
        c_period_formatted = c_period_str
        try:
            # Check for patterns like JAN17, OCT16 (3 chars alpha + 2 digits)
            if len(c_period_str) == 5 and c_period_str[:3].isalpha() and c_period_str[3:].isdigit():
                month_part = c_period_str[:3]
                year_part = "20" + c_period_str[3:]
                dt = datetime.strptime(f"{month_part} {year_part}", "%b %Y")
                c_period_formatted = dt.strftime("%b %Y") # "Oct 2016"
        except:
            pass
            
        return pd.Series([c_type, c_period_formatted])
    return pd.Series([None, contract_str])

def load_sheet_main():
    print(f"Loading {SHEET_MAIN}...")
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_MAIN)
    
    # Standardize columns
    df['DateTime'] = pd.to_datetime(df['Date'], errors='coerce')
    df['DateOnly'] = df['DateTime'].dt.date
    
    # Extract Contract details
    contract_details = df['Contract'].apply(parse_contract_string)
    df['Contract Type'] = contract_details[0]
    df['Contract Month'] = contract_details[1]
    
    # Needs: DateTime, DateOnly, Product, Contract Month, Contract Type, Price, Quantity
    return df[['DateTime', 'DateOnly', 'Product', 'Contract Month', 'Contract Type', 'Price', 'Quantity']]

def load_sheet_new():
    print(f"Loading {SHEET_NEW}...")
    df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NEW)
    
    # Helper to combine date and time safely
    def combine_dt(row):
        try:
            d = row['Date']
            t = row['Time']
            if pd.isna(d):
                return pd.NaT
            
            # If d is already datetime/timestamp
            if isinstance(d, (pd.Timestamp, datetime)):
                date_part = d.date()
            else:
                # Try parsing string date if necessary, but typically pandas reads as timestamp
                date_part = pd.to_datetime(d).date()
            
            # If t is time
            time_part = t
            if isinstance(t, pd.Timestamp):
                 time_part = t.time()
            elif isinstance(t, str):
                # Try parse time string? assuming well formed for now or use pd.to_datetime
                pass 
                
            return pd.to_datetime(f"{date_part} {time_part}")
        except Exception:
            # Fallback if time is missing or issues
            return pd.to_datetime(row['Date'])

    df['DateTime'] = df.apply(combine_dt, axis=1)
    df['DateOnly'] = df['DateTime'].dt.date
    
    # Rename columns to match main sheet schema
    df = df.rename(columns={
        'Trade Price': 'Price',
        'Trade Quantity': 'Quantity'
    })
    
    # Format Contract Month
    # 'Contract (Month)' is datetime, e.g., 2025-05-25
    if 'Contract (Month)' in df.columns:
        # Convert to datetime carefully
        cm_series = pd.to_datetime(df['Contract (Month)'], errors='coerce')
        df['Contract Month'] = cm_series.dt.strftime('%b %Y') # "May 2025"
        # Fill NaNs if any?
    else:
        df['Contract Month'] = None
        
    # 'Contract Type' exists directly
    
    return df[['DateTime', 'DateOnly', 'Product', 'Contract Month', 'Contract Type', 'Price', 'Quantity']]

def main():
    try:
        df_main = load_sheet_main()
        df_new = load_sheet_new()
        
        print(f"Main sheet rows: {len(df_main)}")
        print(f"New sheet rows: {len(df_new)}")
        
        # Merge
        full_df = pd.concat([df_main, df_new], ignore_index=True)
        print(f"Total rows before cleaning: {len(full_df)}")
        
        # Drop rows with critical missing data
        full_df = full_df.dropna(subset=['DateOnly', 'Price', 'Quantity', 'Product'])
        print(f"Total rows after cleaning: {len(full_df)}")

        # Sort values for OHLC logic (First/Last) within the day
        # Important: Sort by DateTime to get correct Open/Close
        full_df = full_df.sort_values(by=['Product', 'Contract Month', 'Contract Type', 'DateOnly', 'DateTime'])
        
        # Aggregate
        print("Aggregating OHLCV...")
        # Ensure Quantity is numeric
        full_df['Quantity'] = pd.to_numeric(full_df['Quantity'], errors='coerce').fillna(0)
        full_df['Price'] = pd.to_numeric(full_df['Price'], errors='coerce')
        
        aggregation = {
            'Quantity': 'sum',               # Volume
            'Price': ['first', 'max', 'min', 'last'] # Open, High, Low, Close
        }

        # Group by the key identifiers
        grouped = full_df.groupby(['Product', 'Contract Month', 'Contract Type', 'DateOnly']).agg(aggregation)
        
        # Flatten columns
        grouped.columns = ['Volume', 'Open', 'High', 'Low', 'Close']
        grouped = grouped.reset_index()
        
        # Select and Reorder
        output_df = grouped[[
            'Product', 
            'Contract Month', 
            'Contract Type',
            'DateOnly', 
            'Volume', 
            'Open', 
            'Close', 
            'High', 
            'Low'
        ]].copy()
        
        # Rename DateOnly to Date for user
        output_df.rename(columns={'DateOnly': 'Date'}, inplace=True)
        
        # --- Strict Sorting ---
        # User requested strict sorting by Date.
        # Primary: Date, Secondary: Product, Tertiary: Contract Month
        output_df = output_df.sort_values(by=['Date', 'Product', 'Contract Month'])
        
        # Format Date to YYYY.MM.DD
        output_df['Date'] = pd.to_datetime(output_df['Date']).dt.strftime('%Y.%m.%d')
        
        # Formatting Volume (optional but clean)
        output_df['Volume'] = output_df['Volume'].astype(int)

        print("Sample Output:")
        print(output_df.head())
        
        
        # --- 4-Hour Aggregation ---
        print("\nAggregating 4-Hour OHLCV...")
        # For 4H, we need to group by Product/Contract first, then resample by DateTime
        # pd.Grouper(key='DateTime', freq='4H') is useful here.
        
        grouped_4h = full_df.groupby([
            'Product', 
            'Contract Month', 
            'Contract Type',
            pd.Grouper(key='DateTime', freq='4H')
        ]).agg(aggregation)
        
        grouped_4h.columns = ['Volume', 'Open', 'High', 'Low', 'Close']
        grouped_4h = grouped_4h.dropna(subset=['Open']) # Remove empty intervals
        grouped_4h = grouped_4h.reset_index()
        
        # Rename DateTime to Date (or keep as Time)
        # User output requirement: "Product, Contract Month, Date, ..."
        # For 4H, 'Date' usually implies the start time of the bar.
        output_4h = grouped_4h[[
            'Product', 
            'Contract Month', 
            'Contract Type',
            'DateTime', 
            'Volume', 
            'Open', 
            'Close', 
            'High', 
            'Low'
        ]].copy()
        
        output_4h.rename(columns={'DateTime': 'Date'}, inplace=True)
        
        # Sort strict by Time
        output_4h = output_4h.sort_values(by=['Date', 'Product', 'Contract Month'])
        
        # Format Date to YYYY.MM.DD HH:MM
        output_4h['Date'] = output_4h['Date'].dt.strftime('%Y.%m.%d %H:%M')
        output_4h['Volume'] = output_4h['Volume'].astype(int)

        print("Sample 4H Output:")
        print(output_4h.head())
        
        OUTPUT_FILE_4H = OUTPUT_FILE.replace('.csv', '_4h.csv')
        print(f"Saving to {OUTPUT_FILE_4H}...")
        output_4h.to_csv(OUTPUT_FILE_4H, index=False)
        print("Done.")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
