//+------------------------------------------------------------------+
//|                                   LiQiyu_Strategy_V8.6.1_Professional.mq4|
//|                    M3/M12 Trend + Volume Squeeze + Pending Orders|
//+------------------------------------------------------------------+
#property copyright "Li Qiyu Quant Labs"
#property version   "8.62"
#property strict

// --- Account Protection & Target ($200 Doubling Plan) ---

extern string _S_ = "=== Protection ($200 Start) ===";

extern double Risk_Percent   = 2.0;   // Risk per trade (%) Default: 2%

extern double Fixed_Lot      = 0.01;  // Fixed Lot Size (Priority if > 0)

extern double Max_Drawdown   = 20.0;  // Max Account Drawdown (%)

extern double Target_Profit  = 100.0; // Stage Profit Target ($)

extern int    Max_Spread_Point = 50;  // Max Spread Allowed (Points) for Safety



// --- Strategy Parameters (V8.5 Micro) ---

extern string _P_ = "=== Strategy V8.6 (Professional) ===";

extern int    Trend_MA_Period = 34;   // M12 EMA Period

extern double Vol_Squeeze_F   = 1.0;  // Standard Volume (Was 0.75 - Tight Squeeze)

extern int    Vol_MA_Period   = 20;   // M3 Volume MA Period

extern double ATR_Stop_Mult   = 2.0;  // Initial SL Multiplier (Wider for Gold noise)

extern double Trail_Start     = 1.2;  // Start Trailing at 1.2 ATR (Wait for profit)

extern double Trail_Step      = 0.5;  // Trail distance 0.5 ATR (Forgiving space)

extern double BE_Start        = 0.5;  // Break Even Trigger (0.5 ATR) - Safe Trigger
extern int    BE_Offset       = 20;   // Break Even Offset (Points) - Cover swaps

extern double BE_Lock_Level   = 1.0;  // Tier 2: Secure Profit Trigger (1.0 ATR)
extern double BE_Lock_Amt     = 0.3;  // Tier 2: Profit Amount to Lock (0.3 ATR)

extern double Max_Loss_USD    = 10.0; // Hard Safety: Max Loss in USD for 0.01 lot (Safe for $100)



extern string _F_ = "=== Filters ===";

extern int    RSI_Buy_Max     = 75;   // Extended Range (Was 70)

extern int    RSI_Sell_Min    = 25;   // Extended Range (Was 30)

extern int    Breakout_Buffer = 10;   // Faster Entry (Was 15)

extern bool   Use_Momentum    = true; // Momentum Check
extern bool   Use_MACD_Filter = true; // V8.6 MACD Trend Confirmation
extern bool   Use_Vol_Ignition= true; // V8.6 Volume Spike Check



extern string _A_ = "=== Advanced Filters ===";

extern int    ADX_Period      = 14;   // ADX Period

extern int    ADX_Min_Level   = 15;   // Catch Trends Earlier (Was 18)

extern bool   Use_M30_Filter  = true; // M30 Trend Filter

extern int    M30_Buffer_Points = 20; // M30 Tolerance (Points)



// --- Global Variables ---
int    Magic  = 2026805; // V8.5 Magic
string sComm  = "LQ_V8.5_Micro";
datetime Last_M3_Time = 0;
bool   Order_Placed_In_Current_Bar = false; // Prevent multiple orders in same bar due to latency

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
extern bool Use_Time_Filter = false; // Set to true to restrict hours
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
   if (Use_Time_Filter && (hour < StartHour || hour >= EndHour)) {
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
      
      // Reset Order Flag for new bar
      Order_Placed_In_Current_Bar = false;
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
   
   // New M3 Trend Filter (Added for safety with M1 Trigger)
   // Strategy: M12 (Macro) + M3 (Micro) + M1 (Trigger)
   bool m3_trend_up = (M3_1.b_close > GetSyntheticEMA(3, 34, 1));
   bool m3_trend_dn = (M3_1.b_close < GetSyntheticEMA(3, 34, 1));

   bool rsi_resonance_buy = (rsi_m3 < RSI_Buy_Max && rsi_m12 > 50); 
   bool rsi_resonance_sell = (rsi_m3 > RSI_Sell_Min && rsi_m12 < 50); 
   
   bool momentum_up = !Use_Momentum || (M12_0.b_close > M12_1.b_close);
   bool momentum_dn = !Use_Momentum || (M12_0.b_close < M12_1.b_close);

   // 6. Breakout Trigger Calc (Optimized to M1 for Speed)
   // Old: M3_1.b_high/low (Too slow)
   // New: High[1]/Low[1] (Fast M1 Trigger)
   double buffer = Breakout_Buffer * Point;
   double buy_trigger = High[1] + buffer; 
   double sell_trigger = Low[1] - buffer;  
   
   // --- V8.6 Precision Filters ---
   
   // A. MACD Trend Confirmation (M12 & M3)
   double m12_macd_main = GetSyntheticMACD(12, 12, 26, 9, 0, MODE_MAIN);
   double m12_macd_sig  = GetSyntheticMACD(12, 12, 26, 9, 0, MODE_SIGNAL);
   bool m12_macd_bull = (m12_macd_main > m12_macd_sig);
   bool m12_macd_bear = (m12_macd_main < m12_macd_sig);
   
   double m3_macd_main = GetSyntheticMACD(3, 12, 26, 9, 1, MODE_MAIN); // Previous M3
   double m3_macd_sig  = GetSyntheticMACD(3, 12, 26, 9, 1, MODE_SIGNAL);
   bool m3_macd_bull = (m3_macd_main > m3_macd_sig);
   bool m3_macd_bear = (m3_macd_main < m3_macd_sig);
   
   // V8.6.1 Optimization: Relaxed MACD (Only require M12 Trend Confirmation, ignore M3 noise)
   bool macd_buy_ok  = !Use_MACD_Filter || m12_macd_bull; 
   bool macd_sell_ok = !Use_MACD_Filter || m12_macd_bear;

   // B. Volume Ignition (Spike Check)
   // M1 Tick Volume must be > Moving Average at moment of breakout attempt
   double vol_sum_m1 = 0;
   for(int k=1; k<=20; k++) vol_sum_m1 += iVolume(NULL, PERIOD_M1, k);
   double vol_m1_avg = vol_sum_m1 / 20.0; // Simple Vol MA
   bool vol_ignite = !Use_Vol_Ignition || (Volume[0] > vol_m1_avg * 1.0); // Current M1 Volume vs Avg (Starting Ignition)
   // Optimization: If Volume Squeeze is disabled or very loose (>= 0.8), relax Ignition too
   if (Vol_Squeeze_F >= 0.8) vol_ignite = (Volume[0] > vol_m1_avg * 0.8); // Lower threshold if aggressive

   
   // Strict Alignment Check
   bool strict_buy  = is_uptrend && m3_trend_up && m30_bull && macd_buy_ok && vol_ignite;
   bool strict_sell = is_dntrend && m3_trend_dn && m30_bear && macd_sell_ok && vol_ignite;  
   
   // 7. Place Pending Orders (Only on New Bar start to avoid spam/repaint)
   int spread = (int)MarketInfo(Symbol(), MODE_SPREAD);
   
   // Removed 10s limit: Allow anytime entry if conditions align but NO order placed yet
   if (current_m3_start == Last_M3_Time && !Order_Placed_In_Current_Bar) { 
       
       // Safety Check: High Spread (News/Rollover)
       if (spread > Max_Spread_Point) {
           Print("Safety: Spread too high: ", spread, " > ", Max_Spread_Point, ". No trade.");
           return;
       }

       // Buy Condition
       // Market Sniper: Entry if price is >= buy_trigger AND Strict Alignment
       if (CountOrders(0) == 0 && Ask >= buy_trigger && strict_buy && adx_ok && momentum_up && is_sqz && rsi_resonance_buy) {
          OpenTrade(0, atr, M3_1.b_low);
          Order_Placed_In_Current_Bar = true; // Lock immediately
       }
       
       // Sell Condition
       // Market Sniper: Entry if price is <= sell_trigger AND Strict Alignment
       else if (CountOrders(1) == 0 && Bid <= sell_trigger && strict_sell && adx_ok && momentum_dn && is_sqz && rsi_resonance_sell) {
          OpenTrade(1, atr, M3_1.b_high);
          Order_Placed_In_Current_Bar = true; // Lock immediately
       }
   }
   
   // Update Dashboard
   bool ui_m30_sync = (is_uptrend && m30_bull) || (is_dntrend && m30_bear);
   bool ui_m3_sync = (is_uptrend && m3_trend_up) || (is_dntrend && m3_trend_dn);
   bool ui_mom_ok = (is_uptrend && momentum_up) || (is_dntrend && momentum_dn);
   
   UpdateUI(M12_0.b_close, ema_m12, M3_1.b_volume, vol_ma_m3, rsi_m3, rsi_m12, adx_m30, ui_m30_sync, buy_trigger, sell_trigger, macd_buy_ok, macd_sell_ok, vol_ignite, ui_m3_sync, ui_mom_ok);
}

//+------------------------------------------------------------------+
//| Helper: Open Market Trade                                        |
//+------------------------------------------------------------------+
void OpenTrade(int type, double atr, double structure_price) {
   double sl_dist_atr = ATR_Stop_Mult * atr;
   double lots = Fixed_Lot;
   
   // Safety Check: Margin & Lots
   if (lots <= 0) { Print("Error: Invalid Lots ", lots); return; }
   if (AccountFreeMargin() < 10) { Print("Error: Low Free Margin < $10. No Trade."); return; }

   double sl_price;
   int cmd;
   color clr;
   
   if (type == 0) {
      cmd = OP_BUY;
      // Precision SL: Choose tighter of Structure or ATR, but respect Max_Loss
      sl_price = MathMax(structure_price, Ask - sl_dist_atr);
      if (Ask - sl_price > Max_Loss_USD) sl_price = Ask - Max_Loss_USD;
      if (Ask - sl_price < 15 * Point) sl_price = Ask - 15 * Point; // Min buffer
      clr = clrDeepSkyBlue;
   } else {
      cmd = OP_SELL;
      sl_price = MathMin(structure_price, Bid + sl_dist_atr);
      if (sl_price - Bid > Max_Loss_USD) sl_price = Bid + Max_Loss_USD;
      if (sl_price - Bid < 15 * Point) sl_price = Bid + 15 * Point; // Min buffer
      clr = clrOrangeRed;
   }
   
   int ticket = OrderSend(Symbol(), cmd, lots, (type==0?Ask:Bid), 3, NormalizeDouble(sl_price, Digits), 0, sComm, Magic, 0, clr);
   
   if(ticket < 0) Print("Market Order failed: ", GetLastError());
   else Print("Market Sniper Trade Entered #", ticket, " @ ", (type==0?Ask:Bid));
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

// New: Synthetic MACD Calculation
double GetSyntheticMACD(int period_min, int fast_ema, int slow_ema, int signal_ema, int shift, int mode) {
   // Approximate MACD using Synthetic EMAs
   double fast = GetSyntheticEMA(period_min, fast_ema, shift);
   double slow = GetSyntheticEMA(period_min, slow_ema, shift);
   double main_line = fast - slow;
   
   if (mode == MODE_MAIN) return main_line;
   
   // Signal Line (SMA of Main Line) - Approximation for efficiency (Last 9 samples)
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

//+------------------------------------------------------------------+
//| Trade Management                                                 |
//+------------------------------------------------------------------+
void ManagePositions(double atr) {
   for(int i=0; i<OrdersTotal(); i++) {
      if(OrderSelect(i, SELECT_BY_POS) && OrderMagicNumber() == Magic) {
         double profit_pips = (OrderType()==0) ? (Bid - OrderOpenPrice()) : (OrderOpenPrice() - Ask);
         profit_pips = profit_pips / Point;
         
         double start_trail = Trail_Start * atr / Point; 
         double start_be    = BE_Start * atr / Point;
         
         // 1. Tier 1: Break Even (Risk Free)
         if (profit_pips > start_be && profit_pips <= (BE_Lock_Level * atr / Point)) { 
             double be_sl;
             if (OrderType() == OP_BUY) {
                 be_sl = OrderOpenPrice() + BE_Offset * Point;
                 if (be_sl > OrderStopLoss() && OrderStopLoss() < OrderOpenPrice()) // Only move if better and not already at BE
                    if(OrderModify(OrderTicket(), OrderOpenPrice(), NormalizeDouble(be_sl, Digits), 0, 0, clrGreen))
                        Print("Tier 1 BreakEven @ ", be_sl);
             }
             else {
                 be_sl = OrderOpenPrice() - BE_Offset * Point;
                 if ((OrderStopLoss() == 0 || be_sl < OrderStopLoss()) && (OrderStopLoss() == 0 || OrderStopLoss() > OrderOpenPrice()))
                    if(OrderModify(OrderTicket(), OrderOpenPrice(), NormalizeDouble(be_sl, Digits), 0, 0, clrGreen))
                        Print("Tier 1 BreakEven @ ", be_sl);
             }
         }
         
         // 2. Tier 2: Secure Profit (Bank Some Gains)
         double lock_trig = BE_Lock_Level * atr / Point;
         double lock_amt  = BE_Lock_Amt * atr / Point;
         
         if (profit_pips > lock_trig) {
             double lock_sl;
             if (OrderType() == OP_BUY) {
                 lock_sl = OrderOpenPrice() + lock_amt * Point;
                 // Only move if new SL is higher than current SL AND we haven't started trailing yet (trail logic handles > trail_start)
                 if (lock_sl > OrderStopLoss() && profit_pips < (Trail_Start * atr / Point))
                    if(OrderModify(OrderTicket(), OrderOpenPrice(), NormalizeDouble(lock_sl, Digits), 0, 0, clrBlue))
                        Print("Tier 2 Profit Lock @ ", lock_sl);
             }
             else {
                 lock_sl = OrderOpenPrice() - lock_amt * Point;
                 if ((OrderStopLoss() == 0 || lock_sl < OrderStopLoss()) && profit_pips < (Trail_Start * atr / Point))
                    if(OrderModify(OrderTicket(), OrderOpenPrice(), NormalizeDouble(lock_sl, Digits), 0, 0, clrBlue))
                        Print("Tier 2 Profit Lock @ ", lock_sl);
             }
         }

         // 2. Trailing Stop Logic (Lock Profit)
         if (profit_pips > start_trail) {
             double new_sl;
             bool res = false;
             if (OrderType() == OP_BUY) {
                 new_sl = Bid - (Trail_Step * atr); 
                 if (new_sl > OrderStopLoss() + 5 * Point && new_sl > OrderOpenPrice()) 
                     res = OrderModify(OrderTicket(), OrderOpenPrice(), NormalizeDouble(new_sl, Digits), 0, 0, clrGreen);
             }
             else {
                 new_sl = Ask + (Trail_Step * atr);
                 if ((OrderStopLoss() == 0 || new_sl < OrderStopLoss() - 5 * Point) && (new_sl < OrderOpenPrice() || OrderStopLoss() > OrderOpenPrice()))
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
//| Dashboard Display (V8.6 Professional)                            |
//+------------------------------------------------------------------+
void UpdateUI(double price, double ema, double vol, double vol_ma, double rsi_m3, double rsi_m12, double adx, bool m30_ok, double b_trig, double s_trig, bool macd_buy_ok, bool macd_sell_ok, bool vol_ignite, bool m3_ok_trend, bool mom_ok) {

   Comment("");   // No Comment Text
   color bg_color = clrBlack; 
   DrawRect("LQ_BG", 20, 20, 360, 460, bg_color); // Increased Height to 460

   // --- Header ---
   DrawLabel("LQ_Title", 40, 40, "LiQiyu V8.6.2 PRO (Agile Frequency)", 11, clrGold);

   // --- Section 1: Trend & Structure ---
   bool bull = (price > ema);
   string t_txt = bull ? "[1] M12 Trend: BULL (Above)" : "[1] M12 Trend: BEAR (Below)";
   DrawLabel("LQ_Trend", 40, 70, t_txt, 10, bull ? clrLime : clrRed);
   
   string m30_txt = "    M30 Trend: " + (m30_ok ? "Confirmed" : "Conflict");
   DrawLabel("LQ_M30", 40, 90, m30_txt, 9, m30_ok ? clrSilver : clrRed); // Spaced 90

   string m3_t_txt = "    M3 Trend: " + (m3_ok_trend ? "Synced" : "Conflict");
   DrawLabel("LQ_M3T", 40, 110, m3_t_txt, 9, m3_ok_trend ? clrSilver : clrRed); // New M3 Trend - Spaced 110

   // --- Section 2: Momentum Strength ---
   bool adx_pass = (adx > ADX_Min_Level);
   string adx_txt = "[2] ADX Strength: " + DoubleToString(adx, 1) + (adx_pass ? " (OK)" : " (Weak)");
   DrawLabel("LQ_ADX", 40, 140, adx_txt, 10, adx_pass ? clrLime : clrGray); // Spaced 140
   
   string mom_txt = "    M12 Momentum: " + (mom_ok ? "UP (Push)" : "WAIT (Pullback)");
   DrawLabel("LQ_Mom", 40, 160, mom_txt, 9, mom_ok ? clrSilver : clrRed); // New Momentum - Spaced 160

   // --- Section 3: Volume Dynamics ---
   bool sqz = (vol < vol_ma * Vol_Squeeze_F);
   string v_txt = "[3] M3 Vol: " + (sqz ? "Squeeze (Ready)" : "High Vol (Wait)");
   DrawLabel("LQ_Vol", 40, 190, v_txt, 10, sqz ? clrLime : clrGray); // Spaced 190
   
   string vi_txt = "    M1 Ignition: " + (vol_ignite ? "IGNITED (GO)" : "Low Energy");
   DrawLabel("LQ_VolIgnite", 40, 210, vi_txt, 9, vol_ignite ? clrLime : clrRed); // Spaced 210

   // --- Section 4: Momentum Sync (RSI + MACD) ---
   bool m3_ok = (bull ? rsi_m3 < RSI_Buy_Max : rsi_m3 > RSI_Sell_Min);
   bool m12_ok = (bull ? rsi_m12 > 50 : rsi_m12 < 50);
   bool rsi_all_ok = m3_ok && m12_ok;
   
   string r_txt = "[4] RSI Sync: " + (rsi_all_ok ? "Synced" : "Wait");
   DrawLabel("LQ_RSI", 40, 240, r_txt, 10, rsi_all_ok ? clrLime : clrRed); // Spaced 240
   
   string r_d1 = "    M3=" + DoubleToString(rsi_m3, 1) + " / M12=" + DoubleToString(rsi_m12, 1);
   DrawLabel("LQ_RSI1", 40, 260, r_d1, 8, clrSilver); // Spaced 260
   
   string macd_txt = "    MACD Trend: " + ((macd_buy_ok || macd_sell_ok) ? "M12 CONFIRMED" : "CONFLICT");
   DrawLabel("LQ_MACD", 40, 280, macd_txt, 9, (macd_buy_ok || macd_sell_ok) ? clrLime : clrRed); // Spaced 280

   // --- Section 5: Breakout Zones (Sniper) ---
   double dist = 0;
   if (bull) {
       dist = (b_trig - Ask)/Point;
       DrawLabel("LQ_Trig", 40, 310, "M1 Breakout > " + DoubleToString(b_trig, Digits), 11, clrDeepSkyBlue);
       DrawLabel("LQ_Dist", 40, 330, "Relative: " + DoubleToString(dist, 0) + (dist <= 0 ? " (IN ZONE)" : " pts"), 10, dist <= 0 ? clrLime : clrGray);
   } else {
       dist = (Bid - s_trig)/Point;
       DrawLabel("LQ_Trig", 40, 310, "M1 Breakout < " + DoubleToString(s_trig, Digits), 11, clrOrangeRed);
       DrawLabel("LQ_Dist", 40, 330, "Relative: " + DoubleToString(dist, 0) + (dist <= 0 ? " (IN ZONE)" : " pts"), 10, dist <= 0 ? clrLime : clrGray);
   }

   // --- Section 6: Account & Status ---
   string acc = "Equity: $" + DoubleToString(AccountEquity(), 2);
   DrawLabel("LQ_Acc", 40, 370, acc, 11, clrWhite);

   bool ready = sqz && rsi_all_ok && adx_pass && m30_ok && (macd_buy_ok || macd_sell_ok) && m3_ok_trend && mom_ok;
   
   string st = "STATUS: Monitoring...";
   color st_clr = clrGray;
   
   if (!vol_ignite && ready) {
       st = "STATUS: Waiting for VOL SPIKE...";
       st_clr = clrOrange;
   }
   else if (ready && vol_ignite) {
       if (dist <= 0) {
           st = "STATUS: TARGET IN ZONE! Executing...";
           st_clr = clrYellow;
       } else {
           st = "STATUS: ALL GREEN! Hunting...";
           st_clr = clrDeepSkyBlue;
       }
   }
   
   if (Order_Placed_In_Current_Bar) {
       st = "STATUS: Trade Locked (1/Bar)";
       st_clr = clrGold;
   }

   DrawLabel("LQ_ST", 40, 400, st, 11, st_clr);

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
