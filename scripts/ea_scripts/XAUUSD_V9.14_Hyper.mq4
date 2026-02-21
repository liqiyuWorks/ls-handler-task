//+------------------------------------------------------------------+
//|                                  LiQiyu_Strategy_V9.14_Hyper.mq4 |
//|                    Hyper Shadow (Super Trend) + Gravity Pro      |
//+------------------------------------------------------------------+
#property copyright "Li Qiyu Quant Labs"
#property version   "9.140"
#property strict

extern string _S_ = "=== Protection & Snowball ===";
extern bool   Use_Auto_Lot   = true;   // [NEW] Enable Compounding
extern double Auto_Lot_Risk  = 1.0;    // [NEW] Risk Factor: 1.0 = 0.01 per $1000
extern double Fixed_Lot      = 0.01;   // Base Lot Size (if Auto=false)
extern double Max_Drawdown   = 30.0;   // Hard Stop: 30% Equity Protection
extern double Min_Margin_Level= 150.0; // [NEW] Freeze grid if Margin Level < 150%
extern int    Max_Grid_Layers = 10;   

extern string _G_ = "=== ATR Grid Recovery ===";
extern bool   Use_Grid_Recovery = true; 
extern bool   Use_ATR_Grid      = true;  
extern int    ATR_Period        = 24;    
extern double ATR_Multi         = 1.5;   // User's Setting (Grid Dist = ATR * 1.5)
extern int    Fix_Dist          = 300;   

extern double Lot_Multi         = 1.3;   // Balanced Multiplier (1.3x)

// --- V9.8 QuickLock (Safe Entry+Fast Exit) ---
extern string _R_ = "=== Adaptive Rolling Profit ===";
extern bool   Use_Basket_Trail   = true;  
extern double Basket_Trail_Start = 3.0;   // Trigger Stage 1 (Wait for $3)
extern double Basket_Trail_Step  = 1.0;   // Stage 1 Retrace (Lock $2)
extern double Basket_Trend_Start = 8.0;   // Trigger Stage 2 (Trend Mode)
extern double Basket_Trend_Step  = 5.0;   // Stage 2 Retrace (Give room for big fish)
extern double Basket_Target_USD  = 50.0;  // Hard Cap (Grand Slam)

extern string _E_ = "=== Smart Exit V9.3 ===";
extern bool   Use_MACD_Exit      = true;  // Enable "Shrinking Momentum" Exit
extern double MACD_Exit_Min_Profit = 2.0; // Only exit if profit > $2

extern int    Max_Spread_Point   = 50;  
extern int    Max_Slippage_Points= 30;    // [NEW] Breakout Execution Slippage

// --- Strategy Parameters (V9.14 Hyper Shadow) ---
extern string _P_ = "=== Entry V9.14 (Hyper) ===";
extern bool   Use_Shadow_Entry = true;    
extern int    Trend_MA_Period = 34;   
extern double Vol_Squeeze_F   = 1.0; 
extern int    Vol_MA_Period   = 20;   
extern int    RSI_Buy_Max     = 70;   
extern int    RSI_Sell_Min    = 30;   
extern int    RSI_M12_Limit   = 80;   
extern int    Max_Dev_From_MA = 1000; // [NEW] Hyper M12 Gravity: $10.0
extern int    Max_Dev_From_M3 = 400;  // Keep M3 Anchor: $4.0
extern int    Breakout_Buffer = 2;    
extern bool   Use_Momentum    = false; 
extern bool   Use_MACD_Filter = true; 
extern bool   Use_Vol_Ignition= true; 
extern bool   Use_M1_Structure= true; 
extern int    ADX_Period      = 14;   
extern int    ADX_Min_Level   = 20;   

extern bool   Use_M30_Filter  = true; 
extern int    M30_Buffer_Points = 20; 

// --- Global Variables ---
int    Magic  = 2026930; 
string sComm  = "LQ_V9.14_Hyper";
datetime Last_M3_Time = 0;
bool   Order_Placed_In_Current_Bar = false; 
bool   Is_Force_Closing = false;

// --- CPU Telemetry Cache ---
struct SyntheticBar {
   double b_open; double b_high; double b_low; double b_close; double b_volume; datetime b_time;
};

int current_tick_id = 0;
SyntheticBar cache_m3[250]; int cache_m3_id[250];
SyntheticBar cache_m12[250]; int cache_m12_id[250];
SyntheticBar cache_m30[250]; int cache_m30_id[250];

// Memory for Trailing
double Basket_High_Water_Mark = -99999.0;

// Forward Declarations
void UpdateUI(double price, double ema, double vol_s, double m1_sqz, double rsi_m3, double rsi_m12, double adx, bool is_uptrend, double b_trig, double s_trig, 
              double macd_m, double macd_s, bool vol_ignite, bool m3_ok_trend, double mom_v, bool m1_struct_ok, bool m12_dist, bool m30_ok, double cur_dev_m12, double cur_dev_m3,
              bool rsi_ok, int spread, bool adx_ok, bool gravity_ok);
void DrawLabel(string name, int x, int y, string text, int size, color clr);
void DrawRect(string name, int x, int y, int w, int h, color bg_color);
bool CheckRisk();
void ManageGridExit();
void ManageGridRecovery();
int CountOrders(int type);
void OpenInitialTrade(int type);
bool ExecuteOrderClose(int ticket, double lots, int type, int slippage, color clr);
void CloseAllOrders();
double GetGridDistance();
SyntheticBar GetSyntheticBar(int period_min, int shift);
double GetSyntheticRSI(int period_min, int rsi_period, int shift);
double GetSyntheticEMA(int period_min, int ma_period, int shift);
double GetSyntheticVolMA(int period_min, int ma_period, int shift);
double GetSyntheticMACD(int period_min, int f, int s, int sig, int shift, int mode);
double GetSyntheticADX(int period_min, int adx_period, int shift);

//+------------------------------------------------------------------+
//| Initialization + Timer                                           |
//+------------------------------------------------------------------+
int OnInit() {
   EventSetTimer(1); 
   ObjectsDeleteAll(0, "LQ_"); 
   return(INIT_SUCCEEDED); 
}
void OnDeinit(const int r) { ObjectsDeleteAll(0, "LQ_"); EventKillTimer(); }
void OnTimer() { ChartRedraw(0); } 

extern bool Use_Time_Filter = false; 
extern int StartHour = 9;   
extern int EndHour   = 22;

//+------------------------------------------------------------------+
//| Main Logic                                                       |
//+------------------------------------------------------------------+
void OnTick() {
   current_tick_id++;
   
   // --- Ultimate Basket Clearance Lock ---
   if (Is_Force_Closing) {
       CloseAllOrders();
       if (CountOrders(OP_BUY) == 0 && CountOrders(OP_SELL) == 0) { Is_Force_Closing = false; Basket_High_Water_Mark = -99999.0; }
       return;
   }
   
   datetime current_time = TimeCurrent();
   int period_seconds = 3 * 60;
   int seconds_In = TimeSeconds(current_time) + TimeMinute(current_time) * 60 + TimeHour(current_time) * 3600;
   datetime current_m3_start = (datetime)(current_time - (seconds_In % period_seconds));
   
   if (current_m3_start != Last_M3_Time) {
      Last_M3_Time = current_m3_start;
      Order_Placed_In_Current_Bar = false; 
   }

   SyntheticBar M12_0 = GetSyntheticBar(12, 0); 
   SyntheticBar M12_1 = GetSyntheticBar(12, 1); 
   SyntheticBar M3_1 = GetSyntheticBar(3, 1);   
   
   double ema_m12 = GetSyntheticEMA(12, Trend_MA_Period, 0); 
   double ema_m3  = GetSyntheticEMA(3, Trend_MA_Period, 0); 
   double vol_ma_m3 = GetSyntheticVolMA(3, Vol_MA_Period, 1); 
   double rsi_m3 = GetSyntheticRSI(3, 14, 0);   
   double rsi_m12 = GetSyntheticRSI(12, 14, 0); 
   double adx_m30 = GetSyntheticADX(30, ADX_Period, 0);
   bool adx_ok = (adx_m30 > ADX_Min_Level);

   double ema_m30 = GetSyntheticEMA(30, 34, 0);
   double close_m30 = iClose(NULL, PERIOD_M1, 0);
   double m30_buf = M30_Buffer_Points * Point;
   bool m30_bull = (!Use_M30_Filter || close_m30 > (ema_m30 - m30_buf)); 
   bool m30_bear = (!Use_M30_Filter || close_m30 < (ema_m30 + m30_buf)); 

   bool is_uptrend = (M12_0.b_close > ema_m12);
   bool is_dntrend = (M12_0.b_close < ema_m12);
   bool is_sqz = (M3_1.b_volume < vol_ma_m3 * Vol_Squeeze_F); 
   
   bool m3_trend_up = (M3_1.b_close > GetSyntheticEMA(3, 34, 1));
   bool m3_trend_dn = (M3_1.b_close < GetSyntheticEMA(3, 34, 1));
   bool rsi_resonance_buy = (rsi_m3 < RSI_Buy_Max && rsi_m12 > 50 && rsi_m12 < RSI_M12_Limit); 
   bool rsi_resonance_sell = (rsi_m3 > RSI_Sell_Min && rsi_m12 < 50 && rsi_m12 > (100 - RSI_M12_Limit)); 
   bool momentum_up = !Use_Momentum || (M12_0.b_close > M12_1.b_close);
   bool momentum_dn = !Use_Momentum || (M12_0.b_close < M12_1.b_close);

   double vol_sum_m1 = 0;
   for(int k=1; k<=20; k++) vol_sum_m1 += (double)iVolume(NULL, PERIOD_M1, k);
   double vol_m1_avg = vol_sum_m1 / 20.0;    
   
   // --- Professional Vol Ignite Logic (Time-Proportional Surge) ---
   int elap_sec = (int)(TimeCurrent() % 60); 
   if(elap_sec < 5) elap_sec = 5; 
   double expected_vol = (vol_m1_avg / 60.0) * elap_sec;
   bool vol_ignite = !Use_Vol_Ignition || (Volume[0] > expected_vol * 1.5) || (iVolume(NULL, PERIOD_M1, 1) > vol_m1_avg * 1.3);
   bool m1_pre_sqz = !Use_M1_Structure || (iVolume(NULL, PERIOD_M1, 1) < vol_m1_avg * 1.3); 

   double buffer = Breakout_Buffer * Point;
   double eff_buf = (vol_ignite && Volume[0] > vol_m1_avg * 1.5) ? 0 : buffer;
   
   double buy_trigger, sell_trigger;
   if (Use_Shadow_Entry && iClose(NULL, PERIOD_M1, 1) > iOpen(NULL, PERIOD_M1, 1)) buy_trigger = iClose(NULL, PERIOD_M1, 1) + eff_buf; 
   else buy_trigger = iHigh(NULL, PERIOD_M1, 1) + eff_buf;
   
   if (Use_Shadow_Entry && iClose(NULL, PERIOD_M1, 1) < iOpen(NULL, PERIOD_M1, 1)) sell_trigger = iClose(NULL, PERIOD_M1, 1) - eff_buf;
   else sell_trigger = iLow(NULL, PERIOD_M1, 1) - eff_buf;
   
   double m12_macd_main = GetSyntheticMACD(12, 12, 26, 9, 0, MODE_MAIN);
   double m12_macd_sig  = GetSyntheticMACD(12, 12, 26, 9, 0, MODE_SIGNAL);
   bool macd_buy_ok  = !Use_MACD_Filter || (m12_macd_main > m12_macd_sig); 
   bool macd_sell_ok = !Use_MACD_Filter || (m12_macd_main < m12_macd_sig);

   double cur_dev_m12 = MathAbs(M12_0.b_close - ema_m12) / Point;
   double cur_dev_m3  = MathAbs(M12_0.b_close - ema_m3) / Point; 
   
   bool ui_m30_sync = (is_uptrend && m30_bull) || (is_dntrend && m30_bear);
   bool ui_m3_sync = (is_uptrend && m3_trend_up) || (is_dntrend && m3_trend_dn);
   bool ui_mom_ok = (is_uptrend && momentum_up) || (is_dntrend && momentum_dn);
   bool rsi_ok = (is_uptrend ? rsi_resonance_buy : rsi_resonance_sell);
   int spread = (int)MarketInfo(Symbol(), MODE_SPREAD);
   bool spread_ok = (spread <= Max_Spread_Point);
   bool grav_ok = (cur_dev_m12 < Max_Dev_From_MA && cur_dev_m3 < Max_Dev_From_M3);
   bool ui_macd_ok = (is_uptrend ? macd_buy_ok : macd_sell_ok);

   double vol_r = expected_vol > 0 ? Volume[0] / expected_vol : 0;
   double m1_sqz_r = vol_m1_avg > 0 ? (double)iVolume(NULL, PERIOD_M1, 1) / vol_m1_avg : 0;
   double mom_v = M12_0.b_close - M12_1.b_close;
   
   UpdateUI(M12_0.b_close, ema_m12, vol_r, m1_sqz_r, rsi_m3, rsi_m12, adx_m30, is_uptrend, buy_trigger, sell_trigger, 
            m12_macd_main, m12_macd_sig, vol_ignite, ui_m3_sync, mom_v, m1_pre_sqz, is_uptrend, ui_m30_sync, cur_dev_m12, cur_dev_m3, rsi_ok, spread, adx_ok, grav_ok);

   if(CheckRisk()) return;      
   ManageGridExit();           
   ManageGridRecovery();        

   if (Use_MACD_Exit) {
       double profit = 0; int type = -1; int cnt = 0;
       for(int i=0; i<OrdersTotal(); i++) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
           profit += OrderProfit() + OrderSwap() + OrderCommission();
           type = OrderType(); cnt++;
       }
       if (cnt > 0 && profit > MACD_Exit_Min_Profit) {
           if (type == OP_BUY && m12_macd_main < m12_macd_sig) { Is_Force_Closing = true; CloseAllOrders(); return; }
           if (type == OP_SELL && m12_macd_main > m12_macd_sig) { Is_Force_Closing = true; CloseAllOrders(); return; }
       }
   }

   if (CountOrders(0) > 0 || CountOrders(1) > 0) return; 
   Basket_High_Water_Mark = -99999.0;

   int hour = TimeHour(TimeCurrent());
   if (Use_Time_Filter && (hour < StartHour || hour >= EndHour)) return; 
   
   bool strict_buy  = is_uptrend && m3_trend_up && m30_bull && macd_buy_ok && vol_ignite && m1_pre_sqz;
   bool strict_sell = is_dntrend && m3_trend_dn && m30_bear && macd_sell_ok && vol_ignite && m1_pre_sqz;  
   
   if (current_m3_start == Last_M3_Time && !Order_Placed_In_Current_Bar) { 
       if (spread > Max_Spread_Point) return;
       bool near_ma_buy = (buy_trigger - ema_m12) < Max_Dev_From_MA * Point && (buy_trigger - ema_m3) < Max_Dev_From_M3 * Point;
       bool near_ma_sell = (ema_m12 - sell_trigger) < Max_Dev_From_MA * Point && (ema_m3 - sell_trigger) < Max_Dev_From_M3 * Point;
       
       if (Ask >= buy_trigger && strict_buy && adx_ok && momentum_up && is_sqz && rsi_resonance_buy && near_ma_buy) {
          OpenInitialTrade(0); Order_Placed_In_Current_Bar = true; 
       }
       else if (Bid <= sell_trigger && strict_sell && adx_ok && momentum_dn && is_sqz && rsi_resonance_sell && near_ma_sell) {
          OpenInitialTrade(1); Order_Placed_In_Current_Bar = true; 
       }
   }
}

//+------------------------------------------------------------------+
//| Helpers                                                          |
//+------------------------------------------------------------------+
void ManageGridExit() {
    double total_profit = 0; int cnt = 0;
    for(int i=0; i<OrdersTotal(); i++) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
        total_profit += OrderProfit() + OrderSwap() + OrderCommission(); cnt++;
    }
    if (cnt == 0) return;
    if (total_profit >= Basket_Target_USD) { Is_Force_Closing = true; CloseAllOrders(); return; }
    if (Use_Basket_Trail) {
        if (Basket_High_Water_Mark == -99999.0) Basket_High_Water_Mark = 0;
        if (total_profit >= Basket_Trail_Start) {
            if (total_profit > Basket_High_Water_Mark) Basket_High_Water_Mark = total_profit;
            double c_step = (total_profit >= Basket_Trend_Start) ? Basket_Trend_Step : Basket_Trail_Step;
            if (total_profit < (Basket_High_Water_Mark - c_step)) { Is_Force_Closing = true; CloseAllOrders(); return; }
        }
    }
}

void ManageGridRecovery() {
    if (!Use_Grid_Recovery) return;
    int cnt = 0; int type = -1; double last_price = 0; double last_lot = 0;
    for(int i=OrdersTotal()-1; i>=0; i--) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
        if (cnt == 0) { last_price = OrderOpenPrice(); last_lot = OrderLots(); type = OrderType(); }
        cnt++;
    }
    if (cnt >= Max_Grid_Layers || cnt == 0) return; 
    
    // Core Small-Capital Defense: Stop expanding grid if margin is critically low
    if (AccountMargin() > 0 && (AccountEquity() / AccountMargin()) * 100.0 < Min_Margin_Level) {
        Print("Grid Blocked: Margin Level below ", Min_Margin_Level, "% (Current: ", DoubleToString((AccountEquity()/AccountMargin())*100.0, 1), "%)");
        return; 
    }
    
    double grid_dist = GetGridDistance();
    
    // Core Small-Capital Snowball: Calculate base lot dynamically
    double base_lot = (!Use_Auto_Lot) ? Fixed_Lot : NormalizeDouble(AccountBalance() / 1000.0 * 0.01 * Auto_Lot_Risk, 2);
    if(base_lot < 0.01) base_lot = 0.01;
    
    // Core Small-Capital Fix: Geometric Progression to prevent 0.01 rounding stagnation
    double next_lot = NormalizeDouble(base_lot * MathPow(Lot_Multi, cnt), 2);
    if (next_lot < 0.01) next_lot = 0.01;
    
    if (AccountFreeMargin() < MarketInfo(Symbol(), MODE_MARGINREQUIRED) * next_lot) {
        Print("Grid Blocked: Insufficient Free Margin."); return;
    }
    
    if (type == OP_BUY && (last_price - Ask) >= grid_dist) {
        int t = -1; int retries = 0;
        RefreshRates();
        while(t < 0 && retries < 3) {
           t = OrderSend(Symbol(), OP_BUY, next_lot, MarketInfo(Symbol(), MODE_ASK), Max_Slippage_Points, 0, 0, sComm+"_L"+IntegerToString(cnt+1), Magic, 0, clrBlue);
           if (t < 0) { retries++; Sleep(100); RefreshRates(); }
        }
        if(t < 0) Print("Grid Buy failed after 3 retries: ", GetLastError());
    } else if (type == OP_SELL && (Bid - last_price) >= grid_dist) {
        int t = -1; int retries = 0;
        RefreshRates();
        while(t < 0 && retries < 3) {
           t = OrderSend(Symbol(), OP_SELL, next_lot, MarketInfo(Symbol(), MODE_BID), Max_Slippage_Points, 0, 0, sComm+"_L"+IntegerToString(cnt+1), Magic, 0, clrRed);
           if (t < 0) { retries++; Sleep(100); RefreshRates(); }
        }
        if(t < 0) Print("Grid Sell failed after 3 retries: ", GetLastError());
    }
}

double GetGridDistance() {
   if(Use_ATR_Grid) {
      double dist = iATR(NULL, 0, ATR_Period, 0) * ATR_Multi;
      return (dist < Fix_Dist * Point) ? (double)Fix_Dist * Point : dist;
   }
   return (double)Fix_Dist * Point;
}

bool ExecuteOrderClose(int ticket, double lots, int type, int slippage, color clr) {
    if (ticket <= 0 || lots <= 0) return false; // Defend against Error 131/108
    bool res = false; int retries = 0;
    RefreshRates();
    double price = (type == OP_BUY) ? MarketInfo(Symbol(), MODE_BID) : MarketInfo(Symbol(), MODE_ASK);
    while(!res && retries < 3) {
       res = OrderClose(ticket, lots, price, Max_Slippage_Points, clr); // Use global slip
       if(!res) { retries++; Sleep(100); RefreshRates(); price = (type == OP_BUY) ? MarketInfo(Symbol(), MODE_BID) : MarketInfo(Symbol(), MODE_ASK); }
    }
    return res;
}

void CloseAllOrders() {
    for(int i=OrdersTotal()-1; i>=0; i--) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
        bool res = ExecuteOrderClose(OrderTicket(), OrderLots(), OrderType(), Max_Slippage_Points, clrGray);
        if(!res) Print("OrderClose failed after retries: Ticket ", OrderTicket(), " Error: ", GetLastError());
    }
}

void OpenInitialTrade(int type) {
    // Core Small-Capital Snowball: Calculate base lot dynamically
    double base_lot = (!Use_Auto_Lot) ? Fixed_Lot : NormalizeDouble(AccountBalance() / 1000.0 * 0.01 * Auto_Lot_Risk, 2);
    if(base_lot < 0.01) base_lot = 0.01;
    
    double lot_size = NormalizeDouble(base_lot, 2);
    if (lot_size <= 0) lot_size = 0.01;
    
    if (AccountFreeMargin() < MarketInfo(Symbol(), MODE_MARGINREQUIRED) * lot_size) { 
        Print("Margin Dynamic Block: Free=", AccountFreeMargin(), " Required=", MarketInfo(Symbol(), MODE_MARGINREQUIRED) * lot_size); 
        return; 
    }
    
    RefreshRates();
    double price = (type == 0) ? MarketInfo(Symbol(), MODE_ASK) : MarketInfo(Symbol(), MODE_BID);
    int t = -1; int retries = 0; 
    
    while(t < 0 && retries < 3) {
        t = OrderSend(Symbol(), (type == 0 ? OP_BUY : OP_SELL), lot_size, price, Max_Slippage_Points, 0, 0, sComm+"_L1", Magic, 0, (type == 0 ? clrBlue : clrRed));
        if (t < 0) { retries++; Sleep(100); RefreshRates(); price = (type == 0) ? MarketInfo(Symbol(), MODE_ASK) : MarketInfo(Symbol(), MODE_BID); }
    }
    if(t < 0) Print("Initial Trade failed after 3 retries: ", GetLastError());
}

int CountOrders(int type) {
   int cnt = 0; for(int i=0; i<OrdersTotal(); i++) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic && OrderType() == type) cnt++;
   return cnt;
}

//+------------------------------------------------------------------+
//| Indicators                                                       |
//+------------------------------------------------------------------+
SyntheticBar GetSyntheticBar(int period_min, int shift) {
   if (shift >= 0 && shift < 250) {
      if (period_min == 3 && cache_m3_id[shift] == current_tick_id) return cache_m3[shift];
      if (period_min == 12 && cache_m12_id[shift] == current_tick_id) return cache_m12[shift];
      if (period_min == 30 && cache_m30_id[shift] == current_tick_id) return cache_m30[shift];
   }

   SyntheticBar bar; bar.b_open=0; bar.b_high=0; bar.b_low=999999; bar.b_close=0; bar.b_volume=0; bar.b_time=0;
   int period_seconds = period_min * 60;
   // --- MT4 Standard Alignment: Epoch-based ---
   datetime current_time = Time[0];
   datetime target_start_time = (datetime)((current_time / period_seconds) * period_seconds - (shift * period_seconds));
   datetime target_end_time   = (datetime)(target_start_time + period_seconds);
   
   int start_idx = iBarShift(NULL, PERIOD_M1, target_start_time, false);
   if (start_idx != -1) {
       bool is_first = true;
       for (int i = start_idx; i >= 0; i--) {
          datetime t = iTime(NULL, PERIOD_M1, i);
          if (t >= target_end_time) break;      // Stopped crossing into future periods
          if (t < target_start_time) continue;  // Prevent prior period gap contamination

          if (is_first) { 
              bar.b_open = iOpen(NULL, PERIOD_M1, i); 
              bar.b_time = target_start_time; 
              is_first = false; 
          }
          if (iHigh(NULL, PERIOD_M1, i) > bar.b_high) bar.b_high = iHigh(NULL, PERIOD_M1, i);
          if (iLow(NULL, PERIOD_M1, i) < bar.b_low)   bar.b_low  = iLow(NULL, PERIOD_M1, i);
          bar.b_close = iClose(NULL, PERIOD_M1, i); 
          bar.b_volume += (double)iVolume(NULL, PERIOD_M1, i);
       }
       if(is_first) {
           int fallback = iBarShift(NULL, PERIOD_M1, target_start_time, false);
           if(fallback != -1) {
              bar.b_open = iClose(NULL, PERIOD_M1, fallback);
              bar.b_high = bar.b_open; bar.b_low = bar.b_open; bar.b_close = bar.b_open;
              bar.b_time = target_start_time;
           }
       }
   }
   
   if (shift >= 0 && shift < 250) {
      if (period_min == 3)  { 
          cache_m3[shift].b_open = bar.b_open; cache_m3[shift].b_high = bar.b_high; cache_m3[shift].b_low = bar.b_low; 
          cache_m3[shift].b_close = bar.b_close; cache_m3[shift].b_volume = bar.b_volume; cache_m3[shift].b_time = bar.b_time;
          cache_m3_id[shift] = current_tick_id; 
      }
      if (period_min == 12) { 
          cache_m12[shift].b_open = bar.b_open; cache_m12[shift].b_high = bar.b_high; cache_m12[shift].b_low = bar.b_low; 
          cache_m12[shift].b_close = bar.b_close; cache_m12[shift].b_volume = bar.b_volume; cache_m12[shift].b_time = bar.b_time;
          cache_m12_id[shift] = current_tick_id; 
      }
      if (period_min == 30) { 
          cache_m30[shift].b_open = bar.b_open; cache_m30[shift].b_high = bar.b_high; cache_m30[shift].b_low = bar.b_low; 
          cache_m30[shift].b_close = bar.b_close; cache_m30[shift].b_volume = bar.b_volume; cache_m30[shift].b_time = bar.b_time;
          cache_m30_id[shift] = current_tick_id; 
      }
   }
   return bar;
}

double GetSyntheticEMA(int period_min, int ma_period, int shift) { 
   double alpha = 2.0 / (ma_period + 1.0);
   int lookback = 100; // --- Deep Convergence for Pro Accuracy ---
   double ema = GetSyntheticBar(period_min, shift + lookback).b_close; 
   for(int i = lookback - 1; i >= 0; i--) {
      ema = (GetSyntheticBar(period_min, shift + i).b_close - ema) * alpha + ema;
   }
   return ema;
}
double GetSyntheticRSI(int period_min, int rsi_period, int shift) {
   double alpha = 1.0 / rsi_period;
   double g_ema = 0, l_ema = 0;
   int lookback = 100;
   
   // --- Professional 100-Bar Convergence Pass ---
   for(int i = lookback; i >= 0; i--) {
      double d = GetSyntheticBar(period_min, shift + i).b_close - GetSyntheticBar(period_min, shift + i + 1).b_close;
      double g = (d > 0) ? d : 0;
      double l = (d < 0) ? -d : 0;
      g_ema = (i == lookback) ? g : (g - g_ema) * alpha + g_ema;
      l_ema = (i == lookback) ? l : (l - l_ema) * alpha + l_ema;
   }
   return (g_ema + l_ema == 0) ? 50.0 : 100.0 * (g_ema / (g_ema + l_ema));
}

double GetSyntheticADX(int period_min, int adx_period, int shift) {
   double alpha = 1.0 / adx_period;
   double tr_ema = 0, dm_p_ema = 0, dm_m_ema = 0;
   int lookback = 100; 
   double dx_arr[105]; ArrayInitialize(dx_arr, 0.0);
   
   // --- Professional 100-Bar Convergence Pass ---
   for(int i = lookback; i >= 0; i--) {
      SyntheticBar b = GetSyntheticBar(period_min, shift + i);
      SyntheticBar bp = GetSyntheticBar(period_min, shift + i + 1);
      double tr = MathMax(b.b_high - b.b_low, MathMax(MathAbs(b.b_high - bp.b_close), MathAbs(b.b_low - bp.b_close)));
      double dp = (b.b_high - bp.b_high > bp.b_low - b.b_low) ? MathMax(b.b_high - bp.b_high, 0) : 0;
      double dm = (bp.b_low - b.b_low > b.b_high - bp.b_high) ? MathMax(bp.b_low - b.b_low, 0) : 0;
      
      tr_ema = (i == lookback) ? tr : (tr - tr_ema) * alpha + tr_ema;
      dm_p_ema = (i == lookback) ? dp : (dp - dm_p_ema) * alpha + dm_p_ema;
      dm_m_ema = (i == lookback) ? dm : (dm - dm_m_ema) * alpha + dm_m_ema;
      
      if (tr_ema == 0) { dx_arr[i] = 0; continue; }
      double di_p = 100.0 * dm_p_ema / tr_ema;
      double di_m = 100.0 * dm_m_ema / tr_ema;
      dx_arr[i] = (di_p + di_m == 0) ? 0 : 100.0 * MathAbs(di_p - di_m) / (di_p + di_m);
   }
   
   // --- Second-Order Smoothing for ADX itself ---
   double adx = 0;
   for(int i = lookback; i >= 0; i--) {
      adx = (i == lookback) ? dx_arr[i] : (dx_arr[i] - adx) * alpha + adx;
   }
   return adx;
}
double GetSyntheticVolMA(int period_min, int ma_period, int shift) {
   double s=0; for(int i=0; i<ma_period; i++) s+=GetSyntheticBar(period_min, shift+i).b_volume; return s/ma_period;
}
double GetSyntheticMACD(int period_min, int f, int s, int sig, int shift, int mode) {
   double main = GetSyntheticEMA(period_min, f, shift) - GetSyntheticEMA(period_min, s, shift);
   if (mode == MODE_MAIN) return main;
   
   // Signal: 9-period EMA of (Fast - Slow)
   double alpha = 2.0 / (sig + 1.0);
   int oldest = 100; // Deep convergence
   double signal = GetSyntheticEMA(period_min, f, shift + oldest) - GetSyntheticEMA(period_min, s, shift + oldest);
   for(int i = oldest - 1; i >= 0; i--) {
      double m_val = GetSyntheticEMA(period_min, f, shift + i) - GetSyntheticEMA(period_min, s, shift + i);
      signal = (m_val - signal) * alpha + signal;
   }
   return signal;
}

bool CheckRisk() { 
   double bal = AccountBalance();
   if (AccountEquity() <= 0 || bal <= 0) return true;
   if ((bal - AccountEquity()) / bal * 100.0 > Max_Drawdown) { Is_Force_Closing = true; CloseAllOrders(); return true; }
   return false;
}

void UpdateUI(double price, double ema, double vol_s, double m1_sqz, double rsi_m3, double rsi_m12, double adx, bool is_uptrend, double b_trig, double s_trig, 
              double macd_m, double macd_s, bool vol_ignite, bool m3_ok_trend, double mom_v, bool m1_struct_ok, bool bull, bool m30_ok, double cur_dev_m12, double cur_dev_m3,
              bool rsi_ok, int spread, bool adx_ok, bool gravity_ok) {

   color bg = clrDarkSlateGray; DrawRect("LQ_BG", 5, 5, 230, 420, bg); 
   DrawLabel("LQ_Title", 15, 12, "LiQiyu V9.14 COMMAND CENTER", 9, clrGold);
   
   int ords = CountOrders(OP_BUY) + CountOrders(OP_SELL);
   double prof = 0; for(int i=0; i<OrdersTotal(); i++) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) prof += OrderProfit() + OrderSwap() + OrderCommission();
   
   // --- Row 1: Status & Profit ---
   DrawLabel("LQ_Grid", 15, 35, "Status: " + (ords > 0 ? "LIVE ("+IntegerToString(ords)+"L)" : "HUNTING"), 9, ords > 0 ? clrOrange : clrSpringGreen); 
   DrawLabel("LQ_Prof", 15, 50, "Profit: $" + DoubleToString(prof, 2), 11, prof > 0 ? clrLime : (prof < 0 ? clrRed : clrSilver)); 

   // --- Row 2: Exit Logic ---
   string tp_strat = (prof >= Basket_Trend_Start) ? "SUPER TREND" : (prof >= Basket_Trail_Start ? "TRAILING" : "STANDARD");
   double lock_val = (Basket_High_Water_Mark > 0) ? (Basket_High_Water_Mark - ((prof >= Basket_Trend_Start) ? Basket_Trend_Step : Basket_Trail_Step)) : 0;
   DrawLabel("LQ_TP_Info", 15, 70, "Exit: " + tp_strat + (ords > 0 && prof >= Basket_Trail_Start ? " (LOCK: $" + DoubleToString(lock_val, 1) + ")" : ""), 8, clrGold);

   // --- Row 2.5: Risk Indicator ---
   double m_level = (AccountMargin() > 0) ? (AccountEquity() / AccountMargin()) * 100.0 : 9999.0;
   color r_clr = (m_level < Min_Margin_Level) ? clrOrangeRed : clrMediumSpringGreen;
   string lot_str = Use_Auto_Lot ? ("AUTO (" + DoubleToString(Auto_Lot_Risk,1) + "x)") : "FIXED";
   DrawLabel("LQ_Risk", 15, 85, "Risk: Mgn " + DoubleToString(m_level, 0) + "% | " + lot_str, 8, r_clr);

   // --- Row 3: Signal Telemetry (Full Data) ---
   int y = 110;
   DrawLabel("LQ_C_Title", 15, y, "SIGNAL TELEMETRY (LIVE)", 8, clrCyan);
   
   y += 15; DrawLabel("LQ_C1", 15, y, "[1] Trend: " + (bull ? "BULL" : "BEAR"), 8, bull ? clrDeepSkyBlue : clrOrangeRed);
   y += 15; 
   DrawLabel("LQ_C2", 15,  y, "[2] M30 Sync", 7, m30_ok ? clrSpringGreen : clrGray);
   DrawLabel("LQ_C3", 115, y, "[3] M3 Sync",  7, m3_ok_trend ? clrSpringGreen : clrGray);
   
   y += 13;
   DrawLabel("LQ_C4", 15,  y, "[4] MACD: " + DoubleToString(macd_m-macd_s, 2), 7, (bull?macd_m>macd_s:macd_m<macd_s) ? clrSpringGreen : clrGray);
   DrawLabel("LQ_C5", 115, y, "[5] RSI: " + DoubleToString(rsi_m3,0) + "/" + DoubleToString(rsi_m12,0), 7, rsi_ok ? clrSpringGreen : clrGray);
   
   y += 13;
   DrawLabel("LQ_C6", 15,  y, "[6] ADX: " + DoubleToString(adx, 1), 7, adx_ok ? clrSpringGreen : clrGray);
   DrawLabel("LQ_C7", 115, y, "[7] Mom: " + DoubleToString(mom_v/Point, 0), 7, (bull?mom_v>0:mom_v<0) ? clrSpringGreen : clrGray);
   
   y += 13;
   DrawLabel("LQ_C8", 15,  y, "[8] Ignit: " + DoubleToString(vol_s, 1) + "x", 7, vol_ignite ? clrSpringGreen : clrGray);
   DrawLabel("LQ_C9", 115, y, "[9] Sqz: " + DoubleToString(m1_sqz, 1) + "x", 7, m1_struct_ok ? clrSpringGreen : clrGray);
   
   y += 13;
   DrawLabel("LQ_C10", 15,  y, "[10] Spread: " + (string)spread, 7, (spread <= Max_Spread_Point) ? clrSpringGreen : clrRed);
   DrawLabel("LQ_C11", 115, y, "[11] Grav OK", 7, gravity_ok ? clrSpringGreen : clrRed);

   // --- Row 4: Gravity Matrix ---
   y += 25;
   DrawLabel("LQ_G_Detail", 15, y, "Gravity Matrix:", 7, clrSilver);
   y += 12;
   DrawLabel("LQ_G12", 20, y, "M12 Dev: " + DoubleToString(cur_dev_m12, 0) + "/" + (string)Max_Dev_From_MA, 7, cur_dev_m12 < Max_Dev_From_MA ? clrSpringGreen : clrRed);
   DrawLabel("LQ_G3", 120, y, "M3 Dev: " + DoubleToString(cur_dev_m3, 0) + "/400", 7, cur_dev_m3 < 400 ? clrSpringGreen : clrRed);

   // --- Row 5: Trigger Logic ---
   y += 35;
   double dst = bull ? (b_trig - Ask)/Point : (Bid - s_trig)/Point;
   DrawLabel("LQ_Trig_T", 15, y, "ACTIVE TRIGGER (Shadow Strike):", 8, clrCyan);
   y += 15;
   string t_msg = (bull ? "BUY > " : "SELL < ") + DoubleToString(bull?b_trig:s_trig, Digits) + " (" + DoubleToString(dst, 0) + " pts)";
   DrawLabel("LQ_Trig", 15, y, t_msg, 9, dst <= 0 ? clrSpringGreen : (bull ? clrDeepSkyBlue : clrOrangeRed));

   string sys_msg = (ords > 0 ? "MANAGING..." : (dst <= 0 ? (gravity_ok ? "READY!" : "HOLD (GRAVITY)") : "HUNTING..."));
   DrawLabel("LQ_ST", 15, 400, "SYSTEM: " + sys_msg, 9, (ords>0 || (dst<=0 && gravity_ok)) ? clrYellow : clrDeepSkyBlue);
   ChartRedraw(0);
}

void DrawLabel(string name, int x, int y, string text, int size, color clr) {
   if(ObjectFind(0, name) < 0) { ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0); ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER); }
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x); ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, name, OBJPROP_TEXT, text); ObjectSetInteger(0, name, OBJPROP_FONTSIZE, size); ObjectSetInteger(0, name, OBJPROP_COLOR, clr);
}
void DrawRect(string name, int x, int y, int w, int h, color bg) {
   if(ObjectFind(0, name) < 0) { ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0); ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER); }
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, x); ObjectSetInteger(0, name, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, w); ObjectSetInteger(0, name, OBJPROP_YSIZE, h); ObjectSetInteger(0, name, OBJPROP_BGCOLOR, bg);
}
