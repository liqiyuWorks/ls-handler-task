import React, { useState, useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Holding, Quote } from '../types';
import { TrendingUp, TrendingDown } from 'lucide-react';

interface PortfolioChartProps {
  holdings: Holding[];
  quotes: Record<string, Quote>;
}

interface ChartDataItem {
  name: string;
  fullName: string;
  symbol: string;
  value: number;
  totalReturn: number;
  returnPct: number;
}

const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#6366f1'];

const formatCurrency = (val: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(val);
const formatPercent = (val: number) => `${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;

const PortfolioChart: React.FC<PortfolioChartProps> = ({ holdings, quotes }) => {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);

  const data = useMemo<ChartDataItem[]>(() => {
    return holdings
      .map(h => {
        const currentPrice = quotes[h.symbol]?.price ?? h.avgCost;
        const marketValue = h.shares * currentPrice;
        const cost = h.shares * h.avgCost;
        const totalReturn = marketValue - cost;
        const returnPct = cost > 0 ? (totalReturn / cost) * 100 : 0;
        return {
          name: h.symbol,
          fullName: h.name || h.symbol,
          symbol: h.symbol,
          value: marketValue,
          totalReturn,
          returnPct,
        };
      })
      .sort((a, b) => b.value - a.value);
  }, [holdings, quotes]);

  const selected = activeIndex != null && data[activeIndex] ? data[activeIndex] : null;

  const handlePieClick = (_: unknown, index: number) => {
    setActiveIndex(prev => (prev === index ? null : index));
  };

  return (
    <div className="bg-slate-800 rounded-xl p-4 sm:p-6 border border-slate-700 shadow-lg min-h-[260px] sm:min-h-[320px] lg:h-[400px]">
      <h2 className="text-base sm:text-lg font-bold text-white mb-3 sm:mb-4">资产分布 (Allocation)</h2>
      <div className="h-[200px] sm:h-[260px] lg:h-[320px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius="40%"
              outerRadius="65%"
              paddingAngle={5}
              dataKey="value"
              onClick={handlePieClick}
              activeIndex={activeIndex ?? undefined}
              activeShape={{ stroke: 'rgba(255,255,255,0.6)', strokeWidth: 2 }}
            >
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={COLORS[index % COLORS.length]}
                  stroke="rgba(0,0,0,0)"
                  className="cursor-pointer"
                />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
              contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc', fontSize: '12px' }}
              itemStyle={{ color: '#f8fafc' }}
            />
            <Legend
              verticalAlign="bottom"
              height={32}
              iconType="circle"
              iconSize={8}
              wrapperStyle={{ fontSize: '12px' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      {selected && (
        <div className="mt-4 p-3 sm:p-4 rounded-lg bg-slate-900/80 border border-slate-600">
          <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">点击选中</p>
          <p className="font-bold text-white truncate" title={selected.fullName}>
            {selected.fullName} <span className="text-slate-500 font-normal">({selected.symbol})</span>
          </p>
          <div className="flex items-center gap-2 mt-2">
            {selected.totalReturn >= 0 ? (
              <TrendingUp className="w-4 h-4 text-emerald-500 shrink-0" />
            ) : (
              <TrendingDown className="w-4 h-4 text-rose-500 shrink-0" />
            )}
            <span className={selected.totalReturn >= 0 ? 'text-emerald-400' : 'text-rose-400'}>{formatCurrency(selected.totalReturn)}</span>
            <span className={`text-sm ${selected.returnPct >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
              {formatPercent(selected.returnPct)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default PortfolioChart;