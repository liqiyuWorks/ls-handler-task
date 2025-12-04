import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  Anchor, 
  User, 
  ChevronDown, 
  ChevronRight,
  Activity, 
  X, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Plus,
  Trophy,
  CandlestickChart as CandlestickIcon,
  History,
  Clock,
  List,
  Zap,
  Trash2,
  Medal,
  DollarSign
} from 'lucide-react';
import { 
  ComposedChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer
} from 'recharts';

// --- Global Styles for Scrollbars ---
const ScrollbarStyles = () => (
  <style>{`
    .custom-scrollbar::-webkit-scrollbar {
      width: 6px;
      height: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
      background: #0f172a; 
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
      background: #334155; 
      border-radius: 3px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
      background: #475569; 
    }
    /* Firefox */
    .custom-scrollbar {
      scrollbar-width: thin;
      scrollbar-color: #334155 #0f172a;
    }
  `}</style>
);

// --- Constants & Config ---
const AVAILABLE_SYMBOLS = ['C5TC', 'P5TC', 'C5', 'S11'];
const AVAILABLE_MONTHS = ['Dec 25', 'Jan 26', 'Feb 26', 'Mar 26', 'Q1 26', 'Q2 26', 'Cal 26'];

const BASE_PRICES = {
  'C5TC': 24860.00,
  'P5TC': 12450.00,
  'C5': 10.00, // Adjusted base to 10.00 as requested
  'S11': 18500.25
};

const PRIZE_POOL = 100000000; 

const MARGIN_RATIOS = { 'C5TC': 0.33, 'P5TC': 0.20, 'C5': 0.33, 'S11': 0.20, 'DEFAULT': 0.25 };

const TIMEFRAME_CONFIG = {
  '5m':  { interval: 5 * 60 * 1000, label: '5m' },
  '15m': { interval: 15 * 60 * 1000, label: '15m' },
  '30m': { interval: 30 * 60 * 1000, label: '30m' },
  '1H':  { interval: 60 * 60 * 1000, label: '1H' },
  '2H':  { interval: 120 * 60 * 1000, label: '2H' },
  '4H':  { interval: 240 * 60 * 1000, label: '4H' },
  '1D':  { interval: 24 * 60 * 60 * 1000, label: '1D' },
  '1W':  { interval: 7 * 24 * 60 * 60 * 1000, label: '1W' },
};

const INITIAL_POSITIONS = [
  { id: 1, contract: 'C5TC', month: 'Jan 26', side: 'BUY', lots: 5, entry: 24860, mark: 24865, margin: 41022, openFees: 374.3 }, 
];

const INITIAL_HISTORY = [
  { id: 'h1', time: '09:30:05', type: 'OPEN', symbol: 'C5TC', side: 'BUY', price: 24860, lots: 5, pl: null },
];

const MOCK_COMPETITORS = [
  { name: 'AlphaTrader', team: 'Quantum Capital', roi: 452.5 },
  { name: 'ShippingKing', team: 'Poseidon Ventures', roi: 312.0 },
  { name: 'BalticBaron', team: 'Nordic Routes', roi: 189.4 },
  { name: 'CapesizeCmdr', team: 'Heavy Lift Inc', roi: 145.2 },
  { name: 'FreightLord', team: 'Global Logistics', roi: 98.1 },
  { name: 'OceanMaster', team: 'Blue Wave', roi: 87.5 },
  { name: 'PanamaxPrince', team: 'Canal Traders', roi: 76.2 },
  { name: 'DerivativesDuke', team: 'Hedging Pro', roi: 65.4 },
  { name: 'HedgeFundHero', team: 'Alpha Seekers', roi: 54.1 },
  { name: 'GlobalMacro', team: 'Macro Strategy', roi: 43.8 },
];

// --- Helpers for Symbol Specific Logic ---

// Get Tick Size: C5 adjusted to 0.05 to support 9.85, 11.05 etc.
const getTickSize = (symbol) => (symbol === 'C5' ? 0.05 : 5);

// Round to Symbol specific tick
const roundToTick = (val, symbol) => {
  const tick = getTickSize(symbol);
  return Math.round(val / tick) * tick;
};

// Format Number: C5 needs decimals (10.50), others integers (24860)
const formatNumber = (val, symbol) => {
  if (symbol === 'C5') {
    return new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val);
  }
  return new Intl.NumberFormat('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(val);
};

// Get Volatility: C5 needs significantly higher pct volatility to swing from 10.0 to 12.0 or 7.5
const getVolatility = (symbol) => (symbol === 'C5' ? 0.08 : 0.0005); 

const formatUSD = (val) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(val);

const calculateFees = (price, lots) => {
  const clearing = lots * 20;
  const contractValue = price * lots; 
  const comm = contractValue * 0.001;
  return clearing + comm;
};

// --- Generators ---
const generateCandleData = (basePrice, timeframe, symbol) => {
  const config = TIMEFRAME_CONFIG[timeframe] || TIMEFRAME_CONFIG['1H'];
  const volatility = getVolatility(symbol);
  const now = Date.now();
  let prevClose = roundToTick(basePrice, symbol);
  
  return Array.from({ length: 60 }, (_, i) => {
    const timeOffset = (59 - i) * config.interval;
    const time = new Date(now - timeOffset);
    let timeLabel = (timeframe.includes('m') || timeframe.includes('H')) 
      ? `${time.getHours().toString().padStart(2,'0')}:${time.getMinutes().toString().padStart(2,'0')}` 
      : `${time.getMonth()+1}/${time.getDate()}`;

    const rawChange = (Math.random() - 0.5) * basePrice * volatility * 2; 
    const open = prevClose;
    const close = roundToTick(open + rawChange, symbol);
    
    // Ensure High/Low respects tick
    const range = Math.abs(open - close);
    const rawHigh = Math.max(open, close) + Math.random() * (range + basePrice * volatility * 0.5);
    const rawLow = Math.min(open, close) - Math.random() * (range + basePrice * volatility * 0.5);
    
    const finalHigh = Math.max(roundToTick(rawHigh, symbol), open, close);
    const finalLow = Math.min(roundToTick(rawLow, symbol), open, close);
    prevClose = close;

    return {
      time: timeLabel, timestamp: time.getTime(),
      open, close, high: finalHigh, low: finalLow,
      body: [Math.min(open, close), Math.max(open, close)],
      symbol // Pass symbol for tooltip formatting
    };
  });
};

const generateMockTape = (symbol) => {
  if (!symbol) symbol = 'C5TC'; 
  const side = Math.random() > 0.5 ? 'BUY' : 'SELL';
  const exchange = Math.random() > 0.7 ? 'EEX' : 'SGX';
  const month = AVAILABLE_MONTHS[Math.floor(Math.random() * AVAILABLE_MONTHS.length)];
  
  const base = BASE_PRICES[symbol] || 20000;
  // C5 logic for tape prices (wider spread)
  const vol = symbol === 'C5' ? 0.1 : 0.01;
  const price = roundToTick(base + (Math.random() - 0.5) * (base * vol), symbol);

  return {
    id: Math.random().toString(36).substr(2, 9),
    time: new Date().toLocaleTimeString('en-GB'),
    contract: symbol,
    month: month,
    price: price,
    lots: (Math.floor(Math.random() * 5) + 1) * 5,
    side,
    exchange
  };
};

// --- Components ---
const CandlestickShape = (props) => {
  const { x, y, width, height, payload } = props;
  const { open, close, high, low } = payload;
  const isRising = close >= open;
  const color = isRising ? '#10b981' : '#f43f5e'; 
  const bodyTopVal = Math.max(open, close);
  const bodyBottomVal = Math.min(open, close);
  const safeBodyHeightVal = (bodyTopVal - bodyBottomVal) || 0.00001;
  const pixelRatio = height / safeBodyHeightVal; 
  const topWickLen = (high - bodyTopVal) * pixelRatio;
  const bottomWickLen = (bodyBottomVal - low) * pixelRatio;
  const centerX = x + width / 2;
  const bodyTopY = y;
  const bodyBottomY = y + height;

  return (
    <g>
      <line x1={centerX} y1={bodyTopY - topWickLen} x2={centerX} y2={bodyBottomY + bottomWickLen} stroke={color} strokeWidth={1.5} />
      <rect x={x} y={y} width={width} height={Math.max(1, height)} fill={color} stroke={color} />
    </g>
  );
};

const CustomOHLCTooltip = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const sym = data.symbol || 'C5TC';
    return (
      <div className="bg-[#1e293b] border border-slate-700 p-2 rounded shadow-xl text-xs font-mono z-50">
        <div className="text-slate-400 mb-1">Time: {data.time}</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          <span className="text-emerald-400">Open:</span> <span className="text-right text-white">{formatNumber(data.open, sym)}</span>
          <span className="text-rose-400">High:</span> <span className="text-right text-white">{formatNumber(data.high, sym)}</span>
          <span className="text-rose-400">Low:</span> <span className="text-right text-white">{formatNumber(data.low, sym)}</span>
          <span className="text-emerald-400">Close:</span> <span className="text-right text-white">{formatNumber(data.close, sym)}</span>
        </div>
      </div>
    );
  }
  return null;
};

// --- Main Application ---

export default function App() {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [balance, setBalance] = useState(998685.00); 
  
  const [isCountdownOpen, setIsCountdownOpen] = useState(true);
  const [isPerformanceOpen, setIsPerformanceOpen] = useState(true);
  const [isTopPerformersOpen, setIsTopPerformersOpen] = useState(true);
  const [isFeesOpen, setIsFeesOpen] = useState(true);

  const [activeTab, setActiveTab] = useState('positions'); 

  // Initial Watchlist with C5 example as requested
  const [watchList, setWatchList] = useState([
    { id: 'row-1', symbol: 'C5TC', month: 'Jan 26', price: 24860, change: 15, changePct: 0.06 },
    { id: 'row-2', symbol: 'C5', month: 'Jan 26', price: 9.85, change: -0.15, changePct: -1.5 }, // Realistic C5 start
    { id: 'row-3', symbol: 'P5TC', month: 'Jan 26', price: 12450, change: -5, changePct: -0.04 },
  ]);

  const [positions, setPositions] = useState(INITIAL_POSITIONS);
  const [activeOrders, setActiveOrders] = useState([]); 
  const [marketTape, setMarketTape] = useState([]); 
  const [history, setHistory] = useState(INITIAL_HISTORY);
  
  const [activeRowId, setActiveRowId] = useState('row-1');
  const [isChartVisible, setIsChartVisible] = useState(true);
  const [selectedTimeframe, setSelectedTimeframe] = useState('2H');
  
  const activeRow = useMemo(() => 
    watchList.find(r => r.id === activeRowId) || watchList[0] || { symbol: 'C5TC', month: 'Jan 26', price: 0, change: 0, changePct: 0 },
  [watchList, activeRowId]);
  
  const [candleData, setCandleData] = useState([]);

  const [lots, setLots] = useState(5);
  const [orderType, setOrderType] = useState('MARKET'); 
  const [limitPrice, setLimitPrice] = useState(0);
  const [orderSymbol, setOrderSymbol] = useState(activeRow.symbol);
  const [orderMonth, setOrderMonth] = useState(activeRow.month);

  // --- Initial & Sync ---
  useEffect(() => {
    // Initial Tape
    const tape = Array.from({ length: 15 }, () => {
        const randomSym = AVAILABLE_SYMBOLS[Math.floor(Math.random() * AVAILABLE_SYMBOLS.length)];
        return generateMockTape(randomSym);
    });
    setMarketTape(tape);
  }, []);

  useEffect(() => {
    setOrderSymbol(activeRow.symbol);
    setOrderMonth(activeRow.month);
    setLimitPrice(roundToTick(activeRow.price, activeRow.symbol));
  }, [activeRow.symbol, activeRow.month]); // Don't depend on price for stable input

  useEffect(() => {
    const existingRow = watchList.find(r => r.symbol === orderSymbol && r.month === orderMonth);
    if (existingRow) setActiveRowId(existingRow.id);
    
    // Chart update
    const base = BASE_PRICES[orderSymbol] || 20000;
    setCandleData(generateCandleData(base, selectedTimeframe, orderSymbol));
  }, [orderSymbol, orderMonth, selectedTimeframe]);

  useEffect(() => {
     const timer = setInterval(() => setCurrentTime(new Date()), 1000);
     return () => clearInterval(timer);
  }, []);

  // --- Core Simulator ---
  useEffect(() => {
    const interval = setInterval(() => {
      // 1. Update Market Prices
      setWatchList(prevList => prevList.map(item => {
        const volatility = getVolatility(item.symbol);
        // Ensure random move is enough to trigger a tick
        let rawMove = (Math.random() - 0.5) * (BASE_PRICES[item.symbol] * volatility * 5); 
        
        // Force a small move if rawMove is too small for the tick
        const tick = getTickSize(item.symbol);
        if (Math.abs(rawMove) < tick / 2) {
             rawMove = Math.random() > 0.8 ? tick : (Math.random() < 0.2 ? -tick : 0);
        }

        const newPrice = roundToTick(item.price + rawMove, item.symbol);
        const change = newPrice - roundToTick(BASE_PRICES[item.symbol], item.symbol); 
        const changePct = (change / BASE_PRICES[item.symbol]) * 100;
        return { ...item, price: newPrice, change, changePct };
      }));
      
      // 2. Update Candle
      setCandleData(prev => {
         if (!prev.length) return prev;
         const last = prev[prev.length - 1];
         // Pass symbol to round correctly
         const symbol = last.symbol || orderSymbol; 
         const volatility = getVolatility(symbol);
         
         const rawMove = (Math.random() - 0.5) * (last.close * volatility * 0.5); 
         const newClose = roundToTick(last.close + rawMove, symbol);
         const newHigh = Math.max(last.high, newClose);
         const newLow = Math.min(last.low, newClose);
         
         const updatedLast = {
           ...last, close: newClose, high: newHigh, low: newLow,
           body: [Math.min(last.open, newClose), Math.max(last.open, newClose)]
         };
         return [...prev.slice(0, -1), updatedLast];
      });

      // 3. Tape
      if (Math.random() > 0.6) {
        setMarketTape(prev => {
           const useActive = Math.random() > 0.3;
           const symbol = useActive ? activeRow.symbol : AVAILABLE_SYMBOLS[Math.floor(Math.random() * AVAILABLE_SYMBOLS.length)];
           
           // Mock tape generation needs to be smart about pricing
           const newTrade = generateMockTape(symbol);
           // If we use active row, ensure price matches active row for realism
           if (useActive) newTrade.price = activeRow.price;

           return [newTrade, ...prev].slice(0, 50);
        });
      }

      // 4. Pending Orders
      setActiveOrders(prevOrders => {
        const remainingOrders = [];
        let ordersExecuted = false;
        prevOrders.forEach(order => {
           const w = watchList.find(r => r.symbol === order.contract && r.month === order.month);
           const currentPrice = w ? w.price : order.entry;
           let executed = false;
           if (order.side === 'BUY' && currentPrice <= order.entry) executed = true;
           if (order.side === 'SELL' && currentPrice >= order.entry) executed = true;

           if (executed) {
             ordersExecuted = true;
             const openFees = calculateFees(order.entry, order.lots);
             setBalance(b => b - openFees);
             const newPos = {
               ...order,
               id: Date.now() + Math.random(),
               entry: order.entry,
               mark: currentPrice,
               margin: order.margin,
               openFees: openFees
             };
             setPositions(currPos => [newPos, ...currPos]);
             setHistory(currHist => [{
               id: `h-${Date.now()}`, time: new Date().toLocaleTimeString('en-GB'), type: 'FILL',
               symbol: order.contract, side: order.side, price: order.entry, lots: order.lots, pl: null
             }, ...currHist]);
           } else {
             remainingOrders.push(order);
           }
        });
        return remainingOrders;
      });
    }, 1500); 
    return () => clearInterval(interval);
  }, [watchList, activeRow, selectedTimeframe]);

  // --- Calculations ---
  const currentMarketPrice = useMemo(() => {
     const w = watchList.find(r => r.symbol === orderSymbol && r.month === orderMonth);
     return w ? w.price : roundToTick(BASE_PRICES[orderSymbol] || 0, orderSymbol);
  }, [watchList, orderSymbol, orderMonth]);

  const executionPrice = orderType === 'LIMIT' ? limitPrice : currentMarketPrice;
  const marginRatio = MARGIN_RATIOS[orderSymbol] || MARGIN_RATIOS['DEFAULT'];
  const contractValue = executionPrice * lots;
  const marginRequired = contractValue * marginRatio;
  
  const clearingFee = lots * 20; 
  const commFee = contractValue * 0.001; 
  const totalEstFees = clearingFee + commFee;

  const totalLiquidationPL = useMemo(() => {
    return positions.reduce((acc, pos) => {
      const watcher = watchList.find(w => w.symbol === pos.contract && w.month === pos.month);
      const currentMark = watcher ? watcher.price : pos.mark; 
      
      const grossPL = pos.side === 'BUY' ? (currentMark - pos.entry) * pos.lots : (pos.entry - currentMark) * pos.lots;
      const closeFees = calculateFees(currentMark, pos.lots);
      return acc + (grossPL - closeFees); 
    }, 0);
  }, [positions, watchList]);

  const totalEquity = balance + totalLiquidationPL;
  const roi = (totalLiquidationPL / balance) * 100;

  const rankingData = useMemo(() => {
    const userData = { name: 'Guest Trader', team: 'Independent', roi: roi, isMe: true };
    const allParticipants = [...MOCK_COMPETITORS, userData];
    allParticipants.sort((a, b) => b.roi - a.roi);
    const myRank = allParticipants.findIndex(p => p.isMe) + 1;
    const top10 = allParticipants.slice(0, 10);
    return { top10, myRank };
  }, [roi]);

  // --- Handlers ---
  const handleOrder = (side) => {
    if (orderType === 'LIMIT') {
      const isBuyLimit = side === 'BUY' && limitPrice < currentMarketPrice;
      const isSellLimit = side === 'SELL' && limitPrice > currentMarketPrice;
      if (isBuyLimit || isSellLimit) {
        const newOrder = {
          id: Date.now(), contract: orderSymbol, month: orderMonth, side, lots,
          entry: limitPrice, margin: marginRequired, time: new Date().toLocaleTimeString('en-GB')
        };
        setActiveOrders([newOrder, ...activeOrders]);
        setHistory([{
           id: `h-${Date.now()}`, time: new Date().toLocaleTimeString('en-GB'), type: 'LIMIT',
           symbol: orderSymbol, side, price: limitPrice, lots, pl: null
        }, ...history]);
        setActiveTab('orders');
        return;
      }
    }

    const openFees = calculateFees(executionPrice, lots);
    setBalance(prev => prev - openFees);

    const newPos = {
      id: Date.now(), contract: orderSymbol, month: orderMonth, side, lots,
      entry: executionPrice, mark: currentMarketPrice, margin: marginRequired,
      openFees: openFees
    };
    setPositions([newPos, ...positions]);
    setActiveTab('positions');
    setHistory([{
      id: `h-${Date.now()}`, time: new Date().toLocaleTimeString('en-GB'), type: 'OPEN',
      symbol: orderSymbol, side, price: executionPrice, lots, pl: null
    }, ...history]);
  };

  const closePosition = (id) => {
    const pos = positions.find(p => p.id === id);
    if (pos) {
      const watcher = watchList.find(w => w.symbol === pos.contract && w.month === pos.month);
      const closePrice = watcher ? watcher.price : pos.mark;
      const grossPL = pos.side === 'BUY' ? (closePrice - pos.entry) * pos.lots : (pos.entry - closePrice) * pos.lots;
      const closeFees = calculateFees(closePrice, pos.lots);
      const netPL = grossPL - pos.openFees - closeFees;
      setBalance(prev => prev + grossPL - closeFees);
      setPositions(positions.filter(p => p.id !== id));
      setHistory([{
        id: `h-${Date.now()}`, time: new Date().toLocaleTimeString('en-GB'), type: 'CLOSE',
        symbol: pos.contract, side: pos.side === 'BUY' ? 'SELL' : 'BUY',
        price: closePrice, lots: pos.lots, pl: netPL
      }, ...history]);
    }
  };

  const cancelOrder = (id) => setActiveOrders(activeOrders.filter(o => o.id !== id));
  const getPLColor = (val) => { if (val > 0) return 'text-emerald-400'; if (val < 0) return 'text-rose-500'; return 'text-slate-400'; };

  return (
    <div className="flex flex-col h-screen w-full bg-[#0b1221] text-slate-200 font-sans overflow-hidden select-none">
      <ScrollbarStyles />
      
      {/* HEADER */}
      <header className="flex items-center justify-between px-4 py-2 bg-[#0f172a] border-b border-slate-800 h-14 shrink-0">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2">
            <div className="bg-blue-600 p-1.5 rounded-lg shadow-lg shadow-blue-500/20">
              <Anchor size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-black tracking-tight leading-none text-white">FFA<span className="text-blue-500">ARENA</span></h1>
              <p className="text-[10px] text-slate-400 font-medium tracking-wider">PRO COMPETITION</p>
            </div>
          </div>
          <div className="flex items-center space-x-2 bg-slate-800/50 px-3 py-1.5 rounded-full border border-slate-700/50">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <span className="text-xs text-emerald-400 font-medium">Data Feed: Connected</span>
          </div>
        </div>
        <div className="flex items-center space-x-8">
          <div className="text-right hidden md:block">
            <div className="text-[10px] text-slate-500 font-bold tracking-wider">UTC TIME</div>
            <div className="text-sm font-mono text-slate-200">{currentTime.toISOString().split('T')[1].split('.')[0]}</div>
          </div>
          <div className="flex items-center space-x-3 pl-6 border-l border-slate-700">
            <div className="text-right">
              <div className="text-xs font-bold text-white">Guest Trader</div>
              <div className="text-xs font-mono text-emerald-400">{formatUSD(totalEquity)}</div>
            </div>
            <div className="bg-slate-700 p-2 rounded-full">
              <User size={16} />
            </div>
          </div>
        </div>
      </header>

      {/* MAIN CONTENT */}
      <div className="flex flex-1 overflow-hidden">
        
        {/* LEFT/CENTER */}
        <div className="flex flex-col flex-1 min-w-0">
          
          {/* MARKET WATCH */}
          <div className="flex-none p-1 space-y-1 bg-[#0b1221]">
            {watchList.map((row) => {
              const isActive = row.id === activeRowId;
              const isPositive = row.change >= 0;
              return (
                <div key={row.id} onClick={() => setActiveRowId(row.id)} className={`flex items-center px-4 py-2 rounded border transition-all cursor-pointer group ${isActive ? 'bg-[#1e293b] border-blue-500/50 shadow-md shadow-blue-900/10' : 'bg-[#131b2e] border-slate-800/50 hover:border-slate-700'}`}>
                  <div className="w-24 flex items-center mr-2">
                    <div className="relative w-full group/select">
                       <select value={row.symbol} onChange={(e) => { const updates = { symbol: e.target.value, price: roundToTick(BASE_PRICES[e.target.value], e.target.value), change: 0, changePct: 0 }; setWatchList(prev => prev.map(r => r.id === row.id ? { ...r, ...updates } : r)); }} className={`w-full appearance-none bg-transparent font-bold text-sm focus:outline-none cursor-pointer ${isActive ? 'text-white' : 'text-slate-300 group-hover:text-white'}`} onClick={(e) => e.stopPropagation()} >
                         {AVAILABLE_SYMBOLS.map(s => <option key={s} value={s} className="bg-[#1e293b] text-white">{s}</option>)}
                       </select>
                       <ChevronDown size={12} className="absolute right-0 top-1.5 text-slate-500 pointer-events-none" />
                    </div>
                  </div>
                  <div className="w-28 flex items-center mr-2">
                     <div className="relative w-full">
                       <select value={row.month} onChange={(e) => setWatchList(prev => prev.map(r => r.id === row.id ? { ...r, month: e.target.value } : r))} className="w-full appearance-none bg-transparent text-sm text-slate-400 focus:outline-none cursor-pointer hover:text-slate-200" onClick={(e) => e.stopPropagation()} >
                         {AVAILABLE_MONTHS.map(m => <option key={m} value={m} className="bg-[#1e293b] text-white">{m}</option>)}
                       </select>
                       <ChevronDown size={12} className="absolute right-0 top-1.5 text-slate-500 pointer-events-none" />
                     </div>
                  </div>
                  <div className={`w-24 font-mono text-sm ${isActive ? 'text-white' : 'text-slate-400'}`}>{formatNumber(row.price, row.symbol)}</div>
                  <div className={`w-24 font-mono text-xs px-1.5 py-0.5 rounded flex items-center justify-center ${isPositive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>{isPositive ? '+' : ''}{row.changePct.toFixed(2)}%</div>
                  <div className="flex-1"></div>
                  <div className={`flex space-x-1 transition-opacity ${isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
                    <button onClick={(e) => { e.stopPropagation(); if(activeRowId===row.id) setIsChartVisible(!isChartVisible); else { setActiveRowId(row.id); setIsChartVisible(true); }}} className="p-1 hover:bg-slate-700 rounded text-slate-400"><CandlestickIcon size={14} /></button>
                    <button onClick={(e) => { e.stopPropagation(); setWatchList(watchList.filter(i=>i.id!==row.id)); }} className="p-1 hover:bg-rose-500/20 hover:text-rose-400 rounded text-slate-400"><Minus size={14} /></button>
                  </div>
                </div>
              );
            })}
            <button onClick={() => { const newId = `row-${Date.now()}`; setWatchList([...watchList, { id: newId, symbol: 'C5TC', month: 'Mar 26', price: roundToTick(BASE_PRICES['C5TC'], 'C5TC'), change: 0, changePct: 0 }]); setActiveRowId(newId); setIsChartVisible(true); }} className="w-full py-1.5 mt-1 border border-dashed border-slate-700 rounded text-slate-500 text-xs font-bold hover:bg-slate-800 hover:text-slate-300 transition-colors flex items-center justify-center">
                <Plus size={12} className="mr-1" /> Add Contract
            </button>
          </div>

          {/* CHART */}
          {isChartVisible && watchList.length > 0 && (
              <div className="flex-1 bg-[#0f1623] relative border-y border-slate-800 flex flex-col min-h-[300px]">
                <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800/50 bg-[#131b2e] h-14">
                    <div className="flex items-center space-x-4">
                        <div className="flex items-center space-x-2">
                            <span className="text-slate-400 text-xs font-medium">CHART:</span>
                            <div className="px-3 py-1 bg-blue-600 text-white font-bold rounded text-xs shadow-lg shadow-blue-500/20">{orderSymbol} - {orderMonth}</div>
                        </div>
                        <div className="flex items-baseline space-x-3 border-l border-slate-700 pl-4 ml-2">
                            <span className="text-xl font-mono font-bold text-white tracking-tight">{formatNumber(currentMarketPrice, orderSymbol)}</span>
                            <span className={`text-xs font-mono font-bold flex items-center ${activeRow.change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {activeRow.change >= 0 ? <TrendingUp size={12} className="mr-1" /> : <TrendingDown size={12} className="mr-1" />}
                                {activeRow.change > 0 ? '+' : ''}{activeRow.change.toFixed(2)} ({activeRow.changePct > 0 ? '+' : ''}{activeRow.changePct.toFixed(2)}%)
                            </span>
                        </div>
                    </div>
                    <div className="flex items-center space-x-4">
                        <div className="flex space-x-0.5 bg-slate-800 rounded p-0.5">
                            {Object.keys(TIMEFRAME_CONFIG).map(tf => (
                              <button key={tf} onClick={() => setSelectedTimeframe(tf)} className={`text-[10px] px-2 py-1 rounded transition-colors ${selectedTimeframe === tf ? 'bg-slate-600 text-white font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'}`}>{tf}</button>
                            ))}
                        </div>
                        <button onClick={() => setIsChartVisible(false)} className="p-1.5 hover:bg-slate-700 rounded text-slate-400"><X size={16} /></button>
                    </div>
                </div>
                <div className="flex-1 w-full relative group p-2">
                    <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={candleData}>
                        <XAxis dataKey="time" hide domain={['dataMin', 'dataMax']} />
                        <YAxis domain={['auto', 'auto']} hide />
                        <Tooltip content={<CustomOHLCTooltip />} cursor={{ stroke: '#334155', strokeWidth: 1, strokeDasharray: '4 4' }} />
                        <Bar dataKey="body" shape={<CandlestickShape />} isAnimationActive={false} />
                    </ComposedChart>
                    </ResponsiveContainer>
                </div>
              </div>
          )}

          {/* BOTTOM PANEL */}
          <div className={`${isChartVisible ? 'h-[320px]' : 'flex-1'} flex border-t border-slate-800 bg-[#131b2e] transition-all duration-300`}>
            
            {/* ORDER ENTRY */}
            <div className="w-[280px] flex-none border-r border-slate-800 flex flex-col bg-[#0f1623]">
              <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
                <div className="mb-4">
                   <div className="text-[10px] font-bold text-slate-500 uppercase mb-1">Instrument</div>
                   <div className="flex space-x-1">
                      <div className="relative flex-1">
                        <select value={orderSymbol} onChange={(e) => setOrderSymbol(e.target.value)} className="w-full bg-[#1e293b] border border-slate-600 text-white text-xs font-bold py-1.5 px-2 rounded appearance-none focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition-all custom-scrollbar">
                            {AVAILABLE_SYMBOLS.map(s => <option key={s} value={s}>{s}</option>)}
                        </select>
                        <ChevronDown size={12} className="absolute right-2 top-2 text-slate-400 pointer-events-none" />
                      </div>
                      <div className="relative flex-1">
                        <select value={orderMonth} onChange={(e) => setOrderMonth(e.target.value)} className="w-full bg-[#1e293b] border border-slate-600 text-slate-300 text-xs py-1.5 px-2 rounded appearance-none focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition-all custom-scrollbar">
                            {AVAILABLE_MONTHS.map(m => <option key={m} value={m}>{m}</option>)}
                        </select>
                        <ChevronDown size={12} className="absolute right-2 top-2 text-slate-400 pointer-events-none" />
                      </div>
                   </div>
                </div>

                <div className="mb-4">
                  <label className="text-[10px] font-bold text-slate-500 uppercase mb-1 block">Order Type</label>
                  <div className="relative">
                    <select value={orderType} onChange={(e) => setOrderType(e.target.value)} className="w-full bg-[#1e293b] border border-slate-600 text-white text-sm py-2 px-3 rounded appearance-none cursor-pointer hover:border-slate-500 focus:border-blue-500 transition-all custom-scrollbar">
                        <option value="MARKET">Market Execution</option>
                        <option value="LIMIT">Limit Order</option>
                    </select>
                    <ChevronDown size={14} className="absolute right-3 top-2.5 text-slate-400 pointer-events-none" />
                  </div>
                  {orderType === 'LIMIT' && (
                    <div className="mt-2 animate-in fade-in slide-in-from-top-1 duration-200">
                        <label className="text-[9px] font-bold text-slate-500 uppercase mb-0.5 block">Limit Price (Tick: {getTickSize(orderSymbol)})</label>
                        <input type="number" step={getTickSize(orderSymbol)} value={limitPrice} onChange={(e) => setLimitPrice(parseFloat(e.target.value) || 0)} onBlur={() => setLimitPrice(roundToTick(limitPrice, orderSymbol))} className="w-full bg-[#0b1221] border border-slate-600 text-white text-sm py-1.5 px-3 rounded focus:outline-none focus:border-blue-500 font-mono transition-all" />
                    </div>
                  )}
                </div>

                <div className="mb-4">
                  <div className="flex justify-between items-end mb-1">
                    <label className="text-[10px] font-bold text-slate-500 uppercase">Lots (Min: 5)</label>
                    <span className="text-[10px] text-slate-400">{lots} LOTS</span>
                  </div>
                  <div className="relative">
                    <input type="number" value={lots} onChange={(e) => setLots(Math.max(5, parseInt(e.target.value) || 0))} min="5" step="5" className="w-full bg-[#1e293b] border border-slate-600 text-white text-xl font-mono py-2 pl-3 pr-10 rounded focus:outline-none focus:border-blue-500 transition-all" />
                    <div className="absolute right-0 top-0 h-full flex flex-col border-l border-slate-600">
                      <button onClick={() => setLots(l => l + 5)} className="flex-1 px-2 hover:bg-slate-700 text-slate-400 transition-colors"><ChevronDown size={12} className="rotate-180" /></button>
                      <button onClick={() => setLots(l => Math.max(5, l - 5))} className="flex-1 px-2 hover:bg-slate-700 text-slate-400 transition-colors"><ChevronDown size={12} /></button>
                    </div>
                  </div>
                </div>

                <div className="flex justify-between items-center text-xs mb-1">
                  <span className="text-slate-500">Margin ({Math.round(marginRatio * 100)}%):</span>
                  <span className="font-mono text-slate-300">~ {formatUSD(marginRequired)}</span>
                </div>

                <div className="mt-4 pt-4 border-t border-slate-800/50">
                   <div onClick={() => setIsFeesOpen(!isFeesOpen)} className="flex justify-between items-center text-[10px] font-bold text-slate-500 cursor-pointer hover:text-slate-300 mb-2 select-none">
                     <span>Fees & Breakdown</span>
                     {isFeesOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                   </div>
                   {isFeesOpen && (
                      <div className="space-y-1 animate-in fade-in slide-in-from-top-1 duration-200">
                        <div className="flex justify-between text-[10px]"><span className="text-slate-600">Clearing ($20/lot)</span><span className="font-mono text-slate-400">{formatUSD(clearingFee)}</span></div>
                        <div className="flex justify-between text-[10px]"><span className="text-slate-600">Brokerage (0.1%)</span><span className="font-mono text-slate-400">{formatUSD(commFee)}</span></div>
                        <div className="flex justify-between text-[10px] pt-1 border-t border-slate-800/30"><span className="text-rose-400 font-bold">Total Est.</span><span className="font-mono text-rose-400 font-bold">{formatUSD(totalEstFees)}</span></div>
                      </div>
                   )}
                </div>
              </div>
              <div className="p-4 pt-2 border-t border-slate-800 bg-[#0f1623] z-10 sticky bottom-0">
                <div className="grid grid-cols-2 gap-2">
                    <button onClick={() => handleOrder('BUY')} className="bg-emerald-600 hover:bg-emerald-500 text-white py-3 rounded font-bold shadow-lg shadow-emerald-900/20 active:translate-y-0.5 transition-all text-sm border-t border-emerald-400/20">BUY</button>
                    <button onClick={() => handleOrder('SELL')} className="bg-rose-600 hover:bg-rose-500 text-white py-3 rounded font-bold shadow-lg shadow-rose-900/20 active:translate-y-0.5 transition-all text-sm border-t border-rose-400/20">SELL</button>
                </div>
              </div>
            </div>

            {/* TABS CONTENT */}
            <div className="flex-1 flex flex-col bg-[#0b1221]">
              <div className="flex border-b border-slate-800">
                {['positions', 'orders', 'tape', 'history'].map(tab => (
                  <button 
                    key={tab}
                    onClick={() => setActiveTab(tab)} 
                    className={`px-4 py-2 text-sm font-bold transition-colors flex items-center ${activeTab === tab ? 'text-blue-400 border-b-2 border-blue-500 bg-blue-500/5' : 'text-slate-500 hover:text-slate-300'}`}
                  >
                    {tab === 'positions' && <>Positions <span className="ml-1 px-1.5 py-0.5 bg-blue-500 text-white text-[10px] rounded-full">{positions.length}</span></>}
                    {tab === 'orders' && <>Active Orders <span className={`ml-1 px-1.5 py-0.5 text-[10px] rounded-full ${activeOrders.length > 0 ? 'bg-orange-500 text-white' : 'bg-slate-700 text-slate-300'}`}>{activeOrders.length}</span></>}
                    {tab === 'tape' && <>Market Tape <span className="ml-2 text-[10px] bg-emerald-500 text-[#0b1221] px-1 rounded font-black">LIVE</span></>}
                    {tab === 'history' && <>Trade History</>}
                  </button>
                ))}
              </div>

              <div className="flex-1 overflow-auto custom-scrollbar">
                
                {/* POSITIONS TABLE */}
                {activeTab === 'positions' && (
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#131b2e] sticky top-0 z-10 text-[10px] text-slate-500 font-bold uppercase tracking-wider shadow-sm">
                      <tr>
                        <th className="px-4 py-2">Contract</th>
                        <th className="px-4 py-2">Month</th>
                        <th className="px-4 py-2">Side</th>
                        <th className="px-4 py-2 text-right">Lots</th>
                        <th className="px-4 py-2 text-right">Entry</th>
                        <th className="px-4 py-2 text-right">Mark</th>
                        <th className="px-4 py-2 text-right text-orange-400">Margin</th>
                        <th className="px-4 py-2 text-right">Net P&L</th>
                        <th className="px-4 py-2 text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {positions.length === 0 ? (
                        <tr><td colSpan="9" className="text-center py-8 text-slate-600 italic">No open positions</td></tr>
                      ) : positions.map((pos) => {
                        const watcher = watchList.find(w => w.symbol === pos.contract && w.month === pos.month);
                        const currentMark = watcher ? watcher.price : pos.mark;
                        
                        const grossPL = pos.side === 'BUY' ? (currentMark - pos.entry) * pos.lots : (pos.entry - currentMark) * pos.lots;
                        const estCloseFees = calculateFees(currentMark, pos.lots);
                        const netPL = grossPL - pos.openFees - estCloseFees;

                        return (
                          <tr key={pos.id} className="hover:bg-slate-800/30 transition-colors group">
                            <td className="px-4 py-2.5 font-bold text-white">{pos.contract}</td>
                            <td className="px-4 py-2.5 text-slate-400">{pos.month}</td>
                            <td className="px-4 py-2.5">{pos.side === 'BUY' ? <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400">BUY</span> : <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-500">SELL</span>}</td>
                            <td className="px-4 py-2.5 text-right font-mono text-slate-300">{pos.lots}</td>
                            <td className="px-4 py-2.5 text-right font-mono text-slate-400">{formatNumber(pos.entry, pos.contract)}</td>
                            <td className="px-4 py-2.5 text-right font-mono text-white animate-pulse-short">{formatNumber(currentMark, pos.contract)}</td>
                            <td className="px-4 py-2.5 text-right font-mono text-orange-400">${Math.round(pos.margin)}</td>
                            <td className={`px-4 py-2.5 text-right font-mono font-bold ${getPLColor(netPL)}`}>{netPL > 0 ? '+' : ''}{formatNumber(netPL)}</td>
                            <td className="px-4 py-2.5 text-center"><button onClick={() => closePosition(pos.id)} className="px-2 py-1 text-[10px] border border-slate-600 text-slate-400 rounded hover:bg-slate-700 hover:text-white hover:border-slate-500 transition-all">Close</button></td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}

                {/* ACTIVE ORDERS */}
                {activeTab === 'orders' && (
                   <table className="w-full text-left text-xs">
                    <thead className="bg-[#131b2e] sticky top-0 z-10 text-[10px] text-slate-500 font-bold uppercase tracking-wider shadow-sm">
                      <tr>
                        <th className="px-4 py-2">Time</th>
                        <th className="px-4 py-2">Contract</th>
                        <th className="px-4 py-2">Month</th>
                        <th className="px-4 py-2">Side</th>
                        <th className="px-4 py-2 text-right">Lots</th>
                        <th className="px-4 py-2 text-right">Limit Price</th>
                        <th className="px-4 py-2 text-right">Current</th>
                        <th className="px-4 py-2 text-right">Status</th>
                        <th className="px-4 py-2 text-center">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {activeOrders.length === 0 ? (
                        <tr><td colSpan="9" className="text-center py-8 text-slate-600 italic">No active orders</td></tr>
                      ) : activeOrders.map((order) => {
                        const watcher = watchList.find(w => w.symbol === order.contract && w.month === order.month);
                        const currentPrice = watcher ? watcher.price : order.entry;
                        const distance = Math.abs(currentPrice - order.entry);
                        return (
                          <tr key={order.id} className="hover:bg-slate-800/30 transition-colors">
                            <td className="px-4 py-2.5 text-slate-500 font-mono">{order.time}</td>
                            <td className="px-4 py-2.5 font-bold text-white">{order.contract}</td>
                            <td className="px-4 py-2.5 text-slate-400">{order.month}</td>
                            <td className="px-4 py-2.5">{order.side === 'BUY' ? <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400">BUY</span> : <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-500/20 text-rose-500">SELL</span>}</td>
                            <td className="px-4 py-2.5 text-right font-mono text-slate-300">{order.lots}</td>
                            <td className="px-4 py-2.5 text-right font-mono text-blue-400 font-bold">{formatNumber(order.entry, order.contract)}</td>
                            <td className="px-4 py-2.5 text-right font-mono text-slate-400">{formatNumber(currentPrice, order.contract)}</td>
                            <td className="px-4 py-2.5 text-right text-[10px] text-orange-400 font-bold animate-pulse">PENDING ({distance.toFixed(order.contract === 'C5' ? 2 : 0)} away)</td>
                            <td className="px-4 py-2.5 text-center"><button onClick={() => cancelOrder(order.id)} className="p-1.5 text-rose-400 hover:bg-rose-500/20 rounded transition-colors"><Trash2 size={12} /></button></td>
                          </tr>
                        );
                      })}
                    </tbody>
                   </table>
                )}

                {/* TAPE */}
                {activeTab === 'tape' && (
                  <table className="w-full text-left text-xs">
                   <thead className="bg-[#131b2e] sticky top-0 z-10 text-[10px] text-slate-500 font-bold uppercase tracking-wider shadow-sm">
                     <tr>
                       <th className="px-4 py-2">Time</th>
                       <th className="px-4 py-2">Contract</th>
                       <th className="px-4 py-2">Month</th>
                       <th className="px-4 py-2 text-right">Price</th>
                       <th className="px-4 py-2 text-right">Lots</th>
                       <th className="px-4 py-2 text-center">EX</th>
                     </tr>
                   </thead>
                   <tbody className="divide-y divide-slate-800/50">
                     {marketTape.map((trade) => (
                       <tr key={trade.id} className="hover:bg-slate-800/30">
                         <td className="px-4 py-1.5 text-slate-500 font-mono">{trade.time}</td>
                         <td className="px-4 py-1.5 font-bold text-slate-300">{trade.contract}</td>
                         <td className="px-4 py-1.5 text-slate-400">{trade.month}</td>
                         <td className={`px-4 py-1.5 text-right font-mono font-bold ${trade.side === 'BUY' ? 'text-emerald-500' : 'text-rose-500'}`}>{formatNumber(trade.price, trade.contract)}</td>
                         <td className="px-4 py-1.5 text-right font-mono text-slate-300">{trade.lots}</td>
                         <td className="px-4 py-1.5 text-center">
                           <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-300`}>
                             {trade.exchange}
                           </span>
                         </td>
                       </tr>
                     ))}
                   </tbody>
                  </table>
                )}

                {/* HISTORY */}
                {activeTab === 'history' && (
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#131b2e] sticky top-0 z-10 text-[10px] text-slate-500 font-bold uppercase tracking-wider shadow-sm">
                      <tr>
                        <th className="px-4 py-2">Time</th>
                        <th className="px-4 py-2">Contract</th>
                        <th className="px-4 py-2">Type</th>
                        <th className="px-4 py-2">Side</th>
                        <th className="px-4 py-2 text-right">Price</th>
                        <th className="px-4 py-2 text-right">Lots</th>
                        <th className="px-4 py-2 text-right">Realized Net P&L</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {history.length === 0 ? (
                        <tr><td colSpan="7" className="text-center py-8 text-slate-600 italic">No history yet</td></tr>
                      ) : history.map((h) => (
                        <tr key={h.id} className="hover:bg-slate-800/30 transition-colors">
                          <td className="px-4 py-2.5 text-slate-500 font-mono">{h.time}</td>
                          <td className="px-4 py-2.5 font-bold text-white">{h.symbol}</td>
                          <td className="px-4 py-2.5 text-slate-400 text-[10px] uppercase font-bold">{h.type}</td>
                          <td className="px-4 py-2.5">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${h.side === 'BUY' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'}`}>
                              {h.side}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-right font-mono text-white">{formatNumber(h.price, h.symbol)}</td>
                          <td className="px-4 py-2.5 text-right font-mono text-slate-300">{h.lots}</td>
                          <td className={`px-4 py-2.5 text-right font-mono font-bold`}>
                            {h.pl !== null ? <span className={getPLColor(h.pl)}>{h.pl > 0 ? '+' : ''}{formatNumber(h.pl)}</span> : <span className="text-slate-600">-</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}

              </div>
            </div>

          </div>
        </div>

        {/* RIGHT SIDEBAR */}
        <div className="w-[300px] flex-none bg-[#101828] border-l border-slate-800 flex flex-col custom-scrollbar">
          
          {/* COUNTDOWN */}
          <div className="border-b border-slate-800">
            <div onClick={() => setIsCountdownOpen(!isCountdownOpen)} className="flex justify-between items-center p-4 cursor-pointer hover:bg-slate-800/30 transition-colors bg-gradient-to-b from-[#172554] to-[#101828]">
               <div className="flex items-center text-blue-400 font-bold text-sm"><Trophy size={14} className="mr-2" />S1 SEASON COUNTDOWN</div>
               {isCountdownOpen ? <ChevronDown size={14} className="text-blue-400" /> : <ChevronRight size={14} className="text-blue-400" />}
            </div>
            {isCountdownOpen && (
              <div className="pb-4 px-4 animate-in fade-in slide-in-from-top-1 duration-200">
                <div className="flex justify-center space-x-2 mb-3">
                  {[{ val: '04', label: 'DAY' }, { val: '12', label: 'HR' }, { val: '58', label: 'MIN' }].map((item, idx) => (
                    <div key={idx} className="bg-[#0b1221] border border-slate-700 p-2 rounded w-16 text-center shadow-lg">
                      <div className="text-xl font-mono font-bold text-white">{item.val}</div>
                      <div className="text-[9px] text-slate-500 font-bold mt-1">{item.label}</div>
                    </div>
                  ))}
                </div>
                <div className="bg-[#1e293b] rounded-lg p-2 flex justify-between items-center border border-slate-700/50">
                   <div className="text-[10px] text-slate-400 font-bold uppercase flex items-center"><DollarSign size={12} className="mr-1 text-yellow-500" /> Total Prize Pool</div>
                   <div className="text-sm font-mono font-bold text-yellow-400">{formatUSD(PRIZE_POOL)}</div>
                </div>
              </div>
            )}
          </div>

          {/* PERFORMANCE */}
          <div className="border-b border-slate-800">
            <div onClick={() => setIsPerformanceOpen(!isPerformanceOpen)} className="flex justify-between items-center p-4 cursor-pointer hover:bg-slate-800/30 transition-colors">
               <div className="flex items-center text-xs font-bold text-slate-400 uppercase"><Activity size={14} className="mr-2" />My Performance</div>
               {isPerformanceOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </div>
            {isPerformanceOpen && (
              <div className="px-4 pb-4 animate-in fade-in slide-in-from-top-1 duration-200">
                <div className="grid grid-cols-2 gap-2 mb-3">
                  <div className="bg-[#0b1221] p-3 rounded border border-slate-800">
                    <div className="text-[10px] text-slate-500 font-bold mb-1">TOTAL EQUITY</div>
                    <div className="text-lg font-mono font-bold text-white tracking-tight">{formatUSD(totalEquity).split('.')[0]}</div>
                  </div>
                  <div className="bg-[#0b1221] p-3 rounded border border-slate-800">
                    <div className="text-[10px] text-slate-500 font-bold mb-1">ROI (NET)</div>
                    <div className={`text-lg font-mono font-bold ${getPLColor(roi)}`}>{roi > 0 ? '+' : ''}{roi.toFixed(2)}%</div>
                  </div>
                </div>
                <div className="flex justify-between items-center bg-[#1e293b] p-2 rounded mb-1">
                  <span className="text-xs text-slate-400">Current Rank</span>
                  <span className="text-sm font-mono font-bold text-white">#{rankingData.myRank}</span>
                </div>
                <div className="flex justify-between items-center bg-[#1e293b] p-2 rounded mb-1">
                  <span className="text-xs text-slate-400">Open Net P&L</span>
                  <span className={`text-sm font-mono font-bold ${getPLColor(totalLiquidationPL)}`}>{totalLiquidationPL > 0 ? '+' : ''}{formatUSD(totalLiquidationPL)}</span>
                </div>
              </div>
            )}
          </div>

          {/* TOP PERFORMERS */}
          <div className="flex flex-col flex-1 min-h-0">
             <div onClick={() => setIsTopPerformersOpen(!isTopPerformersOpen)} className="flex justify-between items-center p-4 cursor-pointer hover:bg-slate-800/30 transition-colors border-b border-slate-800/50">
               <div className="flex items-center text-xs font-bold text-slate-400 uppercase"><Medal size={14} className="mr-2" />Top Performers</div>
               {isTopPerformersOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </div>
            {isTopPerformersOpen && (
              <div className="flex-1 overflow-y-auto custom-scrollbar p-0 animate-in fade-in slide-in-from-top-1 duration-200 flex flex-col">
                  <div className="space-y-1 p-2">
                    {rankingData.top10.map((u, i) => (
                      <div key={i} className={`flex justify-between items-center p-2 rounded border transition-colors ${u.isMe ? 'bg-blue-900/40 border-blue-500/50 shadow-md' : 'bg-[#0b1221] border-slate-800/50 hover:bg-slate-800/30'}`}>
                        <div className="flex items-center space-x-3">
                          <span className={`text-xs font-black w-5 h-5 flex items-center justify-center rounded ${i === 0 ? 'bg-yellow-500 text-black' : i === 1 ? 'bg-slate-400 text-black' : i === 2 ? 'bg-orange-700 text-white' : 'bg-slate-800 text-slate-500'}`}>{i+1}</span>
                          <div>
                            <div className={`text-xs font-bold ${u.isMe ? 'text-white' : 'text-slate-300'}`}>{u.name} {u.isMe && '(You)'}</div>
                            {u.team && <div className="text-[9px] text-slate-500">{u.team}</div>}
                          </div>
                        </div>
                        <span className={`text-xs font-mono font-bold ${getPLColor(u.roi)}`}>{u.roi > 0 ? '+' : ''}{u.roi.toFixed(2)}%</span>
                      </div>
                    ))}
                  </div>
                  
                  {/* Sticky Me Row if not in top 10 */}
                  {rankingData.myRank > 10 && (
                    <div className="sticky bottom-0 mt-auto border-t border-slate-700 bg-[#0f1623] p-2 shadow-lg">
                       <div className="flex justify-between items-center p-2 rounded border border-blue-500/50 bg-blue-900/20">
                        <div className="flex items-center space-x-3">
                          <span className="text-xs font-black w-5 h-5 flex items-center justify-center rounded bg-slate-700 text-white">{rankingData.myRank}</span>
                          <div>
                            <div className="text-xs font-bold text-white">Guest Trader (You)</div>
                            <div className="text-[9px] text-slate-400">Independent</div>
                          </div>
                        </div>
                        <span className={`text-xs font-mono font-bold ${getPLColor(roi)}`}>{roi > 0 ? '+' : ''}{roi.toFixed(2)}%</span>
                      </div>
                    </div>
                  )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}