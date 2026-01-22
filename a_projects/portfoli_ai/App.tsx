import React, { useEffect, useState, useMemo } from 'react';
import { marketDataService } from './services/marketDataService';
import { INITIAL_HOLDINGS } from './constants';
import { Holding, Quote } from './types';
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  PieChart as PieChartIcon, 
  Plus, 
  Pencil, 
  Activity,
  Wallet,
  Building2,
  Globe2
} from 'lucide-react';
import PortfolioChart from './components/PortfolioChart';
import StrategyCard from './components/StrategyCard';
import AddHoldingModal from './components/AddHoldingModal';
import EditHoldingModal from './components/EditHoldingModal';

const App: React.FC = () => {
  const [holdings, setHoldings] = useState<Holding[]>(() => {
    const saved = localStorage.getItem('portfolio_holdings');
    return saved ? JSON.parse(saved) : INITIAL_HOLDINGS;
  });
  
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  
  // Modal States
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingHolding, setEditingHolding] = useState<Holding | null>(null);

  const [selectedAccount, setSelectedAccount] = useState<string>('All');

  // One-time cleanup effect to remove legacy demo data for IBKR and uSmart
  useEffect(() => {
    setHoldings(prev => prev.filter(h => {
      const isDemoIBKR = h.account === 'IBKR' && h.symbol === 'NVDA' && h.avgCost === 450;
      const isDemouSmart = h.account === 'uSmart' && h.symbol === 'BABA' && h.avgCost === 85;
      return !isDemoIBKR && !isDemouSmart;
    }));
  }, []);

  // Subscribe to market data
  useEffect(() => {
    // Register symbols
    holdings.forEach(h => marketDataService.addSymbol(h.symbol));

    const unsubscribe = marketDataService.subscribe((newQuotes) => {
      setQuotes(prev => ({ ...prev, ...newQuotes }));
    });
    return () => unsubscribe();
  }, [holdings]);

  // Persist holdings
  useEffect(() => {
    localStorage.setItem('portfolio_holdings', JSON.stringify(holdings));
  }, [holdings]);

  // Filter Holdings based on selection
  const filteredHoldings = useMemo(() => {
    if (selectedAccount === 'All') return holdings;
    return holdings.filter(h => h.account === selectedAccount);
  }, [holdings, selectedAccount]);

  // Calculate Totals
  const summary = useMemo(() => {
    let totalValue = 0;
    let totalCost = 0;
    let dailyPnL = 0;

    filteredHoldings.forEach(h => {
      const q = quotes[h.symbol];
      const currentPrice = q ? q.price : h.avgCost;
      const prevClose = q ? q.price - q.change : h.avgCost;

      totalValue += h.shares * currentPrice;
      totalCost += h.shares * h.avgCost;
      dailyPnL += h.shares * (currentPrice - prevClose);
    });

    const totalPnL = totalValue - totalCost;
    const totalPnLPercent = totalCost > 0 ? (totalPnL / totalCost) * 100 : 0;

    return { totalValue, totalCost, totalPnL, totalPnLPercent, dailyPnL };
  }, [filteredHoldings, quotes]);

  const addHolding = (holding: Holding) => {
    setHoldings(prev => [...prev, holding]);
    marketDataService.addSymbol(holding.symbol);
  };

  const openEditModal = (holding: Holding) => {
    setEditingHolding(holding);
    setIsEditModalOpen(true);
  };

  const updateHolding = (updatedHolding: Holding) => {
    setHoldings(prev => prev.map(h => 
      (h.symbol === updatedHolding.symbol && h.account === updatedHolding.account) 
        ? updatedHolding 
        : h
    ));
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(val);
  };

  const formatPercent = (val: number) => {
    return `${val > 0 ? '+' : ''}${val.toFixed(2)}%`;
  };

  const getAccountBadgeColor = (account: string) => {
    switch(account) {
      case 'FirstTrade': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'IBKR': return 'bg-orange-500/20 text-orange-400 border-orange-500/30';
      case 'uSmart': return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
      default: return 'bg-slate-700 text-slate-400 border-slate-600';
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-emerald-500/30">
      
      {/* Header - 移动端紧凑 */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 h-14 sm:h-16 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="bg-emerald-500 p-1.5 sm:p-2 rounded-lg shrink-0">
              <Activity className="w-4 h-4 sm:w-5 sm:h-5 text-slate-950" />
            </div>
            <h1 className="text-base sm:text-xl font-bold tracking-tight truncate">
              <span className="sm:hidden">Portfoli.AI</span>
              <span className="hidden sm:inline">Portfoli.AI 投资助手</span>
            </h1>
          </div>
          <button 
            onClick={() => setIsAddModalOpen(true)}
            className="bg-emerald-600 hover:bg-emerald-700 active:scale-[0.98] text-white px-3 py-2 sm:px-4 rounded-lg text-sm font-medium flex items-center gap-2 transition-all shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">添加资产</span>
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-4 sm:py-6 lg:py-8 space-y-4 sm:space-y-6 lg:space-y-8">
        
        {/* Account Filter Tabs - 横向滚动 */}
        <div className="flex gap-2 overflow-x-auto pb-2 -mx-3 px-3 sm:mx-0 sm:px-0 scrollbar-hide">
          <button 
            onClick={() => setSelectedAccount('All')}
            className={`px-3 sm:px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 sm:gap-2 whitespace-nowrap transition-colors border shrink-0 ${selectedAccount === 'All' ? 'bg-slate-800 border-emerald-500 text-white' : 'bg-slate-900/50 border-transparent text-slate-400 hover:text-white'}`}
          >
            <Wallet className="w-4 h-4 shrink-0" /> <span className="hidden sm:inline">全部账户 (All)</span><span className="sm:hidden">All</span>
          </button>
          <button 
            onClick={() => setSelectedAccount('FirstTrade')}
            className={`px-3 sm:px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 sm:gap-2 whitespace-nowrap transition-colors border shrink-0 ${selectedAccount === 'FirstTrade' ? 'bg-slate-800 border-blue-500 text-white' : 'bg-slate-900/50 border-transparent text-slate-400 hover:text-white'}`}
          >
            <Building2 className="w-4 h-4 shrink-0" /> FirstTrade
          </button>
          <button 
            onClick={() => setSelectedAccount('IBKR')}
            className={`px-3 sm:px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 sm:gap-2 whitespace-nowrap transition-colors border shrink-0 ${selectedAccount === 'IBKR' ? 'bg-slate-800 border-orange-500 text-white' : 'bg-slate-900/50 border-transparent text-slate-400 hover:text-white'}`}
          >
            <Globe2 className="w-4 h-4 shrink-0" /> IBKR
          </button>
          <button 
            onClick={() => setSelectedAccount('uSmart')}
            className={`px-3 sm:px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 sm:gap-2 whitespace-nowrap transition-colors border shrink-0 ${selectedAccount === 'uSmart' ? 'bg-slate-800 border-purple-500 text-white' : 'bg-slate-900/50 border-transparent text-slate-400 hover:text-white'}`}
          >
            <Activity className="w-4 h-4 shrink-0" /> uSmart
          </button>
        </div>

        {/* Dashboard Summary Cards - 响应式栅格 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6">
          <div className="bg-slate-800 p-4 sm:p-6 rounded-xl border border-slate-700 shadow-lg relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-3 sm:p-4 opacity-10 group-hover:opacity-20 transition-opacity">
              <DollarSign className="w-12 h-12 sm:w-16 sm:h-16 text-emerald-500" />
            </div>
            <p className="text-slate-400 text-sm font-medium mb-1">{selectedAccount === 'All' ? '总资产净值' : `${selectedAccount} 账户净值`}</p>
            <h2 className="text-2xl sm:text-3xl font-bold text-white break-all">{formatCurrency(summary.totalValue)}</h2>
          </div>
          <div className="bg-slate-800 p-4 sm:p-6 rounded-xl border border-slate-700 shadow-lg">
            <p className="text-slate-400 text-sm font-medium mb-1">累计收益</p>
            <div className="flex flex-wrap items-baseline gap-2 sm:gap-3">
              <h2 className={`text-2xl sm:text-3xl font-bold ${summary.totalPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {summary.totalPnL >= 0 ? '+' : ''}{formatCurrency(summary.totalPnL)}
              </h2>
              <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${summary.totalPnL >= 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}`}>
                {formatPercent(summary.totalPnLPercent)}
              </span>
            </div>
          </div>
          <div className="bg-slate-800 p-4 sm:p-6 rounded-xl border border-slate-700 shadow-lg sm:col-span-2 lg:col-span-1">
            <p className="text-slate-400 text-sm font-medium mb-1">今日盈亏</p>
            <div className="flex items-baseline gap-2">
              <h2 className={`text-2xl sm:text-3xl font-bold ${summary.dailyPnL >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {summary.dailyPnL >= 0 ? '+' : ''}{formatCurrency(summary.dailyPnL)}
              </h2>
              {summary.dailyPnL >= 0 ? <TrendingUp className="w-5 h-5 text-emerald-500 shrink-0" /> : <TrendingDown className="w-5 h-5 text-rose-500 shrink-0" />}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6 lg:gap-8">
          {/* Left: 持仓 - 桌面端表格 / 移动端卡片 */}
          <div className="lg:col-span-2 space-y-4 sm:space-y-6">
            <div className="bg-slate-800 rounded-xl border border-slate-700 shadow-lg overflow-hidden">
              <div className="p-4 sm:p-6 border-b border-slate-700 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
                <div className="flex items-center gap-3 flex-wrap">
                  <h2 className="text-base sm:text-lg font-bold text-white">持仓明细</h2>
                  {selectedAccount !== 'All' && (
                    <span className={`px-2 py-0.5 text-xs rounded border ${getAccountBadgeColor(selectedAccount)}`}>
                      仅显示 {selectedAccount}
                    </span>
                  )}
                </div>
                <span className="text-xs text-slate-500 uppercase tracking-wider">共 {filteredHoldings.length} 个标的</span>
              </div>

              {/* 桌面端：表格 */}
              <div className="hidden md:block overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="bg-slate-900/50 text-slate-400 text-xs uppercase font-semibold">
                    <tr>
                      <th className="px-4 lg:px-6 py-3">标的资产</th>
                      {selectedAccount === 'All' && <th className="px-4 lg:px-6 py-3">账户</th>}
                      <th className="px-4 lg:px-6 py-3 text-right">现价 / 涨跌</th>
                      <th className="px-4 lg:px-6 py-3 text-right">持仓市值</th>
                      <th className="px-4 lg:px-6 py-3 text-right">累计回报</th>
                      <th className="px-4 lg:px-6 py-3 text-center">管理</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700">
                    {filteredHoldings.map((h, idx) => {
                      const q = quotes[h.symbol];
                      const currentPrice = q ? q.price : h.avgCost;
                      const changePct = q ? q.changePercent : 0;
                      const marketValue = h.shares * currentPrice;
                      const totalReturn = marketValue - (h.shares * h.avgCost);
                      const returnPct = (totalReturn / (h.shares * h.avgCost)) * 100;
                      const key = `${h.symbol}-${h.account}-${idx}`;
                      return (
                        <tr key={key} className="hover:bg-slate-700/30 transition-colors">
                          <td className="px-4 lg:px-6 py-3">
                            <div className="flex flex-col">
                              <span className="font-bold text-white">{h.symbol}</span>
                              <span className="text-xs text-slate-400">{h.name}</span>
                            </div>
                          </td>
                          {selectedAccount === 'All' && (
                            <td className="px-4 lg:px-6 py-3">
                              <span className={`px-2 py-1 text-[10px] rounded border ${getAccountBadgeColor(h.account)}`}>{h.account}</span>
                            </td>
                          )}
                          <td className="px-4 lg:px-6 py-3 text-right">
                            <div className="font-medium text-slate-200">{formatCurrency(currentPrice)}</div>
                            <div className={`text-xs ${changePct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{formatPercent(changePct)}</div>
                          </td>
                          <td className="px-4 lg:px-6 py-3 text-right">
                            <div className="font-medium text-slate-200">{formatCurrency(marketValue)}</div>
                            <div className="text-xs text-slate-500">{h.shares.toFixed(4)} 股</div>
                          </td>
                          <td className="px-4 lg:px-6 py-3 text-right">
                            <div className={`font-medium ${totalReturn >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{totalReturn >= 0 ? '+' : ''}{formatCurrency(totalReturn)}</div>
                            <div className={`text-xs ${returnPct >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>{formatPercent(returnPct)}</div>
                          </td>
                          <td className="px-4 lg:px-6 py-3 text-center">
                            <button onClick={() => openEditModal(h)} className="text-slate-500 hover:text-blue-400 transition-colors p-2" title="编辑持仓">
                              <Pencil className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                    {filteredHoldings.length === 0 && (
                      <tr>
                        <td colSpan={selectedAccount === 'All' ? 6 : 5} className="px-4 lg:px-6 py-12 text-center text-slate-500">
                          {selectedAccount === 'All' ? '暂无持仓，请点击右上角添加资产。' : `${selectedAccount} 账户暂无持仓。`}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* 移动端：卡片列表 */}
              <div className="md:hidden divide-y divide-slate-700">
                {filteredHoldings.length === 0 ? (
                  <div className="px-4 py-12 text-center text-slate-500 text-sm">
                    {selectedAccount === 'All' ? '暂无持仓，请点击右上角添加资产。' : `${selectedAccount} 账户暂无持仓。`}
                  </div>
                ) : (
                  filteredHoldings.map((h, idx) => {
                    const q = quotes[h.symbol];
                    const currentPrice = q ? q.price : h.avgCost;
                    const changePct = q ? q.changePercent : 0;
                    const marketValue = h.shares * currentPrice;
                    const totalReturn = marketValue - (h.shares * h.avgCost);
                    const returnPct = (totalReturn / (h.shares * h.avgCost)) * 100;
                    const key = `${h.symbol}-${h.account}-${idx}`;
                    return (
                      <div key={key} className="p-4 active:bg-slate-700/30 transition-colors">
                        <div className="flex justify-between items-start gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2 mb-1">
                              <span className="font-bold text-white">{h.symbol}</span>
                              {selectedAccount === 'All' && (
                                <span className={`px-2 py-0.5 text-[10px] rounded border shrink-0 ${getAccountBadgeColor(h.account)}`}>{h.account}</span>
                              )}
                            </div>
                            <p className="text-xs text-slate-400 truncate">{h.name}</p>
                            <p className="text-xs text-slate-500 mt-0.5">{h.shares.toFixed(4)} 股</p>
                          </div>
                          <button
                            onClick={() => openEditModal(h)}
                            className="text-slate-500 hover:text-blue-400 active:text-blue-400 p-2 -m-2 shrink-0"
                            title="编辑持仓"
                          >
                            <Pencil className="w-4 h-4" />
                          </button>
                        </div>
                        <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-700/50">
                          <div>
                            <p className="text-[10px] text-slate-500 uppercase">现价</p>
                            <p className="font-medium text-slate-200 text-sm">{formatCurrency(currentPrice)}</p>
                            <p className={`text-xs ${changePct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{formatPercent(changePct)}</p>
                          </div>
                          <div>
                            <p className="text-[10px] text-slate-500 uppercase">市值</p>
                            <p className="font-medium text-slate-200 text-sm">{formatCurrency(marketValue)}</p>
                          </div>
                          <div>
                            <p className="text-[10px] text-slate-500 uppercase">累计回报</p>
                            <p className={`font-medium text-sm ${totalReturn >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>{totalReturn >= 0 ? '+' : ''}{formatCurrency(totalReturn)}</p>
                            <p className={`text-xs ${returnPct >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>{formatPercent(returnPct)}</p>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          {/* Right: 图表与 AI */}
          <div className="space-y-4 sm:space-y-6 lg:space-y-8">
            <PortfolioChart holdings={filteredHoldings} quotes={quotes} />
            <StrategyCard holdings={filteredHoldings} quotes={quotes} totalValue={summary.totalValue} />
          </div>
        </div>
      </main>

      <AddHoldingModal 
        isOpen={isAddModalOpen} 
        onClose={() => setIsAddModalOpen(false)} 
        onAdd={addHolding} 
      />

      <EditHoldingModal
        isOpen={isEditModalOpen}
        holding={editingHolding}
        onClose={() => setIsEditModalOpen(false)}
        onSave={updateHolding}
      />
    </div>
  );
};

export default App;