//+------------------------------------------------------------------+
//|                                   LiQiyu_Strategy_V9.0_Martingale.mq4|
//|                    M3/M12 Trend + Smart Grid Recovery (1.5x)     |
//+------------------------------------------------------------------+
#property copyright "Li Qiyu Quant Labs"
#property version   "9.00"
#property strict

// --- Pivot: From "Sniper Stop-Loss" to "Grid Recovery" ---
// User Feedback: "Stop Loss accumulation is painful. Want to hold and win."
// Strategy: Uses V8.7 Precision Entry, but replaces SL with Smart Grid.

extern string _S_ = "=== Protection (Grid Safety) ===";

extern double Risk_Percent   = 0.0;   // Not used in Grid (Use Fixed Lot)
extern double Fixed_Lot      = 0.01;  // Base Lot Size (Start small!)

extern double Max_Drawdown   = 30.0;  // Hard Stop: 30% Equity Protection

extern int    Max_Grid_Layers = 6;    // Safety Cap: Max 6 Layers

extern string _G_ = "=== Grid Recovery Settings ===";

extern bool   Use_Grid_Recovery = true; 
extern int    Grid_Step_Points  = 300;  // 30 Pips Distance (Wider for Gold)

extern int    Martingale_Mode   = 1;    
// 0: Fixed Lot (1.0x) - Conservative
// 1: Semi-Martingale (1.5x) - Recommended (Quick Recovery)
// 2: Standard Martingale (2.0x) - Aggressive

extern double Basket_Target_USD = 5.0;  // Profit Target ($) for the WHOLE basket to close

extern int    Max_Spread_Point = 50;  // Max Spread Allowed

// --- Strategy Parameters (V8.7 Base) ---

extern string _P_ = "=== Strategy V8.7 (Precision Entry) ===";

extern int    Trend_MA_Period = 34;   
extern double Vol_Squeeze_F   = 1.0;  
extern int    Vol_MA_Period   = 20;   

// Removed: ATR_Stop_Mult, Trail_Start (Replaced by Grid Logic)

extern int    RSI_Buy_Max     = 75;   
extern int    RSI_Sell_Min    = 25;   
extern int    Breakout_Buffer = 10;   

extern bool   Use_Momentum    = true; 
extern bool   Use_MACD_Filter = true; 
extern bool   Use_Vol_Ignition= true; 
extern bool   Use_M1_Structure= true; 

extern int    ADX_Period      = 14;   
extern int    ADX_Min_Level   = 15;   
extern bool   Use_M30_Filter  = true; 
extern int    M30_Buffer_Points = 20; 

// --- Global Variables ---
int    Magic  = 2026900; // V9.0 Magic
string sComm  = "LQ_V9.0_Recovery";
datetime Last_M3_Time = 0;
bool   Order_Placed_In_Current_Bar = false; 

// --- Synthetic Bar Structure ---
struct SyntheticBar {
   double b_open;
   double b_high;
   double b_low;
   double b_close;
   double b_volume; 
   datetime b_time;
};

//+------------------------------------------------------------------+
//| Initialization                                                   |
//+------------------------------------------------------------------+
int OnInit() {
   EventSetTimer(1); 
   ObjectsDeleteAll(0, "LQ_"); 
   return(INIT_SUCCEEDED); 
}
void OnDeinit(const int r) { ObjectsDeleteAll(0, "LQ_"); }

// Trading Hours
extern bool Use_Time_Filter = false; 
extern int StartHour = 9;   
extern int EndHour   = 22;

//+------------------------------------------------------------------+
//| Main Logic                                                       |
//+------------------------------------------------------------------+
void OnTick() {
   // 1. Safety & Grid Management (Priority High)
   if(CheckRisk()) return;      // Check Max Drawdown
   ManageGridExit();            // Check Basket Profit
   ManageGridRecovery();        // Check if we need to add layers

   // 2. Entry Logic (Only if NO positions open - Grid handles the rest)
   if (CountOrders(0) > 0 || CountOrders(1) > 0) return; // Busy in Grid

   // --- V8.7 Entry Logic Below ---
   
   // Time Filter
   int hour = TimeHour(TimeCurrent());
   if (Use_Time_Filter && (hour < StartHour || hour >= EndHour)) {
       // Outside hours: If no trades, relax. (Grid manages existing)
       return; 
   }

   // 1. Synthetic Data & Indicators
   datetime current_time = TimeCurrent();
   int period_seconds = 3 * 60;
   int seconds_In = TimeSeconds(current_time) + TimeMinute(current_time) * 60 + TimeHour(current_time) * 3600;
   datetime current_m3_start = (datetime)(current_time - (seconds_In % period_seconds));
   
   if (current_m3_start != Last_M3_Time) {
      Last_M3_Time = current_m3_start;
      Order_Placed_In_Current_Bar = false; // Reset for new bar
   }

   SyntheticBar M12_0 = GetSyntheticBar(12, 0); 
   SyntheticBar M12_1 = GetSyntheticBar(12, 1); 
   SyntheticBar M3_1 = GetSyntheticBar(3, 1);   
   
   double ema_m12 = GetSyntheticEMA(12, Trend_MA_Period, 0); 
   double vol_ma_m3 = GetSyntheticVolMA(3, Vol_MA_Period, 1); 
   
   double rsi_m3 = GetSyntheticRSI(3, 14);   
   double rsi_m12 = GetSyntheticRSI(12, 14); 
   
   double adx_m30 = iADX(NULL, PERIOD_M30, ADX_Period, PRICE_CLOSE, MODE_MAIN, 0);
   bool adx_ok = (adx_m30 > ADX_Min_Level);

   double ema_m30 = iMA(NULL, PERIOD_M30, 34, 0, MODE_EMA, PRICE_CLOSE, 0);
   double close_m30 = iClose(NULL, PERIOD_M30, 0);
   double m30_buf = M30_Buffer_Points * Point;
   bool m30_bull = (!Use_M30_Filter || close_m30 > (ema_m30 - m30_buf)); 
   bool m30_bear = (!Use_M30_Filter || close_m30 < (ema_m30 + m30_buf)); 

   bool is_uptrend = (M12_0.b_close > ema_m12);
   bool is_dntrend = (M12_0.b_close < ema_m12);
   bool is_sqz = (M3_1.b_volume < vol_ma_m3 * Vol_Squeeze_F); 
   
   bool m3_trend_up = (M3_1.b_close > GetSyntheticEMA(3, 34, 1));
   bool m3_trend_dn = (M3_1.b_close < GetSyntheticEMA(3, 34, 1));

   bool rsi_resonance_buy = (rsi_m3 < RSI_Buy_Max && rsi_m12 > 50); 
   bool rsi_resonance_sell = (rsi_m3 > RSI_Sell_Min && rsi_m12 < 50); 
   
   bool momentum_up = !Use_Momentum || (M12_0.b_close > M12_1.b_close);
   bool momentum_dn = !Use_Momentum || (M12_0.b_close < M12_1.b_close);

   double buffer = Breakout_Buffer * Point;
   double buy_trigger = High[1] + buffer; 
   double sell_trigger = Low[1] - buffer;  
   
   // A. MACD Trend Confirmation
   double m12_macd_main = GetSyntheticMACD(12, 12, 26, 9, 0, MODE_MAIN);
   double m12_macd_sig  = GetSyntheticMACD(12, 12, 26, 9, 0, MODE_SIGNAL);
   bool m12_macd_bull = (m12_macd_main > m12_macd_sig);
   bool m12_macd_bear = (m12_macd_main < m12_macd_sig);
   
   bool macd_buy_ok  = !Use_MACD_Filter || m12_macd_bull; 
   bool macd_sell_ok = !Use_MACD_Filter || m12_macd_bear;

   // B. Volume Ignition 
   double vol_sum_m1 = 0;
   for(int k=1; k<=20; k++) vol_sum_m1 += iVolume(NULL, PERIOD_M1, k);
   double vol_m1_avg = vol_sum_m1 / 20.0; 
   bool vol_ignite = !Use_Vol_Ignition || (Volume[0] > vol_m1_avg * 1.0); 
   if (Vol_Squeeze_F >= 0.8) vol_ignite = (Volume[0] > vol_m1_avg * 0.8); 

   // C. V8.7 M1 Micro-Structure
   bool m1_pre_sqz = !Use_M1_Structure || (iVolume(NULL, PERIOD_M1, 1) < vol_m1_avg * 1.3); 
   bool m1_struct_ok = m1_pre_sqz;
   
   // Strict Alignment Check
   bool strict_buy  = is_uptrend && m3_trend_up && m30_bull && macd_buy_ok && vol_ignite && m1_struct_ok;
   bool strict_sell = is_dntrend && m3_trend_dn && m30_bear && macd_sell_ok && vol_ignite && m1_struct_ok;  
   
   int spread = (int)MarketInfo(Symbol(), MODE_SPREAD);
   
   if (current_m3_start == Last_M3_Time && !Order_Placed_In_Current_Bar) { 
       
       if (spread > Max_Spread_Point) return;

       if (Ask >= buy_trigger && strict_buy && adx_ok && momentum_up && is_sqz && rsi_resonance_buy) {
          OpenInitialTrade(0); // Open Buy
          Order_Placed_In_Current_Bar = true; 
       }
       else if (Bid <= sell_trigger && strict_sell && adx_ok && momentum_dn && is_sqz && rsi_resonance_sell) {
          OpenInitialTrade(1); // Open Sell
          Order_Placed_In_Current_Bar = true; 
       }
   }
   
   UpdateUI(M12_0.b_close, ema_m12, M3_1.b_volume, vol_ma_m3, rsi_m3, rsi_m12, adx_m30, is_uptrend, buy_trigger, sell_trigger, macd_buy_ok, macd_sell_ok, vol_ignite, m3_trend_up, momentum_up, m1_struct_ok);
}

//+------------------------------------------------------------------+
//| V9.0 Grid Management Logic                                       |
//+------------------------------------------------------------------+

// 1. Exit Logic: Basket Target
void ManageGridExit() {
    double total_profit = 0;
    int cnt = 0;
    
    for(int i=0; i<OrdersTotal(); i++) {
        if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
            total_profit += OrderProfit() + OrderSwap() + OrderCommission();
            cnt++;
        }
    }
    
    // Close All if Profit Reaches Target
    if (cnt > 0 && total_profit >= Basket_Target_USD) {
        Print("V9.0 Basket Exit! Total Profit: $", total_profit);
        CloseAllOrders();
    }
}

// 2. Recovery Logic: Add Layers
void ManageGridRecovery() {
    if (!Use_Grid_Recovery) return;
    
    int cnt = 0;
    int type = -1;
    double last_entry_price = 0;
    double last_lot = 0;
    
    // Find last order details
    for(int i=OrdersTotal()-1; i>=0; i--) { // Reverse order to find latest
        if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
            if (cnt == 0) { // Most recent
                last_entry_price = OrderOpenPrice();
                last_lot = OrderLots();
                type = OrderType();
            }
            cnt++;
        }
    }
    
    // Safety Limits
    if (cnt >= Max_Grid_Layers) return; 
    if (cnt == 0 || type == -1) return; // No orders to recover
    
    // Check Distance for Logic
    double dist = 0;
    if (type == OP_BUY) {
        dist = (last_entry_price - Ask) / Point; // Positive if price dropped
        if (dist >= Grid_Step_Points) {
            double new_lot = CalculateMartingaleLot(last_lot);
            Print("V9.0 Grid: Adding BUY Layer ", cnt+1, " @ ", Ask, " (Dist: ", dist, ")");
            int t = OrderSend(Symbol(), OP_BUY, new_lot, Ask, 3, 0, 0, sComm+"_L"+IntegerToString(cnt+1), Magic, 0, clrBlue);
        }
    }
    else if (type == OP_SELL) {
        dist = (Bid - last_entry_price) / Point; // Positive if price rose
        if (dist >= Grid_Step_Points) {
            double new_lot = CalculateMartingaleLot(last_lot);
            Print("V9.0 Grid: Adding SELL Layer ", cnt+1, " @ ", Bid, " (Dist: ", dist, ")");
            int t = OrderSend(Symbol(), OP_SELL, new_lot, Bid, 3, 0, 0, sComm+"_L"+IntegerToString(cnt+1), Magic, 0, clrRed);
        }
    }
}

double CalculateMartingaleLot(double last_lot) {
    if (Martingale_Mode == 0) return last_lot; // Fixed
    if (Martingale_Mode == 1) return NormalizeDouble(last_lot * 1.5, 2); // Semi
    if (Martingale_Mode == 2) return NormalizeDouble(last_lot * 2.0, 2); // Standard
    return last_lot;
}

void CloseAllOrders() {
    for(int i=OrdersTotal()-1; i>=0; i--) {
        if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
            if(OrderType() == OP_BUY) OrderClose(OrderTicket(), OrderLots(), Bid, 3, clrGray);
            else if(OrderType() == OP_SELL) OrderClose(OrderTicket(), OrderLots(), Ask, 3, clrGray);
        }
    }
}

void OpenInitialTrade(int type) {
    // Initial Trade has NO STOP LOSS (Grid managed)
    // Removed SL calculation
    
    double lots = Fixed_Lot;
    if (AccountFreeMargin() < 10) return;

    int cmd = (type == 0) ? OP_BUY : OP_SELL;
    double price = (type == 0) ? Ask : Bid;
    color clr = (type == 0) ? clrBlue : clrRed;
    
    int ticket = OrderSend(Symbol(), cmd, lots, price, 3, 0, 0, sComm+"_L1", Magic, 0, clr);
    
    if(ticket > 0) Print("V9.0 Initial Trade Opened. Grid Ready.");
}

//+------------------------------------------------------------------+
//| Synthetic Engine & Helpers (Same as V8.7)                        |
//+------------------------------------------------------------------+
SyntheticBar GetSyntheticBar(int period_min, int shift) {
   SyntheticBar bar;
   bar.b_open=0; bar.b_high=0; bar.b_low=999999; bar.b_close=0; bar.b_volume=0;
   
   datetime current_time = Time[0];
   int seconds_In = TimeSeconds(current_time) + TimeMinute(current_time) * 60 + TimeHour(current_time) * 3600;
   int period_seconds = period_min * 60;
   datetime start_time_0 = (datetime)(current_time - (seconds_In % period_seconds)); 
   datetime target_start_time = (datetime)(start_time_0 - (shift * period_seconds));
   datetime target_end_time   = (datetime)(target_start_time + period_seconds);
   
   int start_idx = iBarShift(NULL, PERIOD_M1, target_start_time, false);
   if (start_idx == -1) return bar; 
   
   bar.b_open = iOpen(NULL, PERIOD_M1, start_idx);
   bar.b_time = iTime(NULL, PERIOD_M1, start_idx);
   
   for (int i = start_idx; i >= 0; i--) {
      datetime t = iTime(NULL, PERIOD_M1, i);
      if (t >= target_end_time) break; 
      if (t < target_start_time) continue; 
      
      if (iHigh(NULL, PERIOD_M1, i) > bar.b_high) bar.b_high = iHigh(NULL, PERIOD_M1, i);
      if (iLow(NULL, PERIOD_M1, i) < bar.b_low)   bar.b_low  = iLow(NULL, PERIOD_M1, i);
      bar.b_close = iClose(NULL, PERIOD_M1, i); 
      bar.b_volume += iVolume(NULL, PERIOD_M1, i);
   }
   return bar;
}

double GetSyntheticRSI(int period_min, int rsi_period) {
   double gain_sum = 0;
   double loss_sum = 0;
   for (int i = 1; i <= rsi_period; i++) {
      SyntheticBar b_curr = GetSyntheticBar(period_min, i);
      SyntheticBar b_prev = GetSyntheticBar(period_min, i + 1);
      double diff = b_curr.b_close - b_prev.b_close;
      if (b_curr.b_close == 0 || b_prev.b_close == 0) continue; 
      if (diff > 0) gain_sum += diff;
      else          loss_sum += -diff;
   }
   if (gain_sum + loss_sum == 0) return 50.0;
   return 100.0 * gain_sum / (gain_sum + loss_sum);
}

double GetSyntheticEMA(int period_min, int ma_period, int shift) {
   return iMA(NULL, PERIOD_M1, period_min * ma_period, 0, MODE_EMA, PRICE_CLOSE, shift * period_min);
}

double GetSyntheticVolMA(int period_min, int ma_period, int shift) {
   double sum = 0;
   for(int i=0; i<ma_period; i++) {
      SyntheticBar b = GetSyntheticBar(period_min, shift + i);
      sum += b.b_volume;
   }
   return sum / ma_period;
}

double GetSyntheticMACD(int period_min, int fast_ema, int slow_ema, int signal_ema, int shift, int mode) {
   double fast = GetSyntheticEMA(period_min, fast_ema, shift);
   double slow = GetSyntheticEMA(period_min, slow_ema, shift);
   double main_line = fast - slow;
   if (mode == MODE_MAIN) return main_line;
   if (mode == MODE_SIGNAL) {
       double signal_sum = 0;
       for(int i=0; i<signal_ema; i++) {
           double f_i = GetSyntheticEMA(period_min, fast_ema, shift + i);
           double s_i = GetSyntheticEMA(period_min, slow_ema, shift + i);
           signal_sum += (f_i - s_i);
       }
       return signal_sum / signal_ema;
   }
   return 0;
}

bool CheckRisk() {
   if (AccountEquity() <= 0) return true;
   // Max Drawdown Check (Hard Stop)
   if ((AccountBalance() - AccountEquity()) / AccountBalance() * 100 > Max_Drawdown) {
       Print("V9.0 SAFETY STOP: Max Drawdown ", Max_Drawdown, "% Reached! Closing All.");
       CloseAllOrders();
       return true;
   }
   return false;
}

int CountOrders(int type) {
   int cnt = 0;
   for(int i=0; i<OrdersTotal(); i++) 
      if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic && OrderType() == type) cnt++;
   return cnt;
}

//+------------------------------------------------------------------+
//| Dashboard Display (V9.0 Recovery)                                |
//+------------------------------------------------------------------+
void UpdateUI(double price, double ema, double vol, double vol_ma, double rsi_m3, double rsi_m12, double adx, bool is_uptrend, double b_trig, double s_trig, bool macd_buy_ok, bool macd_sell_ok, bool vol_ignite, bool m3_trend_up, bool mom_ok, bool m1_struct_ok) {

   Comment("");   
   color bg_color = clrBlack; 
   DrawRect("LQ_BG", 20, 20, 360, 480, bg_color); 

   DrawLabel("LQ_Title", 40, 40, "LiQiyu V9.0 PRO (Recovery Grid)", 11, clrGold);

   int orders = CountOrders(OP_BUY) + CountOrders(OP_SELL);
   double open_prof = 0;
   for(int i=0; i<OrdersTotal(); i++) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) open_prof += OrderProfit();
   
   string g_txt = "Grid Status: " + (orders > 0 ? ("Active (" + IntegerToString(orders) + " Layers)") : "Waiting");
   DrawLabel("LQ_Grid", 40, 70, g_txt, 10, orders > 0 ? clrOrange : clrLime); // Priority Display
   
   string p_txt = "Basket Profit: $" + DoubleToString(open_prof, 2) + " / Target: $" + DoubleToString(Basket_Target_USD, 2);
   DrawLabel("LQ_Prof", 40, 90, p_txt, 11, open_prof > 0 ? clrLime : clrRed); 

   // ... Logic Indicators ...
   string v_txt = "M3 Vol: " + (vol < vol_ma ? "Squeeze (OK)" : "High Vol");
   DrawLabel("LQ_Vol", 40, 130, v_txt, 9, vol < vol_ma ? clrSilver : clrGray);
   
   string m1_txt = "M1 Pre-Squeeze: " + (m1_struct_ok ? "OK" : "Wait");
   DrawLabel("LQ_M1", 40, 150, m1_txt, 9, m1_struct_ok ? clrSilver : clrGray);

   string acc = "Equity: $" + DoubleToString(AccountEquity(), 2);
   DrawLabel("LQ_Acc", 40, 390, acc, 11, clrWhite);

   string st = "STATUS: " + (orders > 0 ? "MANAGING BASKET..." : "HUNTING ENTRY...");
   DrawLabel("LQ_ST", 40, 420, st, 11, orders > 0 ? clrYellow : clrDeepSkyBlue);
}

void DrawLabel(string name, int x, int y, string text, int size, color clr) {
   if(ObjectFind(0, name) < 0) {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_XDISTANCE, (long)x);
      ObjectSetInteger(0, name, OBJPROP_YDISTANCE, (long)y);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, 0);
   }
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, (long)size);
   ObjectSetInteger(0, name, OBJPROP_COLOR, (long)clr);
}

void DrawRect(string name, int x, int y, int w, int h, color bg_color) {
   if(ObjectFind(0, name) < 0) {
      ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, 0);
      ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT);
   }
   // Force property update
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, (long)x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, (long)y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, (long)w);
   ObjectSetInteger(0, name, OBJPROP_YSIZE, (long)h);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, (long)bg_color);
   ObjectSetInteger(0, name, OBJPROP_BACK, 0); // Background false
}
