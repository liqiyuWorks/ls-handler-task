//+------------------------------------------------------------------+
//|                                  LiQiyu_Strategy_V9.14_Hyper.mq4 |
//|                    Hyper Shadow (Super Trend) + Gravity Pro      |
//+------------------------------------------------------------------+
#property copyright "Li Qiyu Quant Labs"
#property version   "9.140"
#property strict

extern string _S_ = "=== Protection (Hybrid) ===";
extern double Fixed_Lot      = 0.01;  // Base Lot Size
extern double Max_Drawdown   = 30.0;  // Hard Stop: 30% Equity Protection
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

extern int    Max_Spread_Point = 50;  

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

// Memory for Trailing
double Basket_High_Water_Mark = -99999.0; 

struct SyntheticBar {
   double b_open; double b_high; double b_low; double b_close; double b_volume; datetime b_time;
};

// Forward Declarations
void UpdateUI(double price, double ema, double vol, double vol_ma, double rsi_m3, double rsi_m12, double adx, bool is_uptrend, double b_trig, double s_trig, 
              bool macd_ok, bool vol_ignite, bool m3_ok_trend, bool mom_ok, bool m1_struct_ok, bool m30_ok, double cur_dev_m12, double cur_dev_m3, 
              bool rsi_ok, bool spread_ok, bool adx_ok, bool gravity_ok);
void DrawLabel(string name, int x, int y, string text, int size, color clr);
void DrawRect(string name, int x, int y, int w, int h, color bg_color);
bool CheckRisk();
void ManageGridExit();
void ManageGridRecovery();
int CountOrders(int type);
void OpenInitialTrade(int type);
void CloseAllOrders();
double GetGridDistance();
SyntheticBar GetSyntheticBar(int period_min, int shift);
double GetSyntheticRSI(int period_min, int rsi_period);
double GetSyntheticEMA(int period_min, int ma_period, int shift);
double GetSyntheticVolMA(int period_min, int ma_period, int shift);
double GetSyntheticMACD(int period_min, int fast_ema, int slow_ema, int signal_ema, int shift, int mode);

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
   bool rsi_resonance_buy = (rsi_m3 < RSI_Buy_Max && rsi_m12 > 50 && rsi_m12 < RSI_M12_Limit); 
   bool rsi_resonance_sell = (rsi_m3 > RSI_Sell_Min && rsi_m12 < 50 && rsi_m12 > (100 - RSI_M12_Limit)); 
   bool momentum_up = !Use_Momentum || (M12_0.b_close > M12_1.b_close);
   bool momentum_dn = !Use_Momentum || (M12_0.b_close < M12_1.b_close);

   double vol_sum_m1 = 0;
   for(int k=1; k<=20; k++) vol_sum_m1 += (double)iVolume(NULL, PERIOD_M1, k);
   double vol_m1_avg = vol_sum_m1 / 20.0; 
   bool vol_ignite = !Use_Vol_Ignition || (Volume[0] > vol_m1_avg * 1.0); 
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

   UpdateUI(M12_0.b_close, ema_m12, M3_1.b_volume, vol_ma_m3, rsi_m3, rsi_m12, adx_m30, is_uptrend, buy_trigger, sell_trigger, 
            ui_macd_ok, vol_ignite, ui_m3_sync, ui_mom_ok, m1_pre_sqz, ui_m30_sync, cur_dev_m12, cur_dev_m3, rsi_ok, spread_ok, adx_ok, grav_ok);

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
           if (type == OP_BUY && m12_macd_main < m12_macd_sig) { CloseAllOrders(); return; }
           if (type == OP_SELL && m12_macd_main > m12_macd_sig) { CloseAllOrders(); return; }
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
    if (total_profit >= Basket_Target_USD) { CloseAllOrders(); return; }
    if (Use_Basket_Trail) {
        if (Basket_High_Water_Mark == -99999.0) Basket_High_Water_Mark = 0;
        if (total_profit >= Basket_Trail_Start) {
            if (total_profit > Basket_High_Water_Mark) Basket_High_Water_Mark = total_profit;
            double c_step = (total_profit >= Basket_Trend_Start) ? Basket_Trend_Step : Basket_Trail_Step;
            if (total_profit < (Basket_High_Water_Mark - c_step)) CloseAllOrders();
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
    double grid_dist = GetGridDistance();
    if (type == OP_BUY && (last_price - Ask) / Point >= grid_dist / Point) {
        if(OrderSend(Symbol(), OP_BUY, NormalizeDouble(last_lot * Lot_Multi, 2), Ask, 10, 0, 0, sComm+"_L"+IntegerToString(cnt+1), Magic, 0, clrBlue) < 0) Print("Grid Buy failed: ", GetLastError());
    } else if (type == OP_SELL && (Bid - last_price) / Point >= grid_dist / Point) {
        if(OrderSend(Symbol(), OP_SELL, NormalizeDouble(last_lot * Lot_Multi, 2), Bid, 10, 0, 0, sComm+"_L"+IntegerToString(cnt+1), Magic, 0, clrRed) < 0) Print("Grid Sell failed: ", GetLastError());
    }
}

double GetGridDistance() {
   if(Use_ATR_Grid) {
      double dist = iATR(NULL, 0, ATR_Period, 0) * ATR_Multi;
      return (dist < Fix_Dist * Point) ? (double)Fix_Dist * Point : dist;
   }
   return (double)Fix_Dist * Point;
}

void CloseAllOrders() {
    for(int i=OrdersTotal()-1; i>=0; i--) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
        bool res = false;
        if(OrderType()==OP_BUY) res = OrderClose(OrderTicket(), OrderLots(), Bid, 10, clrGray);
        else res = OrderClose(OrderTicket(), OrderLots(), Ask, 10, clrGray);
        if(!res) Print("OrderClose failed: ", GetLastError());
    }
}

void OpenInitialTrade(int type) {
    if (AccountFreeMargin() < 10) return;
    double price = (type == 0) ? Ask : Bid;
    if(OrderSend(Symbol(), (type == 0 ? OP_BUY : OP_SELL), Fixed_Lot, price, 3, 0, 0, sComm+"_L1", Magic, 0, (type == 0 ? clrBlue : clrRed)) < 0)
        Print("Initial Trade failed: ", GetLastError());
}

int CountOrders(int type) {
   int cnt = 0; for(int i=0; i<OrdersTotal(); i++) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic && OrderType() == type) cnt++;
   return cnt;
}

//+------------------------------------------------------------------+
//| Indicators                                                       |
//+------------------------------------------------------------------+
SyntheticBar GetSyntheticBar(int period_min, int shift) {
   SyntheticBar bar; bar.b_open=0; bar.b_high=0; bar.b_low=999999; bar.b_close=0; bar.b_volume=0;
   datetime current_time = Time[0];
   int period_seconds = period_min * 60;
   datetime target_start_time = (datetime)(current_time - (TimeSeconds(current_time) + TimeMinute(current_time) * 60 + TimeHour(current_time) * 3600) % period_seconds - (shift * period_seconds));
   datetime target_end_time   = (datetime)(target_start_time + period_seconds);
   int start_idx = iBarShift(NULL, PERIOD_M1, target_start_time, false);
   if (start_idx == -1) return bar; 
   bar.b_open = iOpen(NULL, PERIOD_M1, start_idx); bar.b_time = iTime(NULL, PERIOD_M1, start_idx);
   for (int i = start_idx; i >= 0; i--) {
      datetime t = iTime(NULL, PERIOD_M1, i);
      if (t >= target_end_time) break;
      if (iHigh(NULL, PERIOD_M1, i) > bar.b_high) bar.b_high = iHigh(NULL, PERIOD_M1, i);
      if (iLow(NULL, PERIOD_M1, i) < bar.b_low)   bar.b_low  = iLow(NULL, PERIOD_M1, i);
      bar.b_close = iClose(NULL, PERIOD_M1, i); bar.b_volume += (double)iVolume(NULL, PERIOD_M1, i);
   }
   return bar;
}

double GetSyntheticEMA(int period_min, int ma_period, int shift) { return iMA(NULL, PERIOD_M1, period_min * ma_period, 0, MODE_EMA, PRICE_CLOSE, shift * period_min); }
double GetSyntheticRSI(int period_min, int rsi_period) {
   double g=0, l=0; for (int i=1; i<=rsi_period; i++) {
      double d = GetSyntheticBar(period_min, i).b_close - GetSyntheticBar(period_min, i+1).b_close;
      if (d>0) g+=d; else l+=-d;
   }
   return (g+l==0)?50.0:100.0*g/(g+l);
}
double GetSyntheticVolMA(int period_min, int ma_period, int shift) {
   double s=0; for(int i=0; i<ma_period; i++) s+=GetSyntheticBar(period_min, shift+i).b_volume; return s/ma_period;
}
double GetSyntheticMACD(int period_min, int f, int s, int sig, int shift, int mode) {
   if (mode==MODE_MAIN) return GetSyntheticEMA(period_min, f, shift) - GetSyntheticEMA(period_min, s, shift);
   double sum=0; for(int i=0; i<sig; i++) sum+=(GetSyntheticEMA(period_min, f, shift+i)-GetSyntheticEMA(period_min, s, shift+i)); return sum/sig;
}

bool CheckRisk() { 
   if (AccountEquity() <= 0) return true;
   if ((AccountBalance() - AccountEquity()) / AccountBalance() * 100 > Max_Drawdown) { CloseAllOrders(); return true; }
   return false;
}

void UpdateUI(double price, double ema, double vol, double vol_ma, double rsi_m3, double rsi_m12, double adx, bool is_uptrend, double b_trig, double s_trig, 
              bool macd_ok, bool vol_ignite, bool m3_ok_trend, bool mom_ok, bool m1_struct_ok, bool m30_ok, double cur_dev_m12, double cur_dev_m3,
              bool rsi_ok, bool spread_ok, bool adx_ok, bool gravity_ok) {

   color bg = clrDarkSlateGray; DrawRect("LQ_BG", 5, 5, 230, 380, bg); 
   DrawLabel("LQ_Title", 15, 12, "LiQiyu V9.14 COMMAND CENTER", 9, clrGold);
   
   int ords = CountOrders(OP_BUY) + CountOrders(OP_SELL);
   double prof = 0; for(int i=0; i<OrdersTotal(); i++) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) prof += OrderProfit() + OrderSwap() + OrderCommission();
   
   // --- Row 1: Trading Status ---
   DrawLabel("LQ_Grid", 15, 35, "Status: " + (ords > 0 ? "LIVE ("+IntegerToString(ords)+"L)" : "HUNTING"), 9, ords > 0 ? clrOrange : clrSpringGreen); 
   DrawLabel("LQ_Prof", 15, 50, "Profit: $" + DoubleToString(prof, 2), 11, prof > 0 ? clrLime : (prof < 0 ? clrRed : clrSilver)); 

   // --- Row 2: Strategy & Lock ---
   string tp_strat = (prof >= Basket_Trend_Start) ? "SUPER TREND" : (prof >= Basket_Trail_Start ? "TRAILING" : "STANDARD");
   double lock_val = (Basket_High_Water_Mark > 0) ? (Basket_High_Water_Mark - ((prof >= Basket_Trend_Start) ? Basket_Trend_Step : Basket_Trail_Step)) : 0;
   
   DrawLabel("LQ_TP_Info", 15, 70, "Exit: " + tp_strat + (ords > 0 && prof >= Basket_Trail_Start ? " (LOCK: $" + DoubleToString(lock_val, 1) + ")" : ""), 8, clrGold);

   // --- Row 2.5: Capital Risk ---
   double req_bal = 500.0;
   color r_clr = (AccountBalance() < req_bal) ? clrOrangeRed : clrMediumSpringGreen;
   DrawLabel("LQ_Risk", 15, 85, "Risk: " + (AccountBalance() < req_bal ? "SML-CAP (EX-HIGH)" : "SAFE-CAP (BALANCED)"), 7, r_clr);

   // --- Row 3: Entry Checklist ---
   int y_off = 110;
   DrawLabel("LQ_C_Title", 15, y_off, "SIGNAL CHECKLIST", 8, clrCyan);
   
   string c1 = "[1] M12 Trend: " + (is_uptrend ? "UP" : "DN"); y_off += 15;
   DrawLabel("LQ_C1", 15, y_off, c1, 8, is_uptrend ? clrDeepSkyBlue : clrOrangeRed);
   
   DrawLabel("LQ_C2", 15, y_off+15, "[2] M30 Sync", 7, m30_ok ? clrLime : clrGray);
   DrawLabel("LQ_C3", 100, y_off+15, "[3] M3 Sync", 7, m3_ok_trend ? clrLime : clrGray);
   
   DrawLabel("LQ_C4", 15, y_off+28, "[4] MACD Filter", 7, macd_ok ? clrLime : clrGray);
   DrawLabel("LQ_C5", 100, y_off+28, "[5] RSI Res", 7, rsi_ok ? clrLime : clrGray);
   
   DrawLabel("LQ_C6", 15, y_off+41, "[6] ADX Filter", 7, adx_ok ? clrLime : clrGray);
   DrawLabel("LQ_C7", 100, y_off+41, "[7] Mom Push", 7, mom_ok ? clrLime : clrGray);
   
   DrawLabel("LQ_C8", 15, y_off+54, "[8] Vol Ignite", 7, vol_ignite ? clrLime : clrGray);
   DrawLabel("LQ_C9", 100, y_off+54, "[9] M1 Squeeze", 7, m1_struct_ok ? clrLime : clrGray);
   
   DrawLabel("LQ_C10", 15, y_off+67, "[10] Spread OK", 7, spread_ok ? clrLime : clrRed);
   DrawLabel("LQ_C11", 100, y_off+67, "[11] Gravity", 7, gravity_ok ? clrLime : clrRed);

   // --- Row 4: Gravity Details ---
   y_off += 90;
   DrawLabel("LQ_G_Detail", 15, y_off, "Gravity Details:", 7, clrSilver);
   DrawLabel("LQ_G12", 20, y_off+12, "M12: " + DoubleToString(cur_dev_m12, 0) + "/1000", 7, cur_dev_m12 < 1000 ? clrLime : clrRed);
   DrawLabel("LQ_G3", 100, y_off+12, "M3: " + DoubleToString(cur_dev_m3, 0) + "/400", 7, cur_dev_m3 < 400 ? clrLime : clrRed);

   // --- Row 5: Trigger & Targets ---
   y_off += 40;
   bool bull = is_uptrend;
   double dst = bull ? (b_trig - Ask)/Point : (Bid - s_trig)/Point;
   DrawLabel("LQ_Trig_T", 15, y_off, "ACTIVE TRIGGER:", 8, clrCyan);
   DrawLabel("LQ_Trig", 15, y_off+15, (bull?"BUY > ":"SELL < ") + DoubleToString(bull?b_trig:s_trig, Digits) + " ("+DoubleToString(dst,0)+")", 9, dst <= 0 ? clrLime : (bull?clrDeepSkyBlue:clrOrangeRed));

   string sys_msg = (ords > 0 ? "MANAGING..." : (dst <= 0 ? (gravity_ok ? "READY!" : "HOLD (GRAVITY)") : "HUNTING..."));
   DrawLabel("LQ_ST", 15, 360, "SYSTEM: " + sys_msg, 9, (ords>0 || (dst<=0 && gravity_ok)) ? clrYellow : clrDeepSkyBlue);
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
