import React, { useState, useEffect, useRef } from 'react';
import { X, Plus, Loader2, AlertCircle, RefreshCw } from 'lucide-react';
import { Holding } from '../types';
import { getStockInfo, StockInfo } from '../services/stockInfoService';
import StockDetailsCard from './StockDetailsCard';

interface AddHoldingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (holding: Holding) => void;
  existingHoldings: Holding[];
  defaultAccount?: string;
}

const AddHoldingModal: React.FC<AddHoldingModalProps> = ({ isOpen, onClose, onAdd, existingHoldings, defaultAccount }) => {
  const [formData, setFormData] = useState<Partial<Holding>>({
    symbol: '',
    name: '',
    shares: 0,
    avgCost: 0,
    sector: 'Technology',
    account: (defaultAccount as any) || 'FirstTrade'
  });
  const [error, setError] = useState<string | null>(null);
  const [isLoadingStockInfo, setIsLoadingStockInfo] = useState(false);
  const [stockDetails, setStockDetails] = useState<StockInfo | null>(null);
  const [stockInfoError, setStockInfoError] = useState<string | null>(null);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const userManuallyEditedName = useRef(false);

  // 当对话框关闭时重置表单
  useEffect(() => {
    if (!isOpen) {
      setFormData({
        symbol: '',
        name: '',
        shares: 0,
        avgCost: 0,
        sector: 'Technology',
        account: (defaultAccount as any) || 'FirstTrade'
      });
      setIsLoadingStockInfo(false);
      setStockDetails(null);
      setStockInfoError(null);
      setError(null);
      userManuallyEditedName.current = false;
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
        debounceTimer.current = null;
      }
    } else {
      // 当打开时，如果有 defaultAccount，更新它
      if (defaultAccount) {
        setFormData(prev => ({ ...prev, account: defaultAccount as any }));
      }
    }
  }, [isOpen, defaultAccount]);

  // 根据股票代码自动获取公司信息
  useEffect(() => {
    if (!isOpen) return;

    const symbol = formData.symbol?.trim().toUpperCase();

    // 如果代码为空或太短，不查询
    if (!symbol || symbol.length < 1) {
      return;
    }

    // 如果用户手动编辑过名称，不自动覆盖
    if (userManuallyEditedName.current) {
      return;
    }

    // 清除之前的定时器
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    // 防抖：等待用户停止输入 500ms 后再查询
    debounceTimer.current = setTimeout(async () => {
      setIsLoadingStockInfo(true);
      setStockInfoError(null);
      setStockDetails(null);
      console.log(`[AddHoldingModal] 开始查询股票信息: ${symbol}`);
      try {
        const stockInfo = await getStockInfo(symbol);
        console.log(`[AddHoldingModal] 获取到股票信息:`, stockInfo);

        if (!stockInfo) {
          setStockInfoError('未找到该股票代码，请检查代码是否正确');
          return;
        }

        // 保存详细信息用于展示
        setStockDetails(stockInfo);

        if (!userManuallyEditedName.current) {
          // 确保获取到了有效的名称
          if (stockInfo.name && stockInfo.name !== symbol) {
            setFormData(prev => ({
              ...prev,
              name: stockInfo.name,
              sector: stockInfo.sector || prev.sector || 'Technology'
            }));
            console.log(`[AddHoldingModal] 已自动填充: ${stockInfo.name}`);
          } else {
            console.warn(`[AddHoldingModal] 获取的名称无效: ${stockInfo.name}`);
            // 即使名称无效，也显示基本信息
            if (stockInfo.name) {
              setFormData(prev => ({
                ...prev,
                name: stockInfo.name,
                sector: stockInfo.sector || prev.sector || 'Technology'
              }));
            }
          }
        } else {
          console.log(`[AddHoldingModal] 用户已手动编辑名称，跳过自动填充`);
        }
      } catch (error: any) {
        console.error('[AddHoldingModal] 获取股票信息失败:', error);
        setStockInfoError(error?.message || '获取股票信息失败，请稍后重试');
      } finally {
        setIsLoadingStockInfo(false);
      }
    }, 500);

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [formData.symbol, isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.symbol && formData.shares && formData.avgCost) {
      const symbol = formData.symbol.toUpperCase();

      // 检查是否存在重复代号 (当前账户内唯一)
      const list = existingHoldings || [];
      const existing = list.find(h => h.symbol === symbol && h.account === formData.account);
      if (existing) {
        setError(`该股票 (${symbol}) 已在 ${formData.account} 账户中存在。请勿重复添加，您可以修改现有持仓。`);
        return;
      }

      onAdd({
        symbol: symbol,
        name: formData.name || symbol,
        shares: Number(formData.shares),
        avgCost: Number(formData.avgCost),
        sector: formData.sector || 'Technology',
        account: (formData.account as any) || 'FirstTrade'
      });
      onClose();
      setFormData({
        symbol: '',
        name: '',
        shares: 0,
        avgCost: 0,
        sector: 'Technology',
        account: 'FirstTrade'
      });
      setError(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-0 sm:p-4">
      <div className="bg-slate-800 w-full max-w-md max-h-[90vh] sm:max-h-[85vh] rounded-t-2xl sm:rounded-2xl border border-slate-700 border-b-0 sm:border-b shadow-2xl flex flex-col pb-[env(safe-area-inset-bottom,0px)] sm:pb-0">
        <div className="flex justify-between items-center p-4 sm:p-6 shrink-0 border-b border-slate-700/50 sm:border-b-0">
          <h2 className="text-lg sm:text-xl font-bold text-white">添加持仓 (Add Holding)</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white active:text-white p-2 -m-2 transition-colors touch-manipulation" aria-label="关闭">
            <X className="w-5 h-5 sm:w-6 sm:h-6" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 pt-0">
          {error && (
            <div className="flex items-start gap-2 text-sm text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg p-3">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">账户 (Account)</label>
            <select
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none"
              value={formData.account}
              onChange={e => setFormData({ ...formData, account: e.target.value as any })}
            >
              <option value="FirstTrade">FirstTrade (第一证券)</option>
              <option value="IBKR">IBKR (盈透证券)</option>
              <option value="uSmart">uSmart (盈立证券)</option>
              <option value="Other">Other (其他)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">代码 (Symbol)</label>
            <div className="relative">
              <input
                type="text"
                required
                placeholder="例如: AAPL"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none uppercase"
                value={formData.symbol}
                onChange={e => {
                  setFormData({ ...formData, symbol: e.target.value, name: '' });
                  setStockDetails(null); // 清除之前的详细信息
                  setStockInfoError(null); // 清除错误信息
                  userManuallyEditedName.current = false; // 重置标志，允许自动填充
                }}
              />
              {isLoadingStockInfo && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <Loader2 className="w-4 h-4 text-emerald-500 animate-spin" />
                </div>
              )}
            </div>
            {formData.symbol && !isLoadingStockInfo && !formData.name && !stockDetails && !stockInfoError && (
              <p className="text-xs text-slate-500 mt-1">输入代码后将自动获取公司信息</p>
            )}
            {isLoadingStockInfo && (
              <div className="flex items-center gap-2 text-xs text-emerald-500 mt-1">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>正在查询股票信息...</span>
              </div>
            )}
            {stockInfoError && !isLoadingStockInfo && (
              <div className="flex items-center gap-2 text-xs text-rose-400 mt-1 bg-rose-500/10 border border-rose-500/20 rounded-lg p-2">
                <AlertCircle className="w-3 h-3 shrink-0" />
                <span className="flex-1">{stockInfoError}</span>
                <button
                  type="button"
                  onClick={async () => {
                    const symbol = formData.symbol?.trim().toUpperCase();
                    if (symbol) {
                      setIsLoadingStockInfo(true);
                      setStockInfoError(null);
                      try {
                        const stockInfo = await getStockInfo(symbol);
                        if (stockInfo) {
                          setStockDetails(stockInfo);
                          if (!userManuallyEditedName.current && stockInfo.name) {
                            setFormData(prev => ({
                              ...prev,
                              name: stockInfo.name,
                              sector: stockInfo.sector || prev.sector || 'Technology'
                            }));
                          }
                        } else {
                          setStockInfoError('未找到该股票代码');
                        }
                      } catch (error: any) {
                        setStockInfoError(error?.message || '获取失败');
                      } finally {
                        setIsLoadingStockInfo(false);
                      }
                    }
                  }}
                  className="text-rose-400 hover:text-rose-300 transition-colors"
                  title="重试"
                >
                  <RefreshCw className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>

          {/* 股票详细信息卡片 */}
          {stockDetails && !isLoadingStockInfo && (
            <StockDetailsCard stockInfo={stockDetails} />
          )}

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">公司名称 (Company Name)</label>
            <input
              type="text"
              placeholder="例如: Apple Inc. (将根据代码自动填充)"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none"
              value={formData.name}
              onChange={e => {
                setFormData({ ...formData, name: e.target.value });
                userManuallyEditedName.current = true; // 标记为用户手动编辑
              }}
            />
          </div>

          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">持股数 (Shares)</label>
              <input
                type="number"
                required
                min="0.00001"
                step="any"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none"
                value={formData.shares || ''}
                onChange={e => setFormData({ ...formData, shares: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">成本均价 ($)</label>
              <input
                type="number"
                required
                min="0.01"
                step="any"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none"
                value={formData.avgCost || ''}
                onChange={e => setFormData({ ...formData, avgCost: parseFloat(e.target.value) })}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">板块 (Sector)</label>
            <select
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none"
              value={formData.sector}
              onChange={e => setFormData({ ...formData, sector: e.target.value })}
            >
              <option value="Technology">科技 (Technology)</option>
              <option value="Financial">金融 (Financial)</option>
              <option value="Healthcare">医疗 (Healthcare)</option>
              <option value="Consumer Cyclical">消费周期 (Consumer Cyclical)</option>
              <option value="Consumer Defensive">消费防御 (Consumer Defensive)</option>
              <option value="Communication">通讯 (Communication)</option>
              <option value="Energy">能源 (Energy)</option>
              <option value="Industrial">工业 (Industrial)</option>
              <option value="Basic Materials">原材料 (Basic Materials)</option>
              <option value="Real Estate">房地产 (Real Estate)</option>
              <option value="Utilities">公用事业 (Utilities)</option>
            </select>
          </div>

          <button
            type="submit"
            className="w-full bg-emerald-600 hover:bg-emerald-700 active:scale-[0.99] text-white font-bold py-3 rounded-lg transition-all flex items-center justify-center gap-2 mt-6 touch-manipulation"
          >
            <Plus className="w-5 h-5" />
            添加到组合
          </button>
        </form>
      </div>
    </div>
  );
};

export default AddHoldingModal;