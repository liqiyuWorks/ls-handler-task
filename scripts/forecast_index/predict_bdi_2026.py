import pandas as pd
import datetime

def calculate_slope(x, y):
    n = len(x)
    if n < 2: return 0, 0
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(x * y)
    sum_xx = sum(x * x)
    denominator = (n * sum_xx - sum_x ** 2)
    if denominator == 0: return 0, 0
    m = (n * sum_xy - sum_x * sum_y) / denominator
    c = (sum_y - m * sum_x) / n
    return m, c

def predict_bdi():
    # 1. Load Data
    file_path = 'scripts/forecast_index/baltic_exchange_index_history.csv'
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
        return

    # 2. Preprocessing
    if 'date' not in df.columns or 'BDI' not in df.columns:
        print("Error: Required columns 'date' or 'BDI' missing.")
        return

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['BDI'] = pd.to_numeric(df['BDI'], errors='coerce')
    df = df.dropna(subset=['date', 'BDI']).sort_values('date')

    # 3. Multi-Timeframe Trend Analysis
    # Long Trend (15 days) vs Immediate Momentum (3 days)
    df_15 = df.tail(15).copy()
    df_3 = df.tail(3).copy()
    
    start_date = df_15['date'].min()
    
    def get_xy(dframe):
        dframe['days_since'] = (dframe['date'] - start_date).dt.days
        return dframe['days_since'].values, dframe['BDI'].values

    x15, y15 = get_xy(df_15)
    x3, y3 = get_xy(df_3)
    
    m15, c15 = calculate_slope(x15, y15)
    m3, c3 = calculate_slope(x3, y3)
    
    print(f"15-Day Trend Slope: {m15:.2f} pts/day")
    print(f" 3-Day Trend Slope: {m3:.2f} pts/day")
    
    # 4. Forecast Logic
    target_date = pd.to_datetime("2026-01-08")
    days_to_target = (target_date - start_date).days
    
    # Detect Reversal
    # If 15-day is positive but 3-day is negative, we are in a reversal.
    effective_slope = m15 # Default
    effective_c = c15
    
    if m15 > 0 and m3 < 0:
        print(">> Reversal Detected: Market is turning down after a rally.")
        # The 3-day slope is likely very steep (-59 pts/day based on 2845->2727).
        # Extrapolating that for 30 days would crash the market to 0.
        # So we can't just use m3.
        # We assume the "Correction" brings us back to the mean or a support level.
        
        # Strategy:
        # Use a dampened negative slope.
        # Let's assume the correction continues for a week, then flattens.
        # Or simpler: Use a weighted slope of 0 (flat) or slightly negative.
        
        # Let's use a "Correction Slope" of -10 pts/day as a heuristic for a "soft landing" or steady decline.
        # Or better, average the m15 (bullish) and m3 (bearish) but weight m3 more?
        # m15 is +35. m3 is likely -60. Average is -12. This seems reasonable.
        
        effective_slope = (0.3 * m15) + (0.7 * m3)
        
        # Recalculate intercept from last point
        last_x = x3[-1]
        last_y = y3[-1]
        effective_c = last_y - effective_slope * last_x

    print(f"Effective Slope for Projection: {effective_slope:.2f} pts/day")
    
    baseline_pred = effective_slope * days_to_target + effective_c
    
    # 5. Industry Attribute Adjustment (The "January Effect")
    last_observed_bdi = df['BDI'].iloc[-1]
    
    # Seasonal Anchor:
    # Industry expectation: Jan is weak.
    # If our baseline is now predicting a drop (e.g. to 2200), that aligns with seasonality.
    # We still blend with the Seasonal Anchor to be safe.
    
    seasonal_anchor = last_observed_bdi * 0.85
    
    # Weighted Average
    weighted_prediction = (0.5 * baseline_pred) + (0.5 * seasonal_anchor)
    
    print("-" * 30)
    print("FORECAST ANALYSIS (FINAL)")
    print("-" * 30)
    print(f"Target Date: {target_date.date()}")
    print(f"Last Observed: {last_observed_bdi} (on {df['date'].max().date()})")
    print(f"1. Trend Projection: {baseline_pred:.0f}")
    print(f"   (Slope: {effective_slope:.2f} pts/day)")
    print(f"2. Seasonal Anchor: {seasonal_anchor:.0f}")
    print(f"   (Industry expectation: ~15% drop in Jan)")
    print(f"3. Weighted Forecast: {weighted_prediction:.0f}")
    print("-" * 30)
    print(f"FINAL PREDICTION FOR 2026-01-08: {int(weighted_prediction)}")
    print("-" * 30)

if __name__ == "__main__":
    predict_bdi()
