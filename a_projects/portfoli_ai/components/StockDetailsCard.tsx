import React from 'react';
import { TrendingUp, TrendingDown, DollarSign, BarChart3, Activity, Globe } from 'lucide-react';
import { StockInfo } from '../services/stockInfoService';
import { getStrategyBucket, STRATEGY_DEFINITIONS } from '../utils/strategyUtils';

interface StockDetailsCardProps {
  stockInfo: StockInfo;
}

const StockDetailsCard: React.FC<StockDetailsCardProps> = ({ stockInfo }) => {
  const formatCurrency = (value?: number) => {
    if (value === undefined || value === null || value === 0) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: stockInfo.currency || 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatNumber = (value?: number) => {
    if (value === undefined || value === null) return 'N/A';
    if (value >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
    if (value >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
    return value.toFixed(2);
  };

  const formatPercent = (value?: number) => {
    if (value === undefined || value === null) return 'N/A';
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const isPositive = (stockInfo.change ?? 0) >= 0;
  const hasPriceData = stockInfo.currentPrice !== undefined && stockInfo.currentPrice > 0;

  return (
    <div className="bg-slate-900/50 border border-emerald-500/20 border-slate-700 rounded-xl p-4 space-y-4 animate-in fade-in slide-in-from-top-2 duration-300 shadow-lg">
      {/* 标题和价格 */}
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-base sm:text-lg font-bold text-white truncate">{stockInfo.name}</h3>
              {(() => {
                const strat = getStrategyBucket(stockInfo.symbol, stockInfo.sector || '');
                const def = STRATEGY_DEFINITIONS[strat];
                return (
                  <span className={`px-1.5 py-0.5 text-[10px] rounded border ${def.color} whitespace-nowrap`}>
                    {def.name.split(' ')[0]}
                  </span>
                );
              })()}
            </div>
            <p className="text-xs sm:text-sm text-slate-400">{stockInfo.symbol}</p>
          </div>
          {stockInfo.exchange && (
            <div className="flex items-center gap-1 text-xs text-slate-500 shrink-0">
              <Globe className="w-3 h-3" />
              <span className="hidden sm:inline">{stockInfo.exchange}</span>
            </div>
          )}
        </div>

        {hasPriceData && (
          <div className="flex flex-wrap items-baseline gap-2 sm:gap-3">
            <div className="text-xl sm:text-2xl font-bold text-white">
              {formatCurrency(stockInfo.currentPrice)}
            </div>
            {stockInfo.change !== undefined && stockInfo.changePercent !== undefined && (
              <div className={`flex items-center gap-1 text-xs sm:text-sm font-semibold ${isPositive ? 'text-emerald-400' : 'text-rose-400'
                }`}>
                {isPositive ? (
                  <TrendingUp className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                ) : (
                  <TrendingDown className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                )}
                <span>{formatCurrency(Math.abs(stockInfo.change))}</span>
                <span>({formatPercent(stockInfo.changePercent)})</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 详细信息网格 - 参考图2的布局 */}
      {hasPriceData && (
        <div className="space-y-3 pt-3 border-t border-slate-700/50">
          {/* 第一行：前收盘、开盘、当日最高、当日最低 */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {stockInfo.previousClose !== undefined && (
              <div className="space-y-1">
                <div className="text-xs text-slate-500">前收盘</div>
                <div className="text-sm font-medium text-slate-300">
                  {formatCurrency(stockInfo.previousClose)}
                </div>
              </div>
            )}
            {stockInfo.open !== undefined && (
              <div className="space-y-1">
                <div className="text-xs text-slate-500">开盘</div>
                <div className="text-sm font-medium text-slate-300">
                  {formatCurrency(stockInfo.open)}
                </div>
              </div>
            )}
            {stockInfo.dayHigh !== undefined && stockInfo.dayHigh > 0 && (
              <div className="space-y-1">
                <div className="text-xs text-slate-500">最高</div>
                <div className="text-sm font-medium text-emerald-400">
                  {formatCurrency(stockInfo.dayHigh)}
                </div>
              </div>
            )}
            {stockInfo.dayLow !== undefined && stockInfo.dayLow > 0 && (
              <div className="space-y-1">
                <div className="text-xs text-slate-500">最低</div>
                <div className="text-sm font-medium text-rose-400">
                  {formatCurrency(stockInfo.dayLow)}
                </div>
              </div>
            )}
          </div>

          {/* 第二行：成交量、平均成交量、市值、流通股 */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {stockInfo.volume !== undefined && (
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs text-slate-500">
                  <Activity className="w-3 h-3" />
                  <span>成交量</span>
                </div>
                <div className="text-sm font-medium text-slate-300">
                  {formatNumber(stockInfo.volume)}
                </div>
              </div>
            )}
            {stockInfo.averageVolume !== undefined && (
              <div className="space-y-1">
                <div className="text-xs text-slate-500">平均成交量</div>
                <div className="text-sm font-medium text-slate-300">
                  {formatNumber(stockInfo.averageVolume)}
                </div>
              </div>
            )}
            {stockInfo.marketCap !== undefined && (
              <div className="space-y-1">
                <div className="flex items-center gap-1.5 text-xs text-slate-500">
                  <DollarSign className="w-3 h-3" />
                  <span>市值</span>
                </div>
                <div className="text-sm font-medium text-slate-300">
                  {formatNumber(stockInfo.marketCap)}
                </div>
              </div>
            )}
            {stockInfo.sharesOutstanding !== undefined && (
              <div className="space-y-1">
                <div className="text-xs text-slate-500">流通股</div>
                <div className="text-sm font-medium text-slate-300">
                  {formatNumber(stockInfo.sharesOutstanding)}
                </div>
              </div>
            )}
          </div>

          {/* 第三行：52周最高/最低、股息收益率 */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {stockInfo.high52Week !== undefined && (
              <div className="space-y-1">
                <div className="text-xs text-slate-500">52周最高</div>
                <div className="text-sm font-medium text-emerald-400">
                  {formatCurrency(stockInfo.high52Week)}
                </div>
              </div>
            )}
            {stockInfo.low52Week !== undefined && (
              <div className="space-y-1">
                <div className="text-xs text-slate-500">52周最低</div>
                <div className="text-sm font-medium text-rose-400">
                  {formatCurrency(stockInfo.low52Week)}
                </div>
              </div>
            )}
            {stockInfo.dividendYield !== undefined && stockInfo.dividendYield > 0 && (
              <div className="space-y-1">
                <div className="text-xs text-slate-500">股息收益率</div>
                <div className="text-sm font-medium text-slate-300">
                  {(stockInfo.dividendYield * 100).toFixed(2)}%
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 板块信息 */}
      {stockInfo.sector && (
        <div className="pt-3 border-t border-slate-700/50">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">板块</span>
            <span className="text-sm font-medium text-slate-300 px-2 py-1 bg-slate-800 rounded">
              {stockInfo.sector}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default StockDetailsCard;
