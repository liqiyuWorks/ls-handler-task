//+------------------------------------------------------------------+
//|                                   LiQiyu_Strategy_V8.4_Sniper.mq4|
//|                    M3/M12 Trend + Volume Squeeze + Pending Orders|
//+------------------------------------------------------------------+
#property copyright "Li Qiyu Quant Labs"
#property version   "8.40"
#property strict

// --- Account Protection & Target ($200 Doubling Plan) ---

// --- Account Protection & Target ($200 Doubling Plan) ---

extern string _S_ = "=== Protection ($200 Start) ===";

extern double Risk_Percent   = 2.0;   // Risk per trade (%) Default: 2%

extern double Fixed_Lot      = 0.01;  // Fixed Lot Size (Priority if > 0)

extern double Max_Drawdown   = 20.0;  // Max Account Drawdown (%)

extern double Target_Profit  = 100.0; // Stage Profit Target ($)



// --- Strategy Parameters (V8.5 Micro) ---

extern string _P_ = "=== Strategy V8.5 (Micro) ===";

extern int    Trend_MA_Period = 34;   // M12 EMA Period

extern double Vol_Squeeze_F   = 0.75; // Volume Squeeze Factor (0.75)

extern int    Vol_MA_Period   = 20;   // M3 Volume MA Period

extern double ATR_Stop_Mult   = 3.0;  // Initial SL Multiplier (3.0)

extern double Trail_Start     = 1.2;  // Trailing Start (1.2 ATR)

extern double Trail_Step      = 0.3;  // Trailing Step (0.3 ATR)



extern string _F_ = "=== Filters ===";

extern int    RSI_Buy_Max     = 70;   // RSI Max for Buy

extern int    RSI_Sell_Min    = 30;   // RSI Min for Sell

extern int    Breakout_Buffer = 15;   // Breakout Buffer (Points)

extern bool   Use_Momentum    = true; // Momentum Check



extern string _A_ = "=== Advanced Filters ===";

extern int    ADX_Period      = 14;   // ADX Period

extern int    ADX_Min_Level   = 18;   // Min Trend Strength

extern bool   Use_M30_Filter  = true; // M30 Trend Filter

extern int    M30_Buffer_Points = 20; // M30 Tolerance (Points)



// --- Global Variables ---

// --- Global Variables ---
int    Magic  = 2026805; // V8.5 Magic
string sComm  = "LQ_V8.5_Micro";
datetime Last_M3_Time = 0;

// --- Synthetic Bar Structure (Renamed to avoid conflict) ---
struct SyntheticBar {
   double b_open;
   double b_high;
   double b_low;
   double b_close;
   double b_volume; // Use tick volume
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

// Trading Hours (Europe/US Session Only)
extern int StartHour = 9;   
extern int EndHour   = 22;

//+------------------------------------------------------------------+
//| Main Logic (Driven by M1 Ticks)                                  |
//+------------------------------------------------------------------+
void OnTick() {
   if(CheckRisk()) return; 

   // === HIGH ACCURACY MODE ACTIVE ===
   // Calculations are performed on every tick for UI precision.
   // Trade signals are locked to bar close for stability.

   // Always Run: Position Management (Trailing Stop)
   double atr = iATR(NULL, PERIOD_M15, 14, 0); 
   ManagePositions(atr);
   
   // Time Filter
   int hour = TimeHour(TimeCurrent());
   if (hour < StartHour || hour >= EndHour) {
      if(hour % 4 == 0 && Minute() == 0 && Seconds() < 5) 
         Print("Outside Trading Hours (", StartHour, "-", EndHour, "). Current: ", hour);
      string w_txt = "Non-Trading Hours (" + IntegerToString(StartHour) + ":00 - " + IntegerToString(EndHour) + ":00)";
      if(ObjectFind(0, "LQ_Wait") < 0) DrawLabel("LQ_Wait", 40, 320, w_txt, 10, clrGray);
      else ObjectSetString(0, "LQ_Wait", OBJPROP_TEXT, w_txt);
      
      // Outside hours, delete all pending orders
      DeletePendingOrders();
      return; 
   }
   if(ObjectFind(0, "LQ_Wait") >= 0) ObjectDelete(0, "LQ_Wait");

   // --- Core Upgrade: M3 Candle Driver (Sniper Mode) ---
   // 1. Detect New M3 Bar
   // Calculate current M3 start time
   datetime current_time = TimeCurrent();
   int period_seconds = 3 * 60;
   int seconds_In = TimeSeconds(current_time) + TimeMinute(current_time) * 60 + TimeHour(current_time) * 3600;
   datetime current_m3_start = (datetime)(current_time - (seconds_In % period_seconds));
   
   if (current_m3_start != Last_M3_Time) {
      // === New M3 Candle Started ===
      Last_M3_Time = current_m3_start;
      
      // 2. Cleanup Old Orders (Expire Current)
      DeletePendingOrders();
   }
   
   // 3. Recalculate Logic Every Tick (To update Dashboard Dynamically)
   // 1. Get Synthetic Data
   SyntheticBar M12_0 = GetSyntheticBar(12, 0); // Current M12
   SyntheticBar M12_1 = GetSyntheticBar(12, 1); // Previous M12
   SyntheticBar M3_1 = GetSyntheticBar(3, 1);   // Previous M3 (Completed)
   
   // 2. Calculate Indicators
   double ema_m12 = GetSyntheticEMA(12, Trend_MA_Period, 0); 
   double vol_ma_m3 = GetSyntheticVolMA(3, Vol_MA_Period, 1); 
   
   // 3. RSI Synthesis
   double rsi_m3 = GetSyntheticRSI(3, 14);   
   double rsi_m12 = GetSyntheticRSI(12, 14); 

   // 4. Advanced Trend Filter (V8.3/4)
   double adx_m30 = iADX(NULL, PERIOD_M30, ADX_Period, PRICE_CLOSE, MODE_MAIN, 0);
   bool adx_ok = (adx_m30 > ADX_Min_Level);

   double ema_m30 = iMA(NULL, PERIOD_M30, 34, 0, MODE_EMA, PRICE_CLOSE, 0);
   double close_m30 = iClose(NULL, PERIOD_M30, 0);
   double m30_buf = M30_Buffer_Points * Point;
   bool m30_bull = (!Use_M30_Filter || close_m30 > (ema_m30 - m30_buf)); // Allow 20pts buffer below EMA
   bool m30_bear = (!Use_M30_Filter || close_m30 < (ema_m30 + m30_buf)); // Allow 20pts buffer above EMA

   // 5. Trend & Momentum
   bool is_uptrend = (M12_0.b_close > ema_m12);
   bool is_dntrend = (M12_0.b_close < ema_m12);
   bool is_sqz = (M3_1.b_volume < vol_ma_m3 * Vol_Squeeze_F); 
   
   bool rsi_resonance_buy = (rsi_m3 < RSI_Buy_Max && rsi_m12 > 50); 
   bool rsi_resonance_sell = (rsi_m3 > RSI_Sell_Min && rsi_m12 < 50); 
   
   bool momentum_up = !Use_Momentum || (M12_0.b_close > M12_1.b_close);
   bool momentum_dn = !Use_Momentum || (M12_0.b_close < M12_1.b_close);

   // 6. Breakout Trigger Calc
   double buffer = Breakout_Buffer * Point;
   double buy_trigger = M3_1.b_high + buffer; 
   double sell_trigger = M3_1.b_low - buffer;  
   
   // 7. Place Pending Orders (Only on New Bar start to avoid spam/repaint)
   if (current_m3_start == Last_M3_Time && TimeCurrent() < (Last_M3_Time + 10)) { // Only try in first 10 seconds
       // Buy Condition
       if (CountOrders(0) == 0 && is_uptrend && m30_bull && adx_ok && momentum_up && is_sqz && rsi_resonance_buy) {
          PlaceStopOrder(0, buy_trigger, atr);
       }
       
       // Sell Condition
       if (CountOrders(1) == 0 && is_dntrend && m30_bear && adx_ok && momentum_dn && is_sqz && rsi_resonance_sell) {
          PlaceStopOrder(1, sell_trigger, atr);
       }
   }
   
   // Update Dashboard
   bool ui_m30_sync = (is_uptrend && m30_bull) || (is_dntrend && m30_bear);
   UpdateUI(M12_0.b_close, ema_m12, M3_1.b_volume, vol_ma_m3, rsi_m3, rsi_m12, adx_m30, ui_m30_sync, buy_trigger, sell_trigger);
}

//+------------------------------------------------------------------+
//| Helper: Place Pending Orders                                     |
//+------------------------------------------------------------------+
void PlaceStopOrder(int type, double price, double atr) {
   double sl = ATR_Stop_Mult * atr;
   double lots = Fixed_Lot;
   double sl_price;
   int cmd;
   color clr;
   
   if (type == 0) {
      cmd = OP_BUYSTOP;
      sl_price = price - sl;
      clr = clrDeepSkyBlue;
      if (price < Ask) return; // Price passed, cannot place STOP order
   } else {
      cmd = OP_SELLSTOP;
      sl_price = price + sl;
      clr = clrOrangeRed;
      if (price > Bid) return;
   }
   
   // Expiry: Auto-managed by DeletePendingOrders() at next M3 bar
   // MT4 expiry time can be unreliable on some brokers, so we manage manually
   
   int ticket = OrderSend(Symbol(), cmd, lots, NormalizeDouble(price, Digits), 0, NormalizeDouble(sl_price, Digits), 0, sComm, Magic, 0, clr);
   
   if(ticket < 0) Print("PlaceStopOrder failed: ", GetLastError());
   else Print("Sniper Order Placed #", ticket, " @ ", price);
}

void DeletePendingOrders() {
   for(int i=OrdersTotal()-1; i>=0; i--) {
      if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
         if (OrderType() == OP_BUYSTOP || OrderType() == OP_SELLSTOP) {
            bool res = OrderDelete(OrderTicket());
         }
      }
   }
}



//+------------------------------------------------------------------+

//| 合成 K 线核心引擎                                                |

//+------------------------------------------------------------------+

//+------------------------------------------------------------------+

//| 合成 K 线核心引擎                                                |

//+------------------------------------------------------------------+

// period_min: 3 or 12, shift: 0 (current), 1 (previous)

SyntheticBar GetSyntheticBar(int period_min, int shift) {

   SyntheticBar bar;
   // Initialize with extreme values to ensure correct Min/Max logic
   bar.b_open = 0; bar.b_high = 0; bar.b_low = 999999; bar.b_close = 0; bar.b_volume = 0;

   

   // 计算当前时间的 M1 索引偏移

   datetime current_time = Time[0];

   

   int seconds_In = TimeSeconds(current_time) + TimeMinute(current_time) * 60 + TimeHour(current_time) * 3600;

   int period_seconds = period_min * 60;

   

   // 当前周期开始的时间戳

   datetime start_time_0 = (datetime)(current_time - (seconds_In % period_seconds)); 

   

   // 目标 shift 的开始时间

   datetime target_start_time = (datetime)(start_time_0 - (shift * period_seconds));

   datetime target_end_time   = (datetime)(target_start_time + period_seconds);

   

   // 遍历 M1 柱子构建合成柱

   // Find start index (Method: Nearest, Exact=False)
   int start_idx = iBarShift(NULL, PERIOD_M1, target_start_time, false);

   if (start_idx == -1) {
       Print("Error: M1 Data missing for synthetic calculation!");
       return bar; 
   }

   

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



// New: Synthetic RSI (Cutler's RSI, no smoothing, ideal for synthetic)

double GetSyntheticRSI(int period_min, int rsi_period) {

   double gain_sum = 0;

   double loss_sum = 0;

   

   for (int i = 1; i <= rsi_period; i++) {

      SyntheticBar b_curr = GetSyntheticBar(period_min, i);

      SyntheticBar b_prev = GetSyntheticBar(period_min, i + 1);

      

      double diff = b_curr.b_close - b_prev.b_close;
      
      // Precision Check: Ensure consistent data
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



//+------------------------------------------------------------------+

//| Trade Management                                                 |

//+------------------------------------------------------------------+

void OpenTrade(int type, double atr) {

   double sl = ATR_Stop_Mult * atr;

   double lots = Fixed_Lot;

   

   double sl_price = (type==0) ? Ask - sl : Bid + sl;

   

   int ticket = -1;

   if (type == 0) ticket = OrderSend(Symbol(), OP_BUY, lots, Ask, 30, NormalizeDouble(sl_price, Digits), 0, sComm, Magic, 0, clrBlue);

   else           ticket = OrderSend(Symbol(), OP_SELL, lots, Bid, 30, NormalizeDouble(sl_price, Digits), 0, sComm, Magic, 0, clrRed);

   

   if(ticket < 0) Print("OrderSend failed with error #", GetLastError());

}



void ManagePositions(double atr) {

   for(int i=0; i<OrdersTotal(); i++) {

      if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {

         double profit_pips = (OrderType()==0) ? (Bid - OrderOpenPrice()) : (OrderOpenPrice() - Ask);

         profit_pips = profit_pips / Point;

         

         double start_trail = Trail_Start * atr / Point; 

         

         if (profit_pips > start_trail) {

             double new_sl;

             bool res = false;

             if (OrderType() == OP_BUY) {

                 new_sl = Bid - (start_trail * 0.5) * Point; 

                 if (new_sl > OrderStopLoss() && new_sl > OrderOpenPrice()) 

                     res = OrderModify(OrderTicket(), OrderOpenPrice(), NormalizeDouble(new_sl, Digits), 0, 0, clrGreen);

             }

             else {

                 new_sl = Ask + (start_trail * 0.5) * Point;

                 if ((OrderStopLoss() == 0 || new_sl < OrderStopLoss()) && new_sl < OrderOpenPrice())

                     res = OrderModify(OrderTicket(), OrderOpenPrice(), NormalizeDouble(new_sl, Digits), 0, 0, clrGreen);

             }

             if(!res && GetLastError() != ERR_NO_ERROR) Print("OrderModify failed: ", GetLastError());

         }

      }

   }

}



bool CheckRisk() {

   if (AccountEquity() <= 0) return true;

   if ((AccountBalance() - AccountEquity()) / AccountBalance() * 100 > Max_Drawdown) return true;

   return false;

}



int CountOrders(int type) {

   int cnt = 0;

   for(int i=0; i<OrdersTotal(); i++) 

      if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic && OrderType() == type) cnt++;

   return cnt;

}



//+------------------------------------------------------------------+

//| Dashboard Display (V8.5 Micro)                                     |

//+------------------------------------------------------------------+

void UpdateUI(double price, double ema, double vol, double vol_ma, double rsi_m3, double rsi_m12, double adx, bool m30_ok, double b_trig, double s_trig) {

   Comment("");   // 1. Background

   color bg_color = clrBlack; 

   DrawRect("LQ_BG", 20, 20, 360, 350, bg_color); // Height 330 -> 350

   

   // Title

   DrawLabel("LQ_Title", 40, 40, "LiQiyu V8.5 Micro ($200 Exclusive)", 11, clrGold);

   

   // 1. Trend Filter (M12 + M30)

   bool bull = (price > ema);
   string t_txt = bull ? "[1] M12 Trend: BULL (Above)" : "[1] M12 Trend: BEAR (Below)";
   DrawLabel("LQ_Trend", 40, 70, t_txt, 10, bull ? clrLime : clrRed);

   

   string m30_txt = "    M30 Trend: " + (m30_ok ? "Confirmed" : "Conflict");

   DrawLabel("LQ_M30", 40, 85, m30_txt, 8, m30_ok ? clrSilver : clrRed);

   

   // 2. ADX Strength (New)

   bool adx_pass = (adx > ADX_Min_Level);

   string adx_txt = "[2] ADX Strength: " + DoubleToString(adx, 1) + (adx_pass ? " (OK)" : " (Weak)");

   DrawLabel("LQ_ADX", 40, 110, adx_txt, 10, adx_pass ? clrLime : clrGray);

   

   // 3. Volume Squeeze

   bool sqz = (vol < vol_ma * Vol_Squeeze_F);

   string v_txt = "[3] M3 Vol: " + (sqz ? "Squeeze (Ready)" : "High Vol (Wait)");

   DrawLabel("LQ_Vol", 40, 135, v_txt, 10, sqz ? clrLime : clrGray);

   

   // 4. RSI Resonance

   bool m3_ok = (bull ? rsi_m3 < RSI_Buy_Max : rsi_m3 > RSI_Sell_Min);

   bool m12_ok = (bull ? rsi_m12 > 50 : rsi_m12 < 50);

   bool rsi_all_ok = m3_ok && m12_ok;

   

   string r_txt = "[4] RSI Sync: " + (rsi_all_ok ? "Synced" : "Wait");

   DrawLabel("LQ_RSI", 40, 160, r_txt, 10, rsi_all_ok ? clrLime : clrRed);

   string r_d1 = "    M3=" + DoubleToString(rsi_m3, 1) + " / M12=" + DoubleToString(rsi_m12, 1);

   DrawLabel("LQ_RSI1", 40, 180, r_d1, 8, clrSilver);

   

   // 5. Breakout Points

   if (bull) {
       DrawLabel("LQ_Trig", 40, 210, "BUY Trigger: " + DoubleToString(b_trig, Digits), 11, clrDeepSkyBlue);
       DrawLabel("LQ_Dist", 40, 230, "Distance: " + DoubleToString((b_trig - Ask)/Point, 0) + " pts", 9, clrGray);
   } else {
       DrawLabel("LQ_Trig", 40, 210, "SELL Trigger: " + DoubleToString(s_trig, Digits), 11, clrOrangeRed);
       DrawLabel("LQ_Dist", 40, 230, "Distance: " + DoubleToString((Bid - s_trig)/Point, 0) + " pts", 9, clrGray);
   }



   // 6. Account & Status

   string acc = "Equity: $" + DoubleToString(AccountEquity(), 2);
   DrawLabel("LQ_Acc", 40, 270, acc, 10, clrWhite);

   

   bool ready = sqz && rsi_all_ok && adx_pass && m30_ok;

   string st = ready ? "STATUS: ALL GREEN! Waiting..." : "STATUS: Monitoring...";

   DrawLabel("LQ_ST", 40, 300, st, 11, ready ? clrYellow : clrGray);

}



// --- Dashboard Helper Functions ---

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

