import React, { useState, useMemo } from 'react';
import { Sparkles, RefreshCcw, Shield, Swords, Zap, Target } from 'lucide-react';
import { analyzePortfolio } from '../services/geminiService';
import { Holding, Quote, AIAnalysisResponse, StrategyBucket } from '../types';
import { getStrategyBucket } from '../utils/strategyUtils';

interface StrategyCardProps {
  holdings: Holding[];
  quotes: Record<string, Quote>;
  totalValue: number;
}

const StrategyCard: React.FC<StrategyCardProps> = ({ holdings, quotes, totalValue }) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<AIAnalysisResponse | null>(null);
  const [expandedBucket, setExpandedBucket] = useState<string | null>(null);

  // Logic to categorize holdings into the 3 buckets
  const buckets = useMemo<StrategyBucket[]>(() => {
    const shield: Holding[] = [];
    const spear: Holding[] = [];
    const sword: Holding[] = [];

    holdings.forEach(h => {
      const type = getStrategyBucket(h.symbol, h.sector);
      if (type === 'Shield') shield.push(h);
      else if (type === 'Sword') sword.push(h);
      else spear.push(h);
    });

    const calcValue = (list: Holding[]) => list.reduce((sum, h) => {
      const price = quotes[h.symbol]?.price || h.avgCost;
      return sum + (h.shares * price);
    }, 0);

    return [
      { name: '盾 (防守底仓)', targetPercent: 50, currentValue: calcValue(shield), holdings: shield, color: 'bg-emerald-500' },
      { name: '矛 (稳健增长)', targetPercent: 30, currentValue: calcValue(spear), holdings: spear, color: 'bg-blue-500' },
      { name: '剑 (进攻博弈)', targetPercent: 20, currentValue: calcValue(sword), holdings: sword, color: 'bg-rose-500' },
    ];
  }, [holdings, quotes]);

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      const result = await analyzePortfolio(buckets, totalValue);
      setData(result);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (val: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val);

  return (
    <div className="bg-slate-800 rounded-xl p-4 sm:p-6 border border-slate-700 shadow-lg">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4 mb-4 sm:mb-6">
        <h2 className="text-base sm:text-xl font-bold flex items-center gap-2 text-white">
          <Target className="w-5 h-5 sm:w-6 sm:h-6 text-purple-400 shrink-0" />
          组合策略平衡
        </h2>
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="flex items-center justify-center gap-2 px-4 py-2.5 sm:py-2 bg-purple-600 hover:bg-purple-700 active:scale-[0.98] text-white rounded-lg transition-all text-sm font-medium disabled:opacity-50 w-full sm:w-auto"
        >
          {loading ? <RefreshCcw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {data ? '更新建议' : '获取 AI 建议'}
        </button>
      </div>

      {/* Visual Bars */}
      <div className="space-y-4 sm:space-y-6 mb-6 sm:mb-8">
        {buckets.map((bucket) => {
          const currentPercent = totalValue > 0 ? (bucket.currentValue / totalValue) * 100 : 0;
          const targetValue = totalValue * (bucket.targetPercent / 100);
          const valueDiff = bucket.currentValue - targetValue;
          const diffPercent = currentPercent - bucket.targetPercent;

          let Icon = Shield;
          if (bucket.name.includes('矛')) Icon = Zap;
          if (bucket.name.includes('剑')) Icon = Swords;

          const isExpanded = expandedBucket === bucket.name;

          return (
            <div key={bucket.name} className="relative bg-slate-900/30 rounded-lg p-3 sm:p-4 border border-slate-700/30">
              <div
                className="flex flex-wrap justify-between items-start gap-2 mb-3 cursor-pointer select-none"
                onClick={() => setExpandedBucket(isExpanded ? null : bucket.name)}
              >
                <div className="flex items-center gap-2 flex-wrap min-w-0">
                  <Icon className={`w-5 h-5 shrink-0 ${bucket.name.includes('盾') ? 'text-emerald-400' : bucket.name.includes('矛') ? 'text-blue-400' : 'text-rose-400'}`} />
                  <div className="flex flex-col">
                    <span className="font-bold text-slate-100 text-sm sm:text-base">{bucket.name}</span>
                    <span className="text-xs text-slate-500">目标: {bucket.targetPercent}% ({formatCurrency(targetValue)})</span>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-white font-bold text-sm sm:text-base">{currentPercent.toFixed(1)}%</div>
                  <div className="text-xs text-slate-400">{formatCurrency(bucket.currentValue)}</div>
                  <div className={`text-xs font-medium mt-1 ${valueDiff >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {valueDiff >= 0 ? '+' : ''}{formatCurrency(valueDiff)}
                  </div>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden flex items-center relative mb-3">
                <div
                  className="absolute h-full w-0.5 bg-white/50 z-10"
                  style={{ left: `${bucket.targetPercent}%` }}
                />
                <div
                  className={`h-full ${bucket.color} transition-all duration-1000`}
                  style={{ width: `${currentPercent}%` }}
                />
              </div>

              {/* Expanded Details */}
              {isExpanded && (
                <div className="mt-4 pt-3 border-t border-slate-700/50 animate-fade-in">
                  <h4 className="text-xs font-bold text-slate-500 uppercase mb-2">包含资产</h4>
                  <div className="space-y-2">
                    {bucket.holdings.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">暂无资产</p>
                    ) : (
                      bucket.holdings.map(h => {
                        const q = quotes[h.symbol];
                        const price = q ? q.price : h.avgCost;
                        const val = h.shares * price;
                        const allocation = totalValue > 0 ? (val / totalValue) * 100 : 0;
                        return (
                          <div key={h.symbol} className="flex justify-between items-center text-sm">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-slate-300 w-12">{h.symbol}</span>
                              <span className="text-xs text-slate-500 truncate max-w-[100px] hidden sm:inline">{h.name}</span>
                            </div>
                            <div className="flex items-center gap-3">
                              <span className="text-slate-400">{allocation.toFixed(1)}%</span>
                              <span className="text-slate-300 font-mono w-16 text-right">{formatCurrency(val)}</span>
                            </div>
                          </div>
                        )
                      })
                    )}
                  </div>
                  <div className="mt-3 pt-2 border-t border-slate-700/30 flex justify-between items-center text-xs">
                    <span className="text-slate-500">建议操作:</span>
                    <span className={`font-bold ${valueDiff < 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {valueDiff < 0 ? `买入 ${formatCurrency(Math.abs(valueDiff))}` : `卖出 ${formatCurrency(valueDiff)}`}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* AI Analysis Result */}
      {data && (
        <div className="bg-slate-900/50 rounded-xl p-4 sm:p-5 border border-purple-500/30 animate-fade-in">
          <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 mb-4 border-b border-slate-700/50 pb-3">
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex flex-col">
                <span className="text-xs text-slate-400 uppercase">策略执行评分</span>
                <span className={`text-xl sm:text-2xl font-bold ${data.score >= 80 ? 'text-emerald-400' : data.score >= 60 ? 'text-yellow-400' : 'text-rose-400'}`}>
                  {data.score}/100
                </span>
              </div>
              <div className="hidden sm:block h-8 w-px bg-slate-700 mx-1" />
              <div className="flex flex-col">
                <span className="text-xs text-slate-400 uppercase">风险偏好</span>
                <span className="text-sm sm:text-base font-bold text-white">{data.riskLevel}</span>
              </div>
            </div>
          </div>

          <p className="text-slate-300 text-sm leading-relaxed mb-4">
            {data.analysis}
          </p>

          <div>
            <h4 className="text-xs font-bold text-purple-400 uppercase tracking-wide mb-2">调仓建议 (AI)</h4>
            <ul className="space-y-2">
              {data.suggestions.map((s, i) => (
                <li key={i} className="flex gap-3 text-sm text-slate-300 bg-slate-800/50 p-2.5 sm:p-2 rounded">
                  <span className="text-purple-500 font-bold shrink-0">•</span>
                  <span className="min-w-0 break-words">{s}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default StrategyCard;