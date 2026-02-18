//+------------------------------------------------------------------+
//|                                  LiQiyu_Strategy_V9.2_Rolling.mq4|
//|                    Precision Entry + Rolling Profit (Basket Trail) |
//+------------------------------------------------------------------+
#property copyright "Li Qiyu Quant Labs"
#property version   "9.20"
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

// --- V9.2 Rolling Profit Settings ---
extern string _R_ = "=== Rolling Profit (Trail) ===";
extern bool   Use_Basket_Trail   = true;  // Enable Rolling Profit
extern double Basket_Trail_Start = 5.0;   // Trigger (Was 8, $5 is faster/safer)
extern double Basket_Trail_Step  = 2.0;   // Retrace (Allow $2 retrace -> Lock $3)
extern double Basket_Target_USD  = 50.0;  // Hard Cap (Grand Slam)

extern int    Max_Spread_Point = 50;  

// --- Strategy Parameters (V8.7 Precision Entry) ---
extern string _P_ = "=== Entry V8.7 (Precision) ===";
extern int    Trend_MA_Period = 34;   
extern double Vol_Squeeze_F   = 1.0; // Standard 
extern int    Vol_MA_Period   = 20;   
extern int    RSI_Buy_Max     = 75;   
extern int    RSI_Sell_Min    = 25;   
extern int    Breakout_Buffer = 10;   
extern bool   Use_Momentum    = true; 
extern bool   Use_MACD_Filter = true; 
extern bool   Use_Vol_Ignition= true; 
extern bool   Use_M1_Structure= true; 
extern int    ADX_Period      = 14;   
extern int    ADX_Min_Level   = 15;   
extern bool   Use_M30_Filter  = true; // M30 Filter (Safety)
extern int    M30_Buffer_Points = 20; 

// --- Global Variables ---
int    Magic  = 2026920; // V9.2 Magic
string sComm  = "LQ_V9.2_Roll";
datetime Last_M3_Time = 0;
bool   Order_Placed_In_Current_Bar = false; 

// V9.2 Rolling Profit Memory
double Basket_High_Water_Mark = -99999.0; // Track highest profit

struct SyntheticBar {
   double b_open; double b_high; double b_low; double b_close; double b_volume; datetime b_time;
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

extern bool Use_Time_Filter = false; 
extern int StartHour = 9;   
extern int EndHour   = 22;

//+------------------------------------------------------------------+
//| Main Logic                                                       |
//+------------------------------------------------------------------+
void OnTick() {
   if(CheckRisk()) return;      
   ManageGridExit();            // Rolling Profit Logic Here
   ManageGridRecovery();        

   if (CountOrders(0) > 0 || CountOrders(1) > 0) return; 

   // Reset High Water Mark when basket is empty
   Basket_High_Water_Mark = -99999.0;

   // --- V8.7 Entry Logic ---
   int hour = TimeHour(TimeCurrent());
   if (Use_Time_Filter && (hour < StartHour || hour >= EndHour)) return; 

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
   
   double m12_macd_main = GetSyntheticMACD(12, 12, 26, 9, 0, MODE_MAIN);
   double m12_macd_sig  = GetSyntheticMACD(12, 12, 26, 9, 0, MODE_SIGNAL);
   bool macd_buy_ok  = !Use_MACD_Filter || (m12_macd_main > m12_macd_sig); 
   bool macd_sell_ok = !Use_MACD_Filter || (m12_macd_main < m12_macd_sig);

   double vol_sum_m1 = 0;
   for(int k=1; k<=20; k++) vol_sum_m1 += iVolume(NULL, PERIOD_M1, k);
   double vol_m1_avg = vol_sum_m1 / 20.0; 
   bool vol_ignite = !Use_Vol_Ignition || (Volume[0] > vol_m1_avg * 1.0); 
   if (Vol_Squeeze_F >= 0.8) vol_ignite = (Volume[0] > vol_m1_avg * 0.8); 
   bool m1_pre_sqz = !Use_M1_Structure || (iVolume(NULL, PERIOD_M1, 1) < vol_m1_avg * 1.3); 

   bool strict_buy  = is_uptrend && m3_trend_up && m30_bull && macd_buy_ok && vol_ignite && m1_pre_sqz;
   bool strict_sell = is_dntrend && m3_trend_dn && m30_bear && macd_sell_ok && vol_ignite && m1_pre_sqz;  
   
   int spread = (int)MarketInfo(Symbol(), MODE_SPREAD);
   
   if (current_m3_start == Last_M3_Time && !Order_Placed_In_Current_Bar) { 
       if (spread > Max_Spread_Point) return;
       if (Ask >= buy_trigger && strict_buy && adx_ok && momentum_up && is_sqz && rsi_resonance_buy) {
          OpenInitialTrade(0); Order_Placed_In_Current_Bar = true; 
       }
       else if (Bid <= sell_trigger && strict_sell && adx_ok && momentum_dn && is_sqz && rsi_resonance_sell) {
          OpenInitialTrade(1); Order_Placed_In_Current_Bar = true; 
       }
   }
   
   bool ui_m30_sync = (is_uptrend && m30_bull) || (is_dntrend && m30_bear);
   bool ui_m3_sync = (is_uptrend && m3_trend_up) || (is_dntrend && m3_trend_dn);
   bool ui_mom_ok = (is_uptrend && momentum_up) || (is_dntrend && momentum_dn);
   UpdateUI(M12_0.b_close, ema_m12, M3_1.b_volume, vol_ma_m3, rsi_m3, rsi_m12, adx_m30, is_uptrend, buy_trigger, sell_trigger, macd_buy_ok, macd_sell_ok, vol_ignite, ui_m3_sync, ui_mom_ok, m1_pre_sqz, ui_m30_sync);
}

//+------------------------------------------------------------------+
//| V9.2 Rolling Profit Logic (Basket Trailing)                      |
//+------------------------------------------------------------------+
void ManageGridExit() {
    double total_profit = 0;
    int cnt = 0;
    
    for(int i=0; i<OrdersTotal(); i++) {
        if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
            total_profit += OrderProfit() + OrderSwap() + OrderCommission();
            cnt++;
        }
    }
    
    if (cnt == 0) return;

    // 1. Hard Target (Grand Slam)
    if (total_profit >= Basket_Target_USD) {
        Print("V9.2 Rolling: HIT HARD TARGET $", total_profit);
        CloseAllOrders();
        return;
    }

    // 2. Rolling Profit Logic
    if (Use_Basket_Trail) {
        // Init HWM if new
        if (Basket_High_Water_Mark == -99999.0) Basket_High_Water_Mark = 0;

        // Activation
        if (total_profit >= Basket_Trail_Start) {
            // Update High Water Mark
            if (total_profit > Basket_High_Water_Mark) {
                Basket_High_Water_Mark = total_profit;
            }
            
            // Check Trailing Exit (Profit retraced too much from High)
            // ex: High=$15, Step=$2. Exit if Profit < $13.
            if (total_profit < (Basket_High_Water_Mark - Basket_Trail_Step)) {
                Print("V9.2 Rolling: TRAILING EXIT! Profit: $", total_profit, " (High: $", Basket_High_Water_Mark, ")");
                CloseAllOrders();
            }
        }
    } else {
        // Legacy Exit (Fallback)
        if (total_profit >= 10.0) CloseAllOrders();
    }
}

void ManageGridRecovery() {
    if (!Use_Grid_Recovery) return;
    int cnt = 0; int type = -1; double last_price = 0; double last_lot = 0;
    for(int i=OrdersTotal()-1; i>=0; i--) { 
        if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
            if (cnt == 0) { last_price = OrderOpenPrice(); last_lot = OrderLots(); type = OrderType(); }
            cnt++;
        }
    }
    if (cnt >= Max_Grid_Layers || cnt == 0) return; 

    double grid_dist = GetGridDistance();
    double dist = 0;
    
    if (type == OP_BUY) {
        dist = (last_price - Ask) / Point; 
        if (dist >= grid_dist / Point) {
            double new_lot = NormalizeDouble(last_lot * Lot_Multi, 2); 
            int t = OrderSend(Symbol(), OP_BUY, new_lot, Ask, 3, 0, 0, sComm+"_L"+IntegerToString(cnt+1), Magic, 0, clrBlue);
        }
    }
    else if (type == OP_SELL) {
        dist = (Bid - last_price) / Point; 
        if (dist >= grid_dist / Point) {
            double new_lot = NormalizeDouble(last_lot * Lot_Multi, 2); 
            int t = OrderSend(Symbol(), OP_SELL, new_lot, Bid, 3, 0, 0, sComm+"_L"+IntegerToString(cnt+1), Magic, 0, clrRed);
        }
    }
}

double GetGridDistance() {
   if(Use_ATR_Grid) {
      double atr = iATR(NULL, 0, ATR_Period, 0); 
      double dist = atr * ATR_Multi;
      if(dist < Fix_Dist * Point) return Fix_Dist * Point;
      return dist;
   }
   return Fix_Dist * Point;
}

void CloseAllOrders() {
    for(int i=OrdersTotal()-1; i>=0; i--) {
        if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
            if(OrderType()==OP_BUY) OrderClose(OrderTicket(), OrderLots(), Bid, 3, clrGray);
            else OrderClose(OrderTicket(), OrderLots(), Ask, 3, clrGray);
        }
    }
}

void OpenInitialTrade(int type) {
    double lots = Fixed_Lot;
    if (AccountFreeMargin() < 10) return;
    int cmd = (type == 0) ? OP_BUY : OP_SELL;
    double price = (type == 0) ? Ask : Bid;
    color clr = (type == 0) ? clrBlue : clrRed;
    int t = OrderSend(Symbol(), cmd, lots, price, 3, 0, 0, sComm+"_L1", Magic, 0, clr);
    if(t > 0) Print("V9.2 Initial Trade. Grid+Roll Ready.");
}

//+------------------------------------------------------------------+
//| Synthetic Engine (Standard)                                      |
//+------------------------------------------------------------------+
SyntheticBar GetSyntheticBar(int period_min, int shift) {
   SyntheticBar bar; bar.b_open=0; bar.b_high=0; bar.b_low=999999; bar.b_close=0; bar.b_volume=0;
   datetime current_time = Time[0];
   int seconds_In = TimeSeconds(current_time) + TimeMinute(current_time) * 60 + TimeHour(current_time) * 3600;
   int period_seconds = period_min * 60;
   datetime start_time_0 = (datetime)(current_time - (seconds_In % period_seconds)); 
   datetime target_start_time = (datetime)(start_time_0 - (shift * period_seconds));
   datetime target_end_time   = (datetime)(target_start_time + period_seconds);
   int start_idx = iBarShift(NULL, PERIOD_M1, target_start_time, false);
   if (start_idx == -1) return bar; 
   bar.b_open = iOpen(NULL, PERIOD_M1, start_idx); bar.b_time = iTime(NULL, PERIOD_M1, start_idx);
   for (int i = start_idx; i >= 0; i--) {
      datetime t = iTime(NULL, PERIOD_M1, i);
      if (t >= target_end_time) break; if (t < target_start_time) continue; 
      if (iHigh(NULL, PERIOD_M1, i) > bar.b_high) bar.b_high = iHigh(NULL, PERIOD_M1, i);
      if (iLow(NULL, PERIOD_M1, i) < bar.b_low)   bar.b_low  = iLow(NULL, PERIOD_M1, i);
      bar.b_close = iClose(NULL, PERIOD_M1, i); bar.b_volume += iVolume(NULL, PERIOD_M1, i);
   }
   return bar;
}
double GetSyntheticRSI(int period_min, int rsi_period) {
   double gain_sum = 0; double loss_sum = 0;
   for (int i = 1; i <= rsi_period; i++) {
      SyntheticBar b_curr = GetSyntheticBar(period_min, i); SyntheticBar b_prev = GetSyntheticBar(period_min, i + 1);
      double diff = b_curr.b_close - b_prev.b_close;
      if (b_curr.b_close == 0 || b_prev.b_close == 0) continue; 
      if (diff > 0) gain_sum += diff; else loss_sum += -diff;
   }
   if (gain_sum + loss_sum == 0) return 50.0;
   return 100.0 * gain_sum / (gain_sum + loss_sum);
}
double GetSyntheticEMA(int period_min, int ma_period, int shift) {
   return iMA(NULL, PERIOD_M1, period_min * ma_period, 0, MODE_EMA, PRICE_CLOSE, shift * period_min);
}
double GetSyntheticVolMA(int period_min, int ma_period, int shift) {
   double sum = 0;
   for(int i=0; i<ma_period; i++) sum += GetSyntheticBar(period_min, shift + i).b_volume;
   return sum / ma_period;
}
double GetSyntheticMACD(int period_min, int fast_ema, int slow_ema, int signal_ema, int shift, int mode) {
   double fast = GetSyntheticEMA(period_min, fast_ema, shift);
   double slow = GetSyntheticEMA(period_min, slow_ema, shift);
   double main_line = fast - slow;
   if (mode == MODE_MAIN) return main_line;
   if (mode == MODE_SIGNAL) {
       double signal_sum = 0;
       for(int i=0; i<signal_ema; i++) signal_sum += (GetSyntheticEMA(period_min, fast_ema, shift + i) - GetSyntheticEMA(period_min, slow_ema, shift + i));
       return signal_sum / signal_ema;
   }
   return 0;
}
bool CheckRisk() {
   if (AccountEquity() <= 0) return true;
   if ((AccountBalance() - AccountEquity()) / AccountBalance() * 100 > Max_Drawdown) {
       CloseAllOrders(); return true;
   }
   return false;
}
int CountOrders(int type) {
   int cnt = 0;
   for(int i=0; i<OrdersTotal(); i++) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic && OrderType() == type) cnt++;
   return cnt;
}

//+------------------------------------------------------------------+
//| Dashboard Display (V9.2 Rolling)                                 |
//+------------------------------------------------------------------+
void UpdateUI(double price, double ema, double vol, double vol_ma, double rsi_m3, double rsi_m12, double adx, bool is_uptrend, double b_trig, double s_trig, bool macd_buy_ok, bool macd_sell_ok, bool vol_ignite, bool m3_ok_trend, bool mom_ok, bool m1_struct_ok, bool m30_ok) {

   Comment("");   
   color bg_color = clrBlack; 
   DrawRect("LQ_BG", 20, 20, 360, 520, bg_color); 

   DrawLabel("LQ_Title", 40, 40, "LiQiyu V9.2 ROLLING (Basket Trail)", 10, clrGold);

   int orders = CountOrders(OP_BUY) + CountOrders(OP_SELL);
   double open_prof = 0;
   for(int i=0; i<OrdersTotal(); i++) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) open_prof += OrderProfit();
   
   string g_txt = "Grid: " + (orders > 0 ? ("ACTIVE (" + IntegerToString(orders) + "L)") : "WAITING");
   DrawLabel("LQ_Grid", 40, 65, g_txt, 9, orders > 0 ? clrOrange : clrLime); 
   
   // --- V9.2 Rolling Status ---
   string p_txt = "Profit: $" + DoubleToString(open_prof, 2);
   color p_clr = open_prof > 0 ? clrLime : (open_prof < -10 ? clrRed : clrSilver);
   
   if (open_prof > Basket_Trail_Start && Basket_High_Water_Mark > 0) {
       // Trailing Active
       p_txt = p_txt + " (High: $" + DoubleToString(Basket_High_Water_Mark, 2) + " | Lock: $" + DoubleToString(Basket_High_Water_Mark - Basket_Trail_Step, 2) + ")";
       p_clr = clrGold; // Gold for activated trail
   } else {
       // Waiting for Trail
       p_txt = p_txt + " (Trail Start: $" + DoubleToString(Basket_Trail_Start, 2) + ")";
   }
   
   DrawLabel("LQ_Prof", 40, 85, p_txt, 9, p_clr); 
   
   // --- ENTRY FILTERS ---
   bool bull = (price > ema);
   string t_txt = "[1] M12 Trend: " + (bull ? "BULL" : "BEAR") + " | M30: " + (m30_ok ? "OK" : "Diff");
   DrawLabel("LQ_Trend", 40, 120, t_txt, 8, m30_ok ? (bull ? clrLime : clrRed) : clrGray);
   
   string m3t_txt = "    M3 Trend: " + (m3_ok_trend ? "Synced" : "Conflict");
   DrawLabel("LQ_M3T", 40, 135, m3t_txt, 8, m3_ok_trend ? clrLime : clrRed);

   bool adx_pass = (adx > ADX_Min_Level);
   string mom_txt = "[2] ADX: " + DoubleToString(adx, 1) + (adx_pass?"(OK)":"(Weak)") + " | Mom: " + (mom_ok?"Push":"Wait");
   DrawLabel("LQ_Mom", 40, 155, mom_txt, 8, (adx_pass && mom_ok) ? clrLime : clrGray);

   string v_txt = "[3] M3 Vol: " + (vol < vol_ma ? "Squeeze" : "High") + " | M1 Pre: " + (m1_struct_ok ? "OK" : "Noisy");
   DrawLabel("LQ_Vol", 40, 175, v_txt, 8, m1_struct_ok ? clrLime : clrGray);

   string vi_txt = "    M1 Ignition: " + (vol_ignite ? "IGNITED (GO)" : "Low Energy");
   DrawLabel("LQ_Ign", 40, 190, vi_txt, 8, vol_ignite ? clrLime : clrRed);

   bool m3_ok = (bull ? rsi_m3 < RSI_Buy_Max : rsi_m3 > RSI_Sell_Min);
   bool m12_ok = (bull ? rsi_m12 > 50 : rsi_m12 < 50);
   bool rsi_all_ok = m3_ok && m12_ok;
   
   string r_txt = "[4] RSI: " + DoubleToString(rsi_m3,1) + "/" + DoubleToString(rsi_m12,1) + (rsi_all_ok?" (Sync)":" (Wait)");
   DrawLabel("LQ_RSI", 40, 210, r_txt, 8, rsi_all_ok ? clrLime : clrRed); 

   string macd_txt = "    MACD: " + ((macd_buy_ok||macd_sell_ok) ? "Confirmed" : "Conflict");
   DrawLabel("LQ_MACD", 40, 225, macd_txt, 8, (macd_buy_ok||macd_sell_ok) ? clrLime : clrRed);

   double dist = 0;
   if (bull) {
       dist = (b_trig - Ask)/Point;
       string trig_txt = "BUY ZONE: > " + DoubleToString(b_trig, Digits) + " (Dist: " + DoubleToString(dist,0) + ")";
       DrawLabel("LQ_Trig", 40, 255, trig_txt, 9, dist <= 0 ? clrLime : clrDeepSkyBlue);
   } else {
       dist = (Bid - s_trig)/Point;
       string trig_txt = "SELL ZONE: < " + DoubleToString(s_trig, Digits) + " (Dist: " + DoubleToString(dist,0) + ")";
       DrawLabel("LQ_Trig", 40, 255, trig_txt, 9, dist <= 0 ? clrLime : clrOrangeRed);
   }

   string acc = "Equity: $" + DoubleToString(AccountEquity(), 2);
   DrawLabel("LQ_Acc", 40, 420, acc, 9, clrWhite);

   string st = "STATUS: " + (orders > 0 ? "MANAGING BASKET (ROLLING)..." : (dist<=0 ? "ZONE REACHED!" : "HUNTING ENTRY..."));
   DrawLabel("LQ_ST", 40, 440, st, 9, orders > 0 ? clrYellow : clrDeepSkyBlue);
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
   }
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, (long)x); ObjectSetInteger(0, name, OBJPROP_YDISTANCE, (long)y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, (long)w); ObjectSetInteger(0, name, OBJPROP_YSIZE, (long)h);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, (long)bg_color); ObjectSetInteger(0, name, OBJPROP_BACK, 0); 
}
