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
    # Calculate row counts per product to determine default popularity
    product_counts = data['Product'].value_counts()
    sorted_products = product_counts.index.tolist()
    
    selected_product = st.sidebar.selectbox("Product", sorted_products)
    
    # Filter by Product
    df_product = data[data['Product'] == selected_product]
    
    # 3. Select Contract
    # Create label first
    df_product['Contract_Label'] = df_product['Contract Month'] + " (" + df_product['Contract Type'] + ")"
    
    # Sort contracts by trade activity (row count)
    contract_counts = df_product['Contract_Label'].value_counts()
    sorted_contracts = contract_counts.index.tolist()
    
    st.sidebar.markdown(f"**Most Active Contract**: {sorted_contracts[0] if sorted_contracts else 'None'}")
    
    selected_contract_label = st.sidebar.selectbox("Contract", sorted_contracts)
    
    # Filter by Contract
    df_chart = df_product[df_product['Contract_Label'] == selected_contract_label].copy()
    
    # Sort by Date/Time
    df_chart['DateTime'] = pd.to_datetime(df_chart['Date'])
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
