import React, { useState, useEffect, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area, ComposedChart, Bar, ReferenceLine, BarChart, Cell, ReferenceArea } from 'recharts';
import { Upload, Activity, ArrowRight, TrendingUp, TrendingDown, Crosshair, DollarSign, Settings, Play, List, AlertCircle, BarChart3, Sparkles, Check, Eye, EyeOff, Layers, FileText, Clock, BarChart2 } from 'lucide-react';

// ==========================================
// 1. Data Processing Engine (Step 1)
// ==========================================

const parseCSV = (text) => {
  const lines = text.split('\n').filter(l => l.trim() !== '');
  const headers = lines[0].split(',').map(h => h.trim());
  
  const idxProd = headers.indexOf('Product');
  const idxMonth = headers.indexOf('Contract Month');
  const idxDate = headers.indexOf('Date');
  const idxClose = headers.indexOf('Close');
  const idxHigh = headers.indexOf('High');
  const idxLow = headers.indexOf('Low');
  const idxOpen = headers.indexOf('Open');

  const rawData = [];
  const productsSet = new Set();
  const monthMap = {'Jan':0,'Feb':1,'Mar':2,'Apr':3,'May':4,'Jun':5,'Jul':6,'Aug':7,'Sep':8,'Oct':9,'Nov':10,'Dec':11};
  
  let minTime = Infinity;
  let maxTime = -Infinity;

  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',');
    if (cols.length < headers.length) continue;

    const product = cols[idxProd];
    if (!product) continue;
    productsSet.add(product);

    const dateStr = cols[idxDate];
    const parts = dateStr.split(' ');
    const ymd = parts[0].split('.');
    
    // Parse Time: "16:00" -> 16
    let hour = 0;
    if (parts[1]) {
        const timeParts = parts[1].split(':');
        if (timeParts.length > 0) hour = parseInt(timeParts[0]);
    }

    const dateObj = new Date(parseInt(ymd[0]), parseInt(ymd[1])-1, parseInt(ymd[2]), hour);
    const timeVal = dateObj.getTime();
    
    if (timeVal < minTime) minTime = timeVal;
    if (timeVal > maxTime) maxTime = timeVal;

    const monthStr = cols[idxMonth];
    const mMatch = monthStr.match(/([A-Za-z]{3})\s?(\d{2,4})/);
    let expiryDate = null;
    let contractMonthKey = null; 
    
    if (mMatch) {
        const mName = mMatch[1]; 
        let year = parseInt(mMatch[2]);
        if (year < 100) year += 2000;
        
        const mKey = mName.charAt(0).toUpperCase() + mName.slice(1).toLowerCase();
        const mIdx = monthMap[mKey];
        
        if (mIdx !== undefined) {
             let nextM = mIdx + 1;
             let nextY = year;
             if(nextM > 11) { nextM = 0; nextY++; }
             expiryDate = new Date(nextY, nextM, 1);
             expiryDate.setDate(expiryDate.getDate() - 1);
             contractMonthKey = `${mKey} ${year}`;
        }
    }

    if (!expiryDate || isNaN(timeVal)) continue;

    const close = parseFloat(cols[idxClose]);
    if (close < 2000) continue;

    rawData.push({
      product: product,
      date: dateObj,
      expiry: expiryDate,
      contractMonth: contractMonthKey,
      close: close,
      high: parseFloat(cols[idxHigh]),
      low: parseFloat(cols[idxLow]),
      open: parseFloat(cols[idxOpen]),
      timeToExpiry: expiryDate - dateObj
    });
  }

  return {
      data: rawData.filter(d => d.timeToExpiry >= 0),
      products: Array.from(productsSet).sort(),
      minDate: new Date(minTime),
      maxDate: new Date(maxTime)
  };
};

// Mode A: Time Weighted (with Forward Fill for M2)
const processTimeWeightedData = (rawData, selectedProduct) => {
    const productData = rawData.filter(d => d.product === selectedProduct);
    const grouped = {};
    
    productData.forEach(d => {
        const k = d.date.getTime(); 
        if(!grouped[k]) grouped[k] = [];
        grouped[k].push(d);
    });

    const dailyData = [];
    const sortedTimes = Object.keys(grouped).map(Number).sort((a,b) => a - b);

    // State for Forward Filling
    let lastKnownM2 = null;

    sortedTimes.forEach(timeKey => {
        const records = grouped[timeKey];
        const contractsMap = {};
        records.forEach(r => contractsMap[r.expiry.getTime()] = r);
        
        const uniqueContracts = Object.values(contractsMap).sort((a,b) => a.timeToExpiry - b.timeToExpiry);

        if (uniqueContracts.length >= 1) {
            const m1 = uniqueContracts[0];
            let currentM2 = null;
            
            if (uniqueContracts.length >= 2) {
                currentM2 = uniqueContracts[1];
                lastKnownM2 = currentM2; 
            }

            const effectiveM2Price = currentM2 ? currentM2.close : (lastKnownM2 ? lastKnownM2.close : null);

            let w2 = 0;
            let synthClose = m1.close;
            let synthHigh = m1.high;
            let synthLow = m1.low;
            let spread = 0;

            if (effectiveM2Price !== null) {
                const monthStart = new Date(m1.expiry);
                monthStart.setDate(1); 
                const totalDuration = m1.expiry - monthStart;
                const timeLeft = m1.expiry - m1.date;
                
                w2 = 1 - (timeLeft / totalDuration);
                w2 = Math.max(0, Math.min(1, w2));
                const w1 = 1 - w2;

                synthClose = m1.close * w1 + effectiveM2Price * w2;
                
                // Safe High/Low calculation handling missing currentM2
                const m2High = currentM2 ? currentM2.high : effectiveM2Price;
                const m2Low = currentM2 ? currentM2.low : effectiveM2Price;
                
                synthHigh = m1.high * w1 + m2High * w2;
                synthLow = m1.low * w1 + m2Low * w2;
                
                spread = m1.close - effectiveM2Price; 
            }
            
            const isoStr = new Date(timeKey).toISOString();

            dailyData.push({
                date: new Date(timeKey), 
                dateStr: isoStr, 
                close: synthClose,
                high: synthHigh,
                low: synthLow,
                spread: spread,
                weight_m2: w2,
                M1_Price: m1.close,
                M2_Price: effectiveM2Price,
                Synthetic: synthClose
            });
        }
    });

    return dailyData;
};

// Mode B: Single Contract
const processSingleContractData = (rawData, selectedProduct, selectedContract) => {
    const contractData = rawData
        .filter(d => d.product === selectedProduct && d.contractMonth === selectedContract)
        .sort((a,b) => a.date - b.date);

    if (contractData.length === 0) return [];

    const allProductData = rawData.filter(d => d.product === selectedProduct);
    
    const grouped = {};
    contractData.forEach(d => {
        const k = d.date.getTime();
        if(!grouped[k]) grouped[k] = [];
        grouped[k].push(d);
    });

    const dailyData = [];
    const sortedTimes = Object.keys(grouped).map(Number).sort((a,b) => a - b);
    
    let lastKnownM2Price = null;

    sortedTimes.forEach(timeKey => {
        const records = grouped[timeKey];
        const m1 = records[records.length - 1]; 
        
        const timestamp = m1.date.getTime();
        const m2Candidates = allProductData.filter(d => 
            d.date.getTime() === timestamp && 
            d.expiry.getTime() > m1.expiry.getTime()
        );
        m2Candidates.sort((a,b) => a.expiry - b.expiry);
        
        const m2 = m2Candidates.length > 0 ? m2Candidates[0] : null;
        
        if (m2) {
            lastKnownM2Price = m2.close;
        }
        
        const effectiveM2 = m2 ? m2.close : lastKnownM2Price;
        const spread = effectiveM2 !== null ? (m1.close - effectiveM2) : 0;

        dailyData.push({
            date: m1.date,
            dateStr: new Date(timeKey).toISOString(),
            close: m1.close,
            high: Math.max(...records.map(r=>r.high)),
            low: Math.min(...records.map(r=>r.low)),
            spread: spread,
            weight_m2: 0,
            M1_Price: m1.close,
            M2_Price: effectiveM2,
            Synthetic: m1.close
        });
    });

    return dailyData;
};

// Helper: Resample Data
const resampleData = (data, timeframe) => {
    if (timeframe === '4H') return data; 

    const grouped = {};
    data.forEach(d => {
        let key;
        const date = new Date(d.date);
        
        if (timeframe === '1D') {
            key = date.toISOString().split('T')[0];
        } else if (timeframe === '1W') {
            const day = date.getDay();
            const diff = date.getDate() - day + (day === 0 ? -6 : 1); 
            const monday = new Date(date.setDate(diff));
            key = monday.toISOString().split('T')[0];
        } else {
            key = d.date.toISOString();
        }
        
        if (!grouped[key]) grouped[key] = [];
        grouped[key].push(d);
    });

    const resampled = [];
    const keys = Object.keys(grouped).sort();

    keys.forEach(k => {
        const bars = grouped[k];
        const first = bars[0];
        const last = bars[bars.length - 1];
        
        const high = Math.max(...bars.map(b => b.high));
        const low = Math.min(...bars.map(b => b.low));
        
        const avgSpread = bars.reduce((sum, b) => sum + b.spread, 0) / bars.length;

        resampled.push({
            ...last, 
            date: new Date(k),
            dateStr: k, 
            high,
            low,
            open: first.close,
            spread: avgSpread
        });
    });

    return resampled;
};

// ==========================================
// 2. Strategy Engine (Step 2)
// ==========================================

const calculateIndicators = (data, params) => {
    const { atrPeriod, trenderMult, macdFast, macdSlow, macdSig } = params;

    let atr = 0;
    let prevClose = data[0].close;
    
    let fu = 0, fl = 0, trend = 1; 
    let bu = 0, bl = 0;

    let emaFast = data[0].close;
    let emaSlow = data[0].close;
    let emaSignal = 0; 

    let bs = 0, ss = 0; 
    let bc = 0, sc = 0; 
    let bcActive = false, scActive = false;

    const alphaFast = 2 / (macdFast + 1);
    const alphaSlow = 2 / (macdSlow + 1);
    const alphaSig = 2 / (macdSig + 1);
    const alphaAtr = 2 / (atrPeriod + 1); 

    const enriched = data.map((d, i) => {
        const { close, high, low } = d;
        
        const tr = Math.max(high - low, Math.abs(close - prevClose));
        if (i === 0) atr = tr;
        else atr = (tr - atr) * alphaAtr + atr;

        bu = close + trenderMult * atr;
        bl = close - trenderMult * atr;

        if (i > 0) {
            if (bu < fu || prevClose > fu) fu = bu; else fu = fu;
            if (bl > fl || prevClose < fl) fl = bl; else fl = fl;
        } else {
            fu = bu; fl = bl;
        }

        if (i > 0) {
            if (trend === 1) {
                if (close < fl) trend = -1;
            } else {
                if (close > fu) trend = 1;
            }
        }
        
        const stopLine = trend === 1 ? fl : fu;

        emaFast = (close - emaFast) * alphaFast + emaFast;
        emaSlow = (close - emaSlow) * alphaSlow + emaSlow;
        const macdLine = emaFast - emaSlow; 
        
        if (i === 0) emaSignal = macdLine;
        else emaSignal = (macdLine - emaSignal) * alphaSig + emaSignal; 
        
        const histogram = macdLine - emaSignal;

        const close4 = i >= 4 ? data[i-4].close : null;
        const high2 = i >= 2 ? data[i-2].high : null;
        const low2 = i >= 2 ? data[i-2].low : null;

        if (close4 !== null) {
            if (close < close4) { bs++; ss = 0; } 
            else if (close > close4) { ss++; bs = 0; } 
            else { bs = 0; ss = 0; }
        }
        const tdB9 = bs === 9;
        const tdS9 = ss === 9;

        if (tdB9) { bcActive = true; bc = 0; scActive = false; }
        if (tdS9) { scActive = true; sc = 0; bcActive = false; }

        let tdB13 = false;
        let tdS13 = false;
        
        let currentBc = 0;
        let currentSc = 0;

        if (bcActive && low2 !== null && close <= low2) {
            bc++;
            currentBc = bc;
            if (bc === 13) { tdB13 = true; bcActive = false; bc = 0; }
        }
        
        if (scActive && high2 !== null && close >= high2) {
            sc++;
            currentSc = sc;
            if (sc === 13) { tdS13 = true; scActive = false; sc = 0; }
        }

        prevClose = close;

        return {
            ...d,
            atr,
            trend,
            stopLine,
            trenderGreen: trend === 1 ? stopLine : null, 
            trenderRed: trend === -1 ? stopLine : null,  
            macd: { line: macdLine, signal: emaSignal, hist: histogram },
            td: { 
                buy9: tdB9, sell9: tdS9, buy13: tdB13, sell13: tdS13,
                bs: bs > 0 ? bs : null, 
                ss: ss > 0 ? ss : null,
                bc: currentBc > 0 ? currentBc : null, 
                sc: currentSc > 0 ? currentSc : null 
            }
        };
    });

    return enriched;
};

const runBacktest = (data, params) => {
    const { riskTarget, spreadThreshold } = params;
    const INITIAL_CAPITAL = 1000000;

    let equity = INITIAL_CAPITAL;
    let position = 0; 
    let entryPrice = 0;
    let peakEquity = INITIAL_CAPITAL;
    let maxDrawdown = 0;
    
    const tradeLog = [];
    const equityCurve = [];

    for (let i = 1; i < data.length; i++) {
        const d = data[i];
        const prev = data[i-1];
        
        const price = d.close;
        const trend = d.trend; 
        const prevTrend = prev.trend;
        const spread = d.spread;
        
        const trendFlipBull = trend === 1 && prevTrend === -1;
        const trendFlipBear = trend === -1 && prevTrend === 1;
        const tdBuy9 = d.td.buy9;
        const tdSell9 = d.td.sell9;
        const tdBuy13 = d.td.buy13;
        const tdSell13 = d.td.sell13;

        let actionTaken = false;

        // Position Management
        if (position !== 0) {
            if ((position > 0 && trendFlipBear) || (position < 0 && trendFlipBull)) {
                const pnl = position > 0 ? (price - entryPrice) * position : (entryPrice - price) * Math.abs(position);
                equity += pnl;
                tradeLog.push({ date: d.dateStr, type: position > 0 ? 'Close Long' : 'Cover Short', price, size: Math.abs(position), pnl, reason: 'Trend Flip', equity });
                position = 0;
                actionTaken = true;
            }
            else if ((position > 0 && (tdSell9 || tdSell13)) || (position < 0 && (tdBuy9 || tdBuy13))) {
                const trimSize = Math.round(Math.abs(position) * 0.5);
                if (trimSize > 0) {
                    const pnl = position > 0 ? (price - entryPrice) * trimSize : (entryPrice - price) * trimSize;
                    equity += pnl;
                    const reason = position > 0 ? (tdSell13 ? 'TD Sell 13' : 'TD Sell 9') : (tdBuy13 ? 'TD Buy 13' : 'TD Buy 9');
                    tradeLog.push({ date: d.dateStr, type: position > 0 ? 'Trim Long' : 'Trim Short', price, size: trimSize, pnl, reason, equity });
                    position = position > 0 ? position - trimSize : position + trimSize;
                }
            }
        }

        // Entry Logic
        if (position === 0 && !actionTaken) {
            const riskAmt = equity * (riskTarget / 100);
            const stopDist = 2 * d.atr;
            let rawSize = stopDist > 0 ? Math.round(riskAmt / stopDist) : 0;
            rawSize = Math.min(rawSize, 1000); 

            if (rawSize > 0) {
                // LONG
                const entrySignalLong = trendFlipBull || (trend === 1 && (tdBuy9 || tdBuy13));
                if (entrySignalLong) {
                    let finalSize = rawSize;
                    let reason = trendFlipBull ? 'Trend Flip' : (tdBuy13 ? 'TD Buy 13' : 'TD Buy 9');
                    position = finalSize;
                    entryPrice = price;
                    tradeLog.push({ date: d.dateStr, type: 'Open Long', price, size: finalSize, pnl:0, reason, equity });
                }
                // SHORT
                const entrySignalShort = trendFlipBear || (trend === -1 && (tdSell9 || tdSell13));
                if (entrySignalShort) {
                    let finalSize = rawSize;
                    let reason = trendFlipBear ? 'Trend Flip' : (tdSell13 ? 'TD Sell 13' : 'TD Sell 9');
                    let skip = false;

                    if (spread > spreadThreshold) {
                        skip = true; 
                    } else if (spread > 0) {
                        finalSize = Math.round(rawSize * 0.5); 
                        reason += " (Backwd Cut)";
                    } else {
                        reason += " (Contango)";
                    }

                    if (!skip && finalSize > 0) {
                        position = -finalSize;
                        entryPrice = price;
                        tradeLog.push({ date: d.dateStr, type: 'Open Short', price, size: finalSize, pnl:0, reason, equity });
                    }
                }
            }
        }

        let unrealized = 0;
        if (position > 0) unrealized = (price - entryPrice) * position;
        else if (position < 0) unrealized = (entryPrice - price) * Math.abs(position);

        const currentEquity = equity + unrealized;
        d.equity = currentEquity;
        d.position = position;
        equityCurve.push({ ...d });

        if (currentEquity > peakEquity) peakEquity = currentEquity;
        const dd = (peakEquity - currentEquity) / peakEquity;
        if (dd > maxDrawdown) maxDrawdown = dd;
    }

    const days = data.length > 0 ? (new Date(data[data.length-1].date) - new Date(data[0].date)) / (1000 * 3600 * 24) : 0;
    const years = days / 365;
    const totalReturn = (equity - INITIAL_CAPITAL) / INITIAL_CAPITAL;
    const cagr = years > 0 ? Math.pow((equity / INITIAL_CAPITAL), 1/years) - 1 : 0;

    return { 
        resultData: equityCurve, 
        trades: tradeLog,
        stats: { finalEquity: equity, totalReturn, cagr, maxDrawdown }
    };
};


// ==========================================
// 3. UI Components
// ==========================================

const fmt = (num) => typeof num === 'number' ? num.toFixed(2) : num;
const fmtPct = (num) => typeof num === 'number' ? (num * 100).toFixed(2) + '%' : num;

const StatCard = ({ title, value, subtext, type = "neutral" }) => {
    let color = "text-slate-700";
    if (type === "bull") color = "text-green-600";
    if (type === "bear") color = "text-red-600";
    return (
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-100">
            <div className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">{title}</div>
            <div className={`text-xl font-bold ${color}`}>{value}</div>
            {subtext && <div className="text-slate-400 text-xs mt-1">{subtext}</div>}
        </div>
    );
};

const SignalMarker = (props) => {
    const { cx, cy, payload, visible } = props;
    if (!payload || !visible) return null;
    
    const { bs, ss, bc, sc } = payload.td;
    const markers = [];

    if (bs) markers.push(<text key="bs" x={cx} y={cy + 15} textAnchor="middle" fill="#22c55e" fontSize={bs===9?12:9} fontWeight={bs===9?"bold":"normal"}>{bs}</text>);
    if (ss) markers.push(<text key="ss" x={cx} y={cy - 10} textAnchor="middle" fill="#ef4444" fontSize={ss===9?12:9} fontWeight={ss===9?"bold":"normal"}>{ss}</text>);
    if (bc) markers.push(<text key="bc" x={cx} y={cy + 28} textAnchor="middle" fill="#15803d" fontSize={bc===13?12:9} fontWeight={bc===13?"bold":"normal"}>{bc}</text>);
    if (sc) markers.push(<text key="sc" x={cx} y={cy - 22} textAnchor="middle" fill="#b91c1c" fontSize={sc===13?12:9} fontWeight={sc===13?"bold":"normal"}>{sc}</text>);

    return <g>{markers}</g>;
};

const TradeLogTable = ({ trades }) => {
    return (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
             <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
                <h3 className="font-bold text-slate-700 flex items-center gap-2"><List size={18}/> Trade Log</h3>
                <span className="text-xs text-slate-500">{trades.length} trades executed</span>
            </div>
            <div className="max-h-96 overflow-y-auto">
                <table className="w-full text-sm text-left">
                    <thead className="bg-slate-50 text-slate-500 font-bold sticky top-0">
                        <tr>
                            <th className="px-6 py-3">Date</th>
                            <th className="px-6 py-3">Type</th>
                            <th className="px-6 py-3">Logic</th>
                            <th className="px-6 py-3 text-right">Price</th>
                            <th className="px-6 py-3 text-right">Size</th>
                            <th className="px-6 py-3 text-right">PnL</th>
                            <th className="px-6 py-3 text-right">Equity</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {trades.slice().reverse().map((t, i) => (
                            <tr key={i} className="hover:bg-slate-50">
                                <td className="px-6 py-3 font-medium text-slate-900 whitespace-nowrap">{t.date.substring(0, 16).replace('T', ' ')}</td>
                                <td className={`px-6 py-3 font-bold ${t.type.includes('Long') ? 'text-green-600' : (t.type.includes('Short') ? 'text-red-600' : '')}`}>
                                    {t.type}
                                </td>
                                <td className="px-6 py-3 text-slate-500 text-xs">
                                    <span className="px-2 py-1 bg-slate-100 rounded border border-slate-200">{t.reason}</span>
                                </td>
                                <td className="px-6 py-3 text-right font-mono">{fmt(t.price)}</td>
                                <td className="px-6 py-3 text-right font-mono font-bold text-blue-600">{t.size}</td>
                                <td className={`px-6 py-3 text-right font-bold font-mono ${t.pnl > 0 ? 'text-green-600' : (t.pnl < 0 ? 'text-red-600' : 'text-slate-400')}`}>
                                    {t.pnl !== 0 ? (t.pnl > 0 ? '+' : '') + fmt(t.pnl) : '-'}
                                </td>
                                <td className="px-6 py-3 text-right font-mono text-slate-700">{fmt(t.equity)}</td>
                            </tr>
                        ))}
                        {trades.length === 0 && (
                            <tr><td colSpan="7" className="p-8 text-center text-slate-400">No trades generated yet. Click "Run Backtest" to start.</td></tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

// ==========================================
// 4. Main App
// ==========================================

export default function App() {
    const [step, setStep] = useState(1);
    const [status, setStatus] = useState("idle");
    const [rawData, setRawData] = useState([]);
    const [metadata, setMetadata] = useState({ products: [], minDate: new Date(), maxDate: new Date(), allContracts: [] });
    
    const [activeConfig, setActiveConfig] = useState(null);
    const [draftConfig, setDraftConfig] = useState({ product: "", start: null, end: null, mode: "timeWeighted", contract: "" });

    const [stratParams, setStratParams] = useState({
        atrPeriod: 50,
        trenderMult: 2.5,
        macdFast: 8,
        macdSlow: 21,
        macdSig: 5,
        riskTarget: 2.0, 
        spreadThreshold: 500 
    });

    const [timeframe, setTimeframe] = useState('4H'); // 4H, 1D, 1W
    const [isOptimizing, setIsOptimizing] = useState(false);
    const [optResult, setOptResult] = useState(null);
    
    const [layers, setLayers] = useState({
        price: true,
        trender: true,
        td: true,
        macd: true,
        basis: true 
    });

    const [processedData, setProcessedData] = useState([]);
    const [strategyData, setStrategyData] = useState(null);

    // Format Date Helper defined in App Scope
    const formatDate = (d) => d ? d.toISOString().split('T')[0] : '';

    const getAvailableContracts = (product) => {
        const contracts = new Set(rawData.filter(d => d.product === product).map(d => d.contractMonth));
        return Array.from(contracts).sort((a,b) => {
            const parse = (s) => {
                const match = s.match(/([A-Za-z]{3})\s?(\d{2,4})/);
                if(!match) return 0;
                let y = parseInt(match[2]);
                if(y<100) y+=2000;
                const m = {'Jan':0,'Feb':1,'Mar':2,'Apr':3,'May':4,'Jun':5,'Jul':6,'Aug':7,'Sep':8,'Oct':9,'Nov':10,'Dec':11}[match[1]];
                return new Date(y, m).getTime();
            };
            return parse(a) - parse(b);
        });
    };

    const handleFileUpload = (event) => {
        const file = event.target.files[0];
        if (!file) return;
        setStatus("loading");
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const res = parseCSV(e.target.result);
                setRawData(res.data);
                setMetadata({ products: res.products, minDate: res.minDate, maxDate: res.maxDate });
                const defProd = res.products.find(p => p.includes('Capesize') || p.includes('5TC')) || res.products[0];
                const defRange = { start: res.minDate, end: res.maxDate };
                setDraftConfig({ product: defProd, ...defRange, mode: "timeWeighted", contract: "" });
                setActiveConfig({ product: defProd, ...defRange, mode: "timeWeighted", contract: "" });
                setStatus("ready");
            } catch (err) {
                console.error(err); alert("File parse error"); setStatus("idle");
            }
        };
        reader.readAsText(file);
    };

    const handleGenerateData = () => {
        if (!draftConfig.product) return;
        if (draftConfig.mode === "single" && !draftConfig.contract) {
            const avail = getAvailableContracts(draftConfig.product);
            if(avail.length > 0) {
                setDraftConfig(prev => ({...prev, contract: avail[avail.length-1]}));
                setActiveConfig({...draftConfig, contract: avail[avail.length-1]});
                return;
            }
        }
        setActiveConfig({ ...draftConfig });
    };

    const handleRunBacktest = () => {
        if (processedData.length === 0) return;
        const resampled = resampleData(processedData, timeframe);
        const withIndicators = calculateIndicators(resampled, stratParams);
        const backtestRes = runBacktest(withIndicators, stratParams);
        setStrategyData({
            data: backtestRes.resultData,
            trades: backtestRes.trades,
            stats: backtestRes.stats,
            last: backtestRes.resultData[backtestRes.resultData.length - 1]
        });
        setOptResult(null); 
    };

    const handleOptimize = async () => {
        if (processedData.length === 0) return;
        setIsOptimizing(true);
        setOptResult(null);

        const resampled = resampleData(processedData, timeframe);
        const atrRange = [30, 50, 70];
        const multRange = [2.0, 2.5, 3.0];
        const riskRange = [1.0, 2.0, 3.0];

        let bestScore = -Infinity;
        let bestParams = null;
        let bestStats = null;

        setTimeout(() => {
            for(let a of atrRange) {
                for(let m of multRange) {
                    for(let r of riskRange) {
                        const testParams = { ...stratParams, atrPeriod: a, trenderMult: m, riskTarget: r };
                        const withInd = calculateIndicators(resampled, testParams);
                        const res = runBacktest(withInd, testParams);
                        const dd = Math.max(0.01, res.stats.maxDrawdown);
                        const score = res.stats.cagr / dd;

                        if (score > bestScore) {
                            bestScore = score;
                            bestParams = testParams;
                            bestStats = res.stats;
                        }
                    }
                }
            }
            setStratParams(bestParams);
            setOptResult(bestStats);
            const withInd = calculateIndicators(resampled, bestParams);
            const res = runBacktest(withInd, bestParams);
            setStrategyData({
                data: res.resultData,
                trades: res.trades,
                stats: res.stats,
                last: res.resultData[res.resultData.length - 1]
            });
            setIsOptimizing(false);
        }, 100);
    };

    useEffect(() => {
        if (!activeConfig || rawData.length === 0) return;
        
        let result = [];
        if (activeConfig.mode === "single") {
            result = processSingleContractData(rawData, activeConfig.product, activeConfig.contract);
        } else {
            const synthetic = processTimeWeightedData(rawData, activeConfig.product);
            const s = activeConfig.start.getTime();
            const e = activeConfig.end.getTime();
            result = synthetic.filter(d => {
                const t = d.date.getTime();
                return t >= s && t <= e;
            });
        }
        
        setProcessedData(result);
        setStrategyData(null); 
    }, [activeConfig, rawData]);

    const formatXAxis = (tickItem) => {
        if (!tickItem) return '';
        if (timeframe === '4H') return tickItem.substring(5, 16).replace('T', ' '); 
        return tickItem.substring(0, 10); 
    };

    const backgroundRegions = useMemo(() => {
        if (!strategyData || !strategyData.data || !layers.basis) return []; // Check layers.basis
        
        const regions = [];
        let currentRegion = null;
        
        strategyData.data.forEach((d) => {
            const isBullish = d.spread > 0;
            
            if (!currentRegion) {
                currentRegion = { start: d.dateStr, end: d.dateStr, isBullish };
            } else if (currentRegion.isBullish !== isBullish) {
                regions.push(currentRegion);
                currentRegion = { start: d.dateStr, end: d.dateStr, isBullish };
            } else {
                currentRegion.end = d.dateStr;
            }
        });
        if (currentRegion) regions.push(currentRegion);
        return regions;
    }, [strategyData, layers.basis]); // Add dependency

    const gradientOffset = () => {
        if (processedData.length === 0) return 0;
        const max = Math.max(...processedData.map(i => i.spread));
        const min = Math.min(...processedData.map(i => i.spread));
        if (max <= 0) return 0;
        if (min >= 0) return 1;
        return max / (max - min);
    };

    const toggleLayer = (key) => setLayers(prev => ({...prev, [key]: !prev[key]}));

    const availableContracts = useMemo(() => {
        if(!draftConfig.product) return [];
        return getAvailableContracts(draftConfig.product);
    }, [draftConfig.product, rawData]);

    return (
        <div className="min-h-screen bg-slate-50 font-sans text-slate-800">
            <header className="bg-white border-b border-slate-200 sticky top-0 z-20 shadow-sm px-6 py-3 flex justify-between items-center">
                <div className="flex items-center gap-2">
                    <Activity className="text-blue-600" size={24} />
                    <h1 className="text-xl font-bold text-slate-800">Cape Crusader <span className="text-slate-400 font-normal">v3.15</span></h1>
                </div>
                <div className="flex bg-slate-100 p-1 rounded-lg">
                    <button onClick={() => setStep(1)} className={`px-4 py-1.5 rounded-md text-sm font-bold transition-all ${step===1 ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500'}`}>1. Data Processor</button>
                    <button onClick={() => setStep(2)} disabled={status !== 'ready'} className={`px-4 py-1.5 rounded-md text-sm font-bold transition-all ${step===2 ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500'}`}>2. Strategy Analysis</button>
                </div>
                <label className="flex items-center gap-2 cursor-pointer bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-lg text-sm font-bold">
                    <Upload size={16} /> Import CSV
                    <input type="file" accept=".csv" className="hidden" onChange={handleFileUpload} />
                </label>
            </header>

            <main className="p-6 max-w-7xl mx-auto">
                {status === "idle" && (
                     <div className="flex flex-col items-center justify-center h-96 bg-white rounded-xl border-2 border-dashed border-slate-300 text-slate-400">
                        <Upload size={48} className="mb-4 text-slate-300" />
                        <p className="text-lg font-medium">Please Upload CSV</p>
                    </div>
                )}

                {status === "ready" && step === 1 && (
                    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 mb-6 grid grid-cols-1 md:grid-cols-4 gap-6 items-end">
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-slate-500 uppercase">Product</label>
                                <select value={draftConfig.product} onChange={(e) => setDraftConfig({...draftConfig, product: e.target.value})} className="w-full p-2 bg-slate-50 border border-slate-300 rounded-lg text-sm font-bold">
                                    {metadata.products.map(p => <option key={p} value={p}>{p}</option>)}
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-slate-500 uppercase">Processing Mode</label>
                                <div className="flex bg-slate-100 p-1 rounded-lg">
                                    <button onClick={() => setDraftConfig({...draftConfig, mode: 'timeWeighted'})} className={`flex-1 text-xs py-1.5 rounded font-bold transition-all ${draftConfig.mode === 'timeWeighted' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500'}`}>Time Weighted</button>
                                    <button onClick={() => setDraftConfig({...draftConfig, mode: 'single'})} className={`flex-1 text-xs py-1.5 rounded font-bold transition-all ${draftConfig.mode === 'single' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500'}`}>Single Contract</button>
                                </div>
                            </div>
                            {draftConfig.mode === 'timeWeighted' ? (
                                <div className="space-y-2 md:col-span-2">
                                    <label className="text-xs font-bold text-slate-500 uppercase">Date Range</label>
                                    <div className="flex gap-4">
                                        <input type="date" className="flex-1 p-2 bg-slate-50 border border-slate-300 rounded-lg text-sm" value={formatDate(draftConfig.start)} onChange={(e) => setDraftConfig({...draftConfig, start: new Date(e.target.value)})}/>
                                        <ArrowRight className="text-slate-300 my-auto" size={16}/>
                                        <input type="date" className="flex-1 p-2 bg-slate-50 border border-slate-300 rounded-lg text-sm" value={formatDate(draftConfig.end)} onChange={(e) => setDraftConfig({...draftConfig, end: new Date(e.target.value)})}/>
                                    </div>
                                </div>
                            ) : (
                                <div className="space-y-2 md:col-span-2">
                                    <label className="text-xs font-bold text-slate-500 uppercase">Select Contract Month</label>
                                    <select value={draftConfig.contract} onChange={(e) => setDraftConfig({...draftConfig, contract: e.target.value})} className="w-full p-2 bg-slate-50 border border-slate-300 rounded-lg text-sm font-medium">
                                        <option value="">-- Select Contract --</option>
                                        {availableContracts.map(c => <option key={c} value={c}>{c}</option>)}
                                    </select>
                                </div>
                            )}
                            <button onClick={handleGenerateData} className="md:col-start-4 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg font-bold shadow-md active:scale-95">Update Chart</button>
                        </div>
                        {processedData.length > 0 && (
                            <div className="space-y-6">
                                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 h-96">
                                    <h3 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2"><Activity size={16}/> Price Data Check</h3>
                                    <ResponsiveContainer width="100%" height="90%">
                                        <ComposedChart data={processedData}>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9"/>
                                            <XAxis dataKey="dateStr" tick={{fontSize:10}} minTickGap={50} tickFormatter={tick => tick.substring(0,10)}/>
                                            <YAxis domain={['auto','auto']} tick={{fontSize:10}} width={40} tickFormatter={fmt}/>
                                            <Tooltip formatter={fmt}/>
                                            <Legend/>
                                            {processedData[0].M2_Price !== null && <Line name="M1" dataKey="M1_Price" stroke="#cbd5e1" dot={false}/>}
                                            {processedData[0].M2_Price !== null && <Line name="M2" dataKey="M2_Price" stroke="#e2e8f0" dot={false}/>}
                                            <Line name="Price" dataKey="close" stroke="#2563eb" strokeWidth={2} dot={false}/>
                                        </ComposedChart>
                                    </ResponsiveContainer>
                                </div>
                                {activeConfig.mode === 'timeWeighted' && (
                                    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 h-64">
                                        <h3 className="text-sm font-bold text-slate-700 mb-2">M1-M2 Spread</h3>
                                        <ResponsiveContainer width="100%" height="90%">
                                            <AreaChart data={processedData}>
                                                <defs>
                                                    <linearGradient id="splitColor" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset={gradientOffset()} stopColor="#10b981" stopOpacity={0.4}/>
                                                        <stop offset={gradientOffset()} stopColor="#ef4444" stopOpacity={0.4}/>
                                                    </linearGradient>
                                                </defs>
                                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9"/>
                                                <XAxis dataKey="dateStr" hide/>
                                                <YAxis width={40} tick={{fontSize:10}} tickFormatter={fmt}/>
                                                <Tooltip formatter={fmt}/>
                                                <ReferenceLine y={0} stroke="#000"/>
                                                <Area type="monotone" dataKey="spread" stroke="#64748b" fill="url(#splitColor)"/>
                                            </AreaChart>
                                        </ResponsiveContainer>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {status === "ready" && step === 2 && (
                    <div className="animate-in fade-in zoom-in-95 duration-500 space-y-6">
                        {/* 1. Params */}
                        <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 relative">
                             <div className="flex justify-between items-center mb-4">
                                <h3 className="font-bold text-slate-800 flex items-center gap-2"><Settings size={18}/> Strategy Parameters</h3>
                                {optResult && (
                                    <div className="flex items-center gap-2 bg-green-50 text-green-700 px-3 py-1 rounded-full text-xs font-bold border border-green-200 animate-in fade-in slide-in-from-top-2">
                                        <Check size={12}/> Optimized: CAGR {fmtPct(optResult.cagr)} / MaxDD {fmtPct(optResult.maxDrawdown)}
                                    </div>
                                )}
                            </div>
                            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 items-end">
                                <div><label className="text-xs font-bold text-slate-500">ATR Period</label><input type="number" className="w-full p-2 border rounded text-sm font-mono" value={stratParams.atrPeriod} onChange={e=>setStratParams({...stratParams, atrPeriod: Number(e.target.value)})}/></div>
                                <div><label className="text-xs font-bold text-slate-500">SuperTrend Mult</label><input type="number" step="0.1" className="w-full p-2 border rounded text-sm font-mono" value={stratParams.trenderMult} onChange={e=>setStratParams({...stratParams, trenderMult: Number(e.target.value)})}/></div>
                                <div><label className="text-xs font-bold text-slate-500">MACD Fast</label><input type="number" className="w-full p-2 border rounded text-sm font-mono" value={stratParams.macdFast} onChange={e=>setStratParams({...stratParams, macdFast: Number(e.target.value)})}/></div>
                                <div><label className="text-xs font-bold text-slate-500">MACD Slow</label><input type="number" className="w-full p-2 border rounded text-sm font-mono" value={stratParams.macdSlow} onChange={e=>setStratParams({...stratParams, macdSlow: Number(e.target.value)})}/></div>
                                <div><label className="text-xs font-bold text-slate-500">MACD Signal</label><input type="number" className="w-full p-2 border rounded text-sm font-mono" value={stratParams.macdSig} onChange={e=>setStratParams({...stratParams, macdSig: Number(e.target.value)})}/></div>
                                <div className="bg-blue-50 p-1 rounded"><label className="text-xs font-bold text-blue-600">Risk Target %</label><input type="number" step="0.5" className="w-full p-2 border border-blue-200 rounded text-sm font-mono text-blue-700" value={stratParams.riskTarget} onChange={e=>setStratParams({...stratParams, riskTarget: Number(e.target.value)})}/></div>
                                <div className="bg-amber-50 p-1 rounded"><label className="text-xs font-bold text-amber-600">Spread Thresh</label><input type="number" className="w-full p-2 border border-amber-200 rounded text-sm font-mono text-amber-700" value={stratParams.spreadThreshold} onChange={e=>setStratParams({...stratParams, spreadThreshold: Number(e.target.value)})}/></div>
                                <div className="col-span-2 md:col-span-1 lg:col-span-1 flex gap-2 mt-auto">
                                    <button onClick={handleRunBacktest} disabled={isOptimizing} className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg font-bold shadow-md flex items-center justify-center h-10 disabled:opacity-50"><Play size={16} fill="currentColor"/></button>
                                    <button onClick={handleOptimize} disabled={isOptimizing} className="flex-1 bg-purple-600 hover:bg-purple-700 text-white py-2 rounded-lg font-bold shadow-md flex items-center justify-center h-10 disabled:opacity-50"><Sparkles size={16}/></button>
                                </div>
                            </div>
                        </div>

                        {strategyData ? (
                            <>
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                    <StatCard title="Total Return" value={fmtPct(strategyData.stats.totalReturn)} type={strategyData.stats.totalReturn > 0 ? "bull" : "bear"} subtext={`CAGR: ${fmtPct(strategyData.stats.cagr)}`} />
                                    <StatCard title="Max Drawdown" value={fmtPct(strategyData.stats.maxDrawdown)} type="bear" subtext="Peak to Valley" />
                                    <StatCard title="Action Call" value={strategyData.last.position > 0 ? "HOLD LONG" : (strategyData.last.position < 0 ? "HOLD SHORT" : "WAIT")} type={strategyData.last.position !== 0 ? "bull" : "neutral"} subtext={`Pos: ${strategyData.last.position} lots`} />
                                    <StatCard title="Final Equity" value={`$${fmt(strategyData.last.equity)}`} type="bull" subtext="Net Result" />
                                </div>

                                {/* Main Unified Chart */}
                                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 flex flex-col gap-4">
                                    
                                    {/* Chart Toolbar */}
                                    <div className="flex justify-between items-center border-b border-slate-100 pb-3">
                                        <div className="flex items-center gap-4">
                                            <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2"><Crosshair size={16}/> Price & Signal Analysis</h3>
                                            
                                            {/* Timeframe Selector */}
                                            <div className="flex bg-slate-100 rounded-lg p-0.5 items-center">
                                                <Clock size={14} className="ml-2 mr-1 text-slate-400"/>
                                                {['4H', '1D', '1W'].map(tf => (
                                                    <button
                                                        key={tf}
                                                        onClick={() => { setTimeframe(tf); setStrategyData(null); }} // Clear to force user to re-run or trigger auto re-run effect
                                                        className={`px-3 py-1 text-xs font-bold rounded-md transition-all ${timeframe === tf ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                                                    >
                                                        {tf}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>

                                        <div className="flex gap-2">
                                            {[
                                                {id: 'price', label: 'Price', color: 'text-slate-600'},
                                                {id: 'trender', label: 'Trender', color: 'text-indigo-600'},
                                                {id: 'td', label: 'TD Signals', color: 'text-emerald-600'},
                                                {id: 'macd', label: 'MACD', color: 'text-blue-600'},
                                                {id: 'basis', label: 'Basis', color: 'text-amber-600'},
                                            ].map(L => (
                                                <button 
                                                    key={L.id}
                                                    onClick={() => toggleLayer(L.id)}
                                                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-bold border transition-all ${layers[L.id] ? 'bg-slate-50 border-slate-300 ' + L.color : 'bg-white border-slate-100 text-slate-300'}`}
                                                >
                                                    {layers[L.id] ? <Eye size={14}/> : <EyeOff size={14}/>}
                                                    {L.label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Price Chart (Always Top) */}
                                    <div style={{ height: (layers.macd && layers.basis) ? '350px' : (layers.macd || layers.basis ? '450px' : '550px') }} className="w-full transition-all duration-300">
                                        <ResponsiveContainer width="100%" height="100%">
                                            <ComposedChart data={strategyData.data} margin={{top:10, right:10, bottom:0, left:0}} syncId="unified">
                                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9"/>
                                                <XAxis dataKey="dateStr" tick={{fontSize:10}} minTickGap={50} hide={layers.macd || layers.basis} tickFormatter={formatXAxis}/>
                                                <YAxis 
                                                    domain={['auto', 'auto']} 
                                                    tick={{fontSize:10}} 
                                                    width={50} 
                                                    tickFormatter={(value) => value.toLocaleString()} 
                                                    label={{ value: 'Price ($)', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fontSize: 10, fill: '#64748b' } }}
                                                />
                                                <Tooltip contentStyle={{borderRadius:'8px', border:'none', boxShadow:'0 4px 12px rgba(0,0,0,0.1)'}} formatter={fmt}/>
                                                <Legend verticalAlign="top" height={36}/>
                                                
                                                {/* Background Color Regions */}
                                                {backgroundRegions.map((region, index) => (
                                                    <ReferenceArea
                                                        key={index}
                                                        x1={region.start}
                                                        x2={region.end}
                                                        fill={region.isBullish ? "#22c55e" : "#ef4444"}
                                                        fillOpacity={0.05}
                                                    />
                                                ))}

                                                {layers.price && <Line name="Price" dataKey="close" stroke="#334155" strokeWidth={2} dot={false}/>}
                                                
                                                {layers.trender && <Line name="Support (Bull)" dataKey="trenderGreen" stroke="#10b981" strokeWidth={2} dot={false} type="stepAfter"/>}
                                                {layers.trender && <Line name="Resistance (Bear)" dataKey="trenderRed" stroke="#ef4444" strokeWidth={2} dot={false} type="stepAfter"/>}
                                                
                                                <Line dataKey="close" stroke="none" dot={<SignalMarker visible={layers.td}/>} legendType="none" isAnimationActive={false}/>
                                            </ComposedChart>
                                        </ResponsiveContainer>
                                    </div>

                                    {/* Basis Spread Chart (Middle) */}
                                    {layers.basis && (
                                        <div className="h-32 w-full border-t border-slate-50 pt-2">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <AreaChart data={strategyData.data} margin={{top:0, right:10, bottom:0, left:0}} syncId="unified">
                                                    <defs>
                                                        <linearGradient id="splitColor" x1="0" y1="0" x2="0" y2="1">
                                                            <stop offset={gradientOffset()} stopColor="#10b981" stopOpacity={0.4}/>
                                                            <stop offset={gradientOffset()} stopColor="#ef4444" stopOpacity={0.4}/>
                                                        </linearGradient>
                                                    </defs>
                                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9"/>
                                                    <XAxis dataKey="dateStr" tick={{fontSize:10}} minTickGap={50} hide={layers.macd} tickFormatter={formatXAxis}/>
                                                    <YAxis width={50} tick={{fontSize:10}} label={{ value: 'Spread', angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fontSize: 10, fill: '#64748b' } }}/>
                                                    <Tooltip formatter={fmt}/>
                                                    <ReferenceLine y={0} stroke="#000"/>
                                                    <Area type="monotone" dataKey="spread" stroke="#64748b" fill="url(#splitColor)"/>
                                                </AreaChart>
                                            </ResponsiveContainer>
                                        </div>
                                    )}

                                    {/* MACD Chart (Synced Bottom) */}
                                    {layers.macd && (
                                        <div className="h-32 w-full border-t border-slate-50 pt-2">
                                            <ResponsiveContainer width="100%" height="100%">
                                                <ComposedChart data={strategyData.data} margin={{top:0, right:10, bottom:0, left:0}} syncId="unified">
                                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9"/>
                                                    <XAxis dataKey="dateStr" tick={{fontSize:10}} minTickGap={50} height={20} tickFormatter={formatXAxis}/>
                                                    <YAxis tick={{fontSize:10}} width={50}/>
                                                    <Tooltip formatter={fmt}/>
                                                    <ReferenceLine y={0} stroke="#000"/>
                                                    <Bar dataKey="macd.hist" fill="#94a3b8" name="Histogram" opacity={0.3}>
                                                        {strategyData.data.map((entry, index) => (
                                                            <Cell key={`cell-${index}`} fill={entry.macd.hist > 0 ? '#10b981' : '#ef4444'} />
                                                        ))}
                                                    </Bar>
                                                    {/* MACD Lines */}
                                                    <Line name="MACD (Fast)" type="monotone" dataKey="macd.line" stroke="#3b82f6" strokeWidth={1} dot={false} />
                                                    <Line name="Signal (Slow)" type="monotone" dataKey="macd.signal" stroke="#f97316" strokeWidth={1} dot={false} />
                                                </ComposedChart>
                                            </ResponsiveContainer>
                                        </div>
                                    )}
                                </div>

                                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100 h-72">
                                    <h3 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2"><DollarSign size={16}/> Equity Curve</h3>
                                    <ResponsiveContainer width="100%" height="90%">
                                        <AreaChart data={strategyData.data}>
                                            <defs>
                                                <linearGradient id="eqColor" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3}/>
                                                    <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                                                </linearGradient>
                                            </defs>
                                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9"/>
                                            <XAxis dataKey="dateStr" hide/>
                                            <YAxis domain={['auto','auto']} tick={{fontSize:10}} width={50} tickFormatter={(val)=>`$${(val/1000).toFixed(0)}k`}/>
                                            <Tooltip formatter={(val)=>`$${fmt(val)}`}/>
                                            <Area type="monotone" dataKey="equity" stroke="#8b5cf6" fill="url(#eqColor)" strokeWidth={2}/>
                                        </AreaChart>
                                    </ResponsiveContainer>
                                </div>

                                <TradeLogTable trades={strategyData.trades} />
                            </>
                        ) : (
                             <div className="flex flex-col items-center justify-center h-64 bg-slate-50 rounded-xl border-2 border-dashed border-slate-200 text-slate-400">
                                <BarChart3 size={32} className="mb-2 opacity-50"/>
                                <p>Click "Run" to generate strategy analysis ({timeframe})</p>
                            </div>
                        )}
                    </div>
                )}
            </main>
        </div>
    );
}