import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# Page Config
st.set_page_config(layout="wide", page_title="Trade Tape Visualization")

# File Paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data_handle')
FILE_DAILY = os.path.join(DATA_DIR, 'tradetape_standardized.csv')
FILE_4H = os.path.join(DATA_DIR, 'tradetape_standardized_4h.csv')

# Load Data
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return None
    df = pd.read_csv(file_path)
    return df

st.title("EEX Trade Tape Visualization")

# Sidebar Controls
st.sidebar.header("Configuration")

# 1. Select Frequency
freq_option = st.sidebar.selectbox("Frequency", ["Daily", "4-Hour"])
selected_file = FILE_4H if freq_option == "4-Hour" else FILE_DAILY

data = load_data(selected_file)

if data is None:
    st.error(f"Data file not found: {selected_file}")
else:
    # 2. Select Product
    # Define Priority List (High liquidity first)
    # User specifically mentioned C5TC (Baltic Capesize 5TC Avg)
    PRIORITY_PRODUCTS = [
        "Baltic Capesize 5TC Avg",
        "Baltic Panamax 4TC Avg",
        "Baltic Supramax 10TC Avg",
        "Baltic Handysize 7TC Avg"
    ]
    
    # Get all unique products
    all_products = sorted(data['Product'].unique().tolist())
    
    # Split into priority and others
    priority_list = [p for p in PRIORITY_PRODUCTS if p in all_products]
    other_list = [p for p in all_products if p not in priority_list]
    
    # Combined sorted list
    sorted_products = priority_list + other_list
    
    selected_product = st.sidebar.selectbox("Product", sorted_products)
    
    # Filter by Product
    df_product = data[data['Product'] == selected_product].copy()
    
    # 3. Select Contract
    # Create label: "Month (Type)"
    df_product['Contract_Label'] = df_product['Contract Month'] + " (" + df_product['Contract Type'] + ")"
    
    # Sort Contracts Chronologically (Time Sequence)
    # We need to parse 'Contract Month' (e.g., "Oct 2016", "Q1 2025") to sort correctly.
    # Since we don't have a dedicated date column for contract expiry in this view, 
    # we can try to extract the earliest trade date for each contract as a proxy for sorting,
    # OR try to parse the string.
    # Using "Earliest Trade Date" is a robust proxy for chronological listing.
    
    # Ensure 'DateTime' column is datetime type for sorting
    df_product['DateTime'] = pd.to_datetime(df_product['Date'])

    # Group by Contract Label and find min Date
    contract_sort_map = df_product.groupby('Contract_Label')['DateTime'].min().sort_values()
    sorted_contracts = contract_sort_map.index.tolist()
    
    # Default selection: The most recent one (last in list) or the closest forward one?
    # Usually users want the "Front Month" (closest future). 
    # But simply picking the last one (furthest future) or first (oldest history) might not be ideal.
    # Let's pick the one with most recent activity (latest max date) or just default to the first one in the sorted list?
    # TradingView usually defaults to current/front.
    # Let's default to the *last* recorded trade's contract? Or just the top of the list (Oldest).
    # User asked for "Normal logic", usually Front Month.
    # Let's stick to the first in the chronological list (Oldest -> Newest).
    
    # However, to be helpful, let's select the one with the *latest* activity by default (likely current front month).
    stats = df_product.groupby('Contract_Label')['DateTime'].max()
    most_recent_contract = stats.idxmax() if not stats.empty else (sorted_contracts[0] if sorted_contracts else None)
    
    # Find index of most recent to set default
    default_index = sorted_contracts.index(most_recent_contract) if most_recent_contract and most_recent_contract in sorted_contracts else 0
    
    st.sidebar.markdown(f"**Most Recent Contract**: {most_recent_contract if most_recent_contract else 'None'}")
    
    selected_contract_label = st.sidebar.selectbox("Contract", sorted_contracts, index=default_index)
    
    # Filter by Contract
    df_chart = df_product[df_product['Contract_Label'] == selected_contract_label].copy()
    
    # Sort by Date/Time
    df_chart = df_chart.sort_values('DateTime')
    
    # --- Enhancements ---
    
    # 4. Date Range
    st.sidebar.subheader("Time Period")
    min_date = df_chart['DateTime'].min().date()
    max_date = df_chart['DateTime'].max().date()
    
    date_range = st.sidebar.date_input(
        "Select Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # 5. Indicators
    st.sidebar.subheader("Technicals")
    indicators = st.sidebar.multiselect("Moving Averages", ["SMA 5", "SMA 10", "SMA 20", "SMA 60", "SMA 120"], default=["SMA 5", "SMA 20"])
    
    # Calculate Indicators on FULL Data (before slicing) to ensure accuracy
    colors = {'SMA 5': '#2962FF', 'SMA 10': '#FF6D00', 'SMA 20': '#00E676', 'SMA 60': '#D500F9', 'SMA 120': '#FF1744'}
    for ind in indicators:
        period = int(ind.split()[1])
        df_chart[ind] = df_chart['Close'].rolling(window=period).mean()

    # Filter by Date Range (Slicing)
    if len(date_range) == 2:
        start_date, end_date = date_range
        mask = (df_chart['DateTime'].dt.date >= start_date) & (df_chart['DateTime'].dt.date <= end_date)
        df_display = df_chart.loc[mask]
    else:
        df_display = df_chart

    # Main Chart Area
    st.subheader(f"{selected_product} - {selected_contract_label}")
    
    # Layout: Candlestick + Volume
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        subplot_titles=('Price Action', 'Volume'),
        row_width=[0.2, 0.7] # Volume is 20%, Candle is 70%
    )
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df_display['Date'], 
        open=df_display['Open'],
        high=df_display['High'],
        low=df_display['Low'],
        close=df_display['Close'],
        name='OHLC'
    ), row=1, col=1)
    
    # Add Indicators
    for ind in indicators:
        fig.add_trace(go.Scatter(
            x=df_display['Date'], 
            y=df_display[ind], 
            name=ind, 
            line=dict(color=colors.get(ind, 'white'), width=1.5),
            opacity=0.8
        ), row=1, col=1)
    
    # Volume
    fig.add_trace(go.Bar(
        x=df_display['Date'],
        y=df_display['Volume'],
        name='Volume',
        marker_color='orange'
    ), row=2, col=1)
    
    # Styling
    fig.update_layout(
        xaxis_rangeslider_visible=True, # Enable Range Slider (TradingView style)
        height=800,
        margin=dict(l=20, r=20, t=40, b=20),
        template="plotly_dark", # Dark theme
        hovermode="x unified", # Crosshair
        xaxis=dict(
            type='category', # Removes gaps
            categoryorder='category ascending',
            rangeslider=dict(visible=True, thickness=0.08)
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Remove range slider from subplot 2 if it appears there, generally it attaches to x1
    fig.update_xaxes(rangeslider_visible=False, row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Data Table Expander
    with st.expander("View Raw Data"):
        st.dataframe(df_display.drop(columns=['DateTime', 'Contract_Label']))
