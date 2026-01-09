import pandas as pd

OUTPUT_FILE = '/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task/scripts/data_handle/tradetape_standardized.csv'
OUTPUT_FILE_4H = '/Users/jiufangkeji/Documents/JiufangCodes/ls-handler-task/scripts/data_handle/tradetape_standardized_4h.csv'

def verify():
    print("Verifying 1D Output...")
    df = pd.read_csv(OUTPUT_FILE)
    cape = df[df['Product'] == 'Baltic Capesize 5TC Avg']
    low_price = cape[cape['High'] < 5000] # Check High to be safe, or Low. If Low < 5000, it's suspicious.
    
    # Actually, we filtered raw trades < 5000. So Low should be >= 5000 (unless there are real trades < 5000 that we missed, or if market really went that low?)
    # But for the outliers we saw (153 rows), they were clearly < 5000 when market was high.
    # Let's check for any Price < 5000 in C5TC
    
    # Note: OHLC columns are Open, High, Low, Close
    print(f"C5TC Low Price Min: {cape['Low'].min()}")
    
    suspicious = cape[cape['Low'] < 5000]
    print(f"Suspicious C5TC rows (<5000): {len(suspicious)}")
    if not suspicious.empty:
        print(suspicious.head())

    print("\nVerifying 4H Output...")
    df4 = pd.read_csv(OUTPUT_FILE_4H)
    cape4 = df4[df4['Product'] == 'Baltic Capesize 5TC Avg']
    
    print(f"C5TC 4H Low Price Min: {cape4['Low'].min()}")
    suspicious4 = cape4[cape4['Low'] < 5000]
    print(f"Suspicious C5TC 4H rows (<5000): {len(suspicious4)}")
    if not suspicious4.empty:
        print(suspicious4.head())
        
if __name__ == "__main__":
    verify()
