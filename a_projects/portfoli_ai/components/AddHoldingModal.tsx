import React, { useState } from 'react';
import { X, Plus } from 'lucide-react';
import { Holding } from '../types';

interface AddHoldingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (holding: Holding) => void;
}

const AddHoldingModal: React.FC<AddHoldingModalProps> = ({ isOpen, onClose, onAdd }) => {
  const [formData, setFormData] = useState<Partial<Holding>>({
    symbol: '',
    name: '',
    shares: 0,
    avgCost: 0,
    sector: 'Technology',
    account: 'FirstTrade'
  });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData.symbol && formData.shares && formData.avgCost) {
      onAdd({
        symbol: formData.symbol.toUpperCase(),
        name: formData.name || formData.symbol.toUpperCase(),
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
            <input
              type="text"
              required
              placeholder="例如: AAPL"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none uppercase"
              value={formData.symbol}
              onChange={e => setFormData({ ...formData, symbol: e.target.value })}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">公司名称 (Company Name)</label>
            <input
              type="text"
              placeholder="例如: Apple Inc."
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
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