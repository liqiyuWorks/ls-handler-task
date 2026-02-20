//+------------------------------------------------------------------+
//|                                  LiQiyu_Strategy_V9.4_Smart.mq4 |
//|                    Precision Entry + Adaptive Trend Trailing      |
//+------------------------------------------------------------------+
#property copyright "Li Qiyu Quant Labs"
#property version   "9.110"
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

// --- V9.4 Accelerated Trail (Adaptive) ---
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

// --- Strategy Parameters (V8.7 Precision Entry) ---
extern string _P_ = "=== Entry V8.7 (Precision) ===";
extern int    Trend_MA_Period = 34;   
extern double Vol_Squeeze_F   = 1.0; 
extern int    Vol_MA_Period   = 20;   
extern int    RSI_Buy_Max     = 70;   // Balanced: Return to Classic 70 (Was 68)
extern int    RSI_Sell_Min    = 30;   // Balanced: Return to Classic 30 (Was 32)
extern int    RSI_M12_Limit   = 80;   // Balanced: M12 Limit 80 (Was 75, give more room)
extern int    Max_Dev_From_MA = 350;  // Gravity Macro: Don't buy if >$3.5 from M12 MA
extern int    Max_Dev_From_M3 = 250;  // Gravity Micro: Relaxed to $2.5 (Was $1.5)
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
string sComm  = "LQ_V9.11_Balanced";
datetime Last_M3_Time = 0;
bool   Order_Placed_In_Current_Bar = false; 

// Memory for Trailing
double Basket_High_Water_Mark = -99999.0; 

struct SyntheticBar {
   double b_open; double b_high; double b_low; double b_close; double b_volume; datetime b_time;
};

//+------------------------------------------------------------------+
//| Initialization + Timer                                           |
//+------------------------------------------------------------------+
int OnInit() {
   EventSetTimer(1); 
   ObjectsDeleteAll(0, "LQ_"); 
   return(INIT_SUCCEEDED); 
}
void OnDeinit(const int r) { ObjectsDeleteAll(0, "LQ_"); EventKillTimer(); }
void OnTimer() { ChartRedraw(0); } // Force redraw every second

extern bool Use_Time_Filter = false; 
extern int StartHour = 9;   
extern int EndHour   = 22;
//+------------------------------------------------------------------+
//| Main Logic                                                       |
//+------------------------------------------------------------------+
void OnTick() {
   // --- ALWAYS Update Indicators First ---
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
   double ema_m3  = GetSyntheticEMA(3, Trend_MA_Period, 0); // V9.10: Micro Gravity Baseline
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
   if (Vol_Squeeze_F >= 0.8) vol_ignite = (Volume[0] > vol_m1_avg * 0.8); 
   bool m1_pre_sqz = !Use_M1_Structure || (iVolume(NULL, PERIOD_M1, 1) < vol_m1_avg * 1.3); 

   double buffer = Breakout_Buffer * Point;
   // V9.5 Flash Logic: If volume is massive (>1.5x avg), entry is instant (0 buffer)
   double eff_buf = (vol_ignite && Volume[0] > vol_m1_avg * 1.5) ? 0 : buffer;
   
   double buy_trigger = High[1] + eff_buf; 
   double sell_trigger = Low[1] - eff_buf;  
   
   double m12_macd_main = GetSyntheticMACD(12, 12, 26, 9, 0, MODE_MAIN);
   double m12_macd_sig  = GetSyntheticMACD(12, 12, 26, 9, 0, MODE_SIGNAL);
   bool macd_buy_ok  = !Use_MACD_Filter || (m12_macd_main > m12_macd_sig); 
   bool macd_sell_ok = !Use_MACD_Filter || (m12_macd_main < m12_macd_sig);

   // --- Update UI ALWAYS ---
   double cur_dev_m12 = MathAbs(M12_0.b_close - ema_m12) / Point;
   double cur_dev_m3  = MathAbs(M12_0.b_close - ema_m3) / Point; // Use M12 approx close
   
   bool ui_m30_sync = (is_uptrend && m30_bull) || (is_dntrend && m30_bear);
   bool ui_m3_sync = (is_uptrend && m3_trend_up) || (is_dntrend && m3_trend_dn);
   bool ui_mom_ok = (is_uptrend && momentum_up) || (is_dntrend && momentum_dn);
   UpdateUI(M12_0.b_close, ema_m12, M3_1.b_volume, vol_ma_m3, rsi_m3, rsi_m12, adx_m30, is_uptrend, buy_trigger, sell_trigger, macd_buy_ok, macd_sell_ok, vol_ignite, ui_m3_sync, ui_mom_ok, m1_pre_sqz, ui_m30_sync, cur_dev_m12, cur_dev_m3);

   // --- Manage Grid ---
   if(CheckRisk()) return;      
   ManageGridExit();           
   ManageGridRecovery();        

   // --- V9.3 Smart MACD Exit ---
   if (Use_MACD_Exit) {
       double profit = 0;
       int type = -1;
       int cnt = 0;
       for(int i=0; i<OrdersTotal(); i++) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
           profit += OrderProfit() + OrderSwap() + OrderCommission();
           type = OrderType();
           cnt++;
       }
       
       if (cnt > 0 && profit > MACD_Exit_Min_Profit) {
           if (type == OP_BUY && m12_macd_main < m12_macd_sig) {
               Print("V9.4 Smart MACD Exit (Buy Weak). Profit: $", profit);
               CloseAllOrders(); return;
           }
           if (type == OP_SELL && m12_macd_main > m12_macd_sig) {
               Print("V9.4 Smart MACD Exit (Sell Weak). Profit: $", profit);
               CloseAllOrders(); return;
           }
       }
   }

   // --- Entry Logic (Only if Empty) ---
   if (CountOrders(0) > 0 || CountOrders(1) > 0) return; 

    // Reset Memory when empty
   Basket_High_Water_Mark = -99999.0;

   // Time Filter
   int hour = TimeHour(TimeCurrent());
   if (Use_Time_Filter && (hour < StartHour || hour >= EndHour)) return; 
   
   bool strict_buy  = is_uptrend && m3_trend_up && m30_bull && macd_buy_ok && vol_ignite && m1_pre_sqz;
   bool strict_sell = is_dntrend && m3_trend_dn && m30_bear && macd_sell_ok && vol_ignite && m1_pre_sqz;  
   
   int spread = (int)MarketInfo(Symbol(), MODE_SPREAD);
   
   if (current_m3_start == Last_M3_Time && !Order_Placed_In_Current_Bar) { 
       if (spread > Max_Spread_Point) return;
       // V9.10 Gravity Pro: Dual Layer Deviation (Macro + Micro)
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
//| V9.4 Adaptive Trailing Logic                                     |
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

    // 1. Hard Target
    if (total_profit >= Basket_Target_USD) {
        Print("V9.4 Grand Slam! $", total_profit);
        CloseAllOrders(); return;
    }

    // 2. Adaptive Rolling Profit
    if (Use_Basket_Trail) {
        if (Basket_High_Water_Mark == -99999.0) Basket_High_Water_Mark = 0;
        if (total_profit >= Basket_Trail_Start) {
            if (total_profit > Basket_High_Water_Mark) Basket_High_Water_Mark = total_profit;
            
            // Choose Step
            double c_step = Basket_Trail_Step;
            if (total_profit >= Basket_Trend_Start) c_step = Basket_Trend_Step;
            
            if (total_profit < (Basket_High_Water_Mark - c_step)) {
                Print("V9.4 Adaptive Exit! Profit: $", total_profit, " Mode: ", (total_profit >= Basket_Trend_Start ? "Trend":"Safety"));
                CloseAllOrders();
            }
        }
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
    if (type == OP_BUY) {
        if ((last_price - Ask) / Point >= grid_dist / Point) {
            double new_lot = NormalizeDouble(last_lot * Lot_Multi, 2); 
            int res = OrderSend(Symbol(), OP_BUY, new_lot, Ask, 3, 0, 0, sComm+"_L"+IntegerToString(cnt+1), Magic, 0, clrBlue);
            if(res < 0) Print("Grid Buy Error: ", GetLastError());
        }
    }
    else if (type == OP_SELL) {
        if ((Bid - last_price) / Point >= grid_dist / Point) {
            double new_lot = NormalizeDouble(last_lot * Lot_Multi, 2); 
            int res = OrderSend(Symbol(), OP_SELL, new_lot, Bid, 3, 0, 0, sComm+"_L"+IntegerToString(cnt+1), Magic, 0, clrRed);
            if(res < 0) Print("Grid Sell Error: ", GetLastError());
        }
    }
}

double GetGridDistance() {
   if(Use_ATR_Grid) {
      double atr = iATR(NULL, 0, ATR_Period, 0); 
      double dist = atr * ATR_Multi;
      if(dist < Fix_Dist * Point) return (double)Fix_Dist * Point;
      return dist;
   }
   return (double)Fix_Dist * Point;
}

void CloseAllOrders() {
    for(int i=OrdersTotal()-1; i>=0; i--) {
        if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
            bool res = false;
            if(OrderType()==OP_BUY) res = OrderClose(OrderTicket(), OrderLots(), Bid, 10, clrGray);
            else res = OrderClose(OrderTicket(), OrderLots(), Ask, 10, clrGray);
            if(!res) Print("Close Error: ", GetLastError());
        }
    }
}

void OpenInitialTrade(int type) {
    if (AccountFreeMargin() < 10) return;
    int cmd = (type == 0) ? OP_BUY : OP_SELL;
    double price = (type == 0) ? Ask : Bid;
    color clr = (type == 0) ? clrBlue : clrRed;
    int res = OrderSend(Symbol(), cmd, Fixed_Lot, price, 3, 0, 0, sComm+"_L1", Magic, 0, clr);
    if(res < 0) Print("Initial Trade Error: ", GetLastError());
}

//+------------------------------------------------------------------+
//| Synthetic Engine                                                 |
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
      bar.b_close = iClose(NULL, PERIOD_M1, i); bar.b_volume += (double)iVolume(NULL, PERIOD_M1, i);
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
//| UI (V9.11 Detailed)                                              |
//+------------------------------------------------------------------+
void UpdateUI(double price, double ema, double vol, double vol_ma, double rsi_m3, double rsi_m12, double adx, bool is_uptrend, double b_trig, double s_trig, bool macd_buy_ok, bool macd_sell_ok, bool vol_ignite, bool m3_ok_trend, bool mom_ok, bool m1_struct_ok, bool m30_ok, double cur_dev_m12, double cur_dev_m3) {
   Comment("");   
   color bg_color = clrDarkSlateGray; // Safe dark gray color for BG
   DrawRect("LQ_BG", 5, 5, 300, 360, bg_color); 
   DrawLabel("LQ_Title", 15, 15, "LiQiyu V9.11 BALANCED (Relaxed Gravity)", 10, clrGold);

   int orders = CountOrders(OP_BUY) + CountOrders(OP_SELL);
   double open_prof = 0;
   for(int i=0; i<OrdersTotal(); i++) if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) open_prof += OrderProfit() + OrderSwap() + OrderCommission();
   
   DrawLabel("LQ_Grid", 15, 40, "Grid: " + (orders > 0 ? ("ACTIVE (" + IntegerToString(orders) + "L)") : "WAITING"), 9, orders > 0 ? clrOrange : clrLime); 
   
   string p_txt = "Profit: $" + DoubleToString(open_prof, 2);
   color p_clr = open_prof > 0 ? clrLime : (open_prof < -10 ? clrRed : clrSilver);
   
   if (open_prof >= Basket_Trail_Start && Basket_High_Water_Mark > 0) {
       double c_step = (open_prof >= Basket_Trend_Start) ? Basket_Trend_Step : Basket_Trail_Step;
       string m_str = (open_prof >= Basket_Trend_Start) ? "TRENDING" : "LOCKING";
       p_txt += " (" + m_str + " | Lock: $" + DoubleToString(Basket_High_Water_Mark - c_step, 2) + ")";
       p_clr = clrGold;
   } else {
       p_txt += " (Start: $" + DoubleToString(Basket_Trail_Start, 2) + ")";
   }
   DrawLabel("LQ_Prof", 15, 60, p_txt, 9, p_clr); 

   bool bull = (price > ema);
   DrawLabel("LQ_Trend", 15, 95, "[1] M12 Trend: " + (bull ? "BULL" : "BEAR") + " | M30: " + (m30_ok ? "OK" : "Diff"), 8, m30_ok ? (bull ? clrLime : clrRed) : clrGray);
   DrawLabel("LQ_M3T", 15, 110, "    M3 Trend: " + (m3_ok_trend ? "Synced" : "Conflict"), 8, m3_ok_trend ? clrLime : clrRed);
   DrawLabel("LQ_Mom", 15, 130, "[2] ADX: " + DoubleToString(adx, 1) + " | Mom: " + (mom_ok?"Push":"Wait"), 8, (adx > ADX_Min_Level && mom_ok) ? clrLime : clrGray);
   DrawLabel("LQ_Vol", 15, 150, "[3] M3 Vol: " + (vol < vol_ma ? "Squeeze" : "High") + " | M1 Pre: " + (m1_struct_ok ? "OK" : "Noisy"), 8, m1_struct_ok ? clrLime : clrGray);
   DrawLabel("LQ_Ign", 15, 165, "    M1 Ignition: " + (vol_ignite ? "IGNITED (GO)" : "Wait"), 8, vol_ignite ? clrLime : clrRed);
   
   bool rsi_all_ok = (bull ? rsi_m3 < RSI_Buy_Max : rsi_m3 > RSI_Sell_Min) && (bull ? rsi_m12 > 50 && rsi_m12 < RSI_M12_Limit : rsi_m12 < 50 && rsi_m12 > (100 - RSI_M12_Limit));
   DrawLabel("LQ_RSI", 15, 185, "[4] RSI: " + DoubleToString(rsi_m3,1) + "/" + DoubleToString(rsi_m12,1) + (rsi_all_ok?" (OK)":" (Wait)"), 8, rsi_all_ok ? clrLime : clrRed); 
   DrawLabel("LQ_MACD", 15, 200, "    MACD: " + ((macd_buy_ok||macd_sell_ok) ? "Confirmed" : "Conflict"), 8, (macd_buy_ok||macd_sell_ok) ? clrLime : clrRed);
   bool grav_ok = (cur_dev_m12 < Max_Dev_From_MA && cur_dev_m3 < Max_Dev_From_M3);
   DrawLabel("LQ_Grav", 15, 215, "    Gravity: M12=" + DoubleToString(cur_dev_m12,0) + "/" + IntegerToString(Max_Dev_From_MA) + " | M3=" + DoubleToString(cur_dev_m3,0) + "/" + IntegerToString(Max_Dev_From_M3), 8, grav_ok ? clrLime : clrRed);

   double dist = (bull) ? (b_trig - Ask)/Point : (Bid - s_trig)/Point;
   string trig_txt = (bull ? "BUY ZONE: > " : "SELL ZONE: < ") + DoubleToString(bull?b_trig:s_trig, Digits) + " (Dist: " + DoubleToString(dist,0) + ")";
   DrawLabel("LQ_Trig", 15, 230, trig_txt, 9, dist <= 0 ? clrLime : (bull?clrDeepSkyBlue:clrOrangeRed));

   DrawLabel("LQ_Acc", 15, 290, "Equity: $" + DoubleToString(AccountEquity(), 2), 9, clrWhite);
   DrawLabel("LQ_ST", 15, 310, "STATUS: " + (orders > 0 ? "MANAGING..." : (dist<=0 ? "ZONE REACHED!" : "HUNTING...")), 9, orders > 0 ? clrYellow : clrDeepSkyBlue);
   
   ChartRedraw(0); // Force UI Update
}

void DrawLabel(string name, int x, int y, string text, int size, color clr) {
   if(ObjectFind(0, name) < 0) {
      ObjectCreate(0, name, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, 0);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, false);
      ObjectSetInteger(0, name, OBJPROP_BACK, false); // Keep on top
   }
   // Always Update Properties
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, (long)x);
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, (long)y);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, (long)size);
   ObjectSetInteger(0, name, OBJPROP_COLOR, (long)clr);
}
void DrawRect(string name, int x, int y, int w, int h, color bg_color) {
   if(ObjectFind(0, name) < 0) {
      ObjectCreate(0, name, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, name, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, false);
      ObjectSetInteger(0, name, OBJPROP_BACK, false); // Keep on top but behind labels
   }
   // Always Update Properties
   ObjectSetInteger(0, name, OBJPROP_XDISTANCE, (long)x); 
   ObjectSetInteger(0, name, OBJPROP_YDISTANCE, (long)y);
   ObjectSetInteger(0, name, OBJPROP_XSIZE, (long)w); 
   ObjectSetInteger(0, name, OBJPROP_YSIZE, (long)h);
   ObjectSetInteger(0, name, OBJPROP_BGCOLOR, (long)bg_color); 
   ObjectSetInteger(0, name, OBJPROP_BORDER_TYPE, BORDER_FLAT); 
}
