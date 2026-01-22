import React, { useState, useEffect } from 'react';
import { X, Save, Lock } from 'lucide-react';
import { Holding } from '../types';

interface EditHoldingModalProps {
  isOpen: boolean;
  holding: Holding | null;
  onClose: () => void;
  onSave: (holding: Holding) => void;
}

const EditHoldingModal: React.FC<EditHoldingModalProps> = ({ isOpen, holding, onClose, onSave }) => {
  const [formData, setFormData] = useState<Holding | null>(null);

  useEffect(() => {
    if (holding) {
      setFormData({ ...holding });
    }
  }, [holding]);

  if (!isOpen || !formData) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (formData) {
      onSave(formData);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-0 sm:p-4">
      <div className="bg-slate-800 w-full max-w-md max-h-[90vh] sm:max-h-[85vh] rounded-t-2xl sm:rounded-2xl border border-slate-700 border-b-0 sm:border-b shadow-2xl flex flex-col pb-[env(safe-area-inset-bottom,0px)] sm:pb-0">
        <div className="flex justify-between items-center gap-2 p-4 sm:p-6 shrink-0 border-b border-slate-700/50 sm:border-b-0">
          <h2 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2 min-w-0">
            <span className="truncate">编辑持仓 (Edit)</span>
            <span className="text-xs sm:text-sm font-normal text-slate-400 bg-slate-900 px-2 py-1 rounded shrink-0">
              {formData.symbol}
            </span>
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white active:text-white p-2 -m-2 transition-colors shrink-0 touch-manipulation" aria-label="关闭">
            <X className="w-5 h-5 sm:w-6 sm:h-6" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 pt-0">
          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1 flex items-center gap-1">
                账户 (锁定) <Lock className="w-3 h-3" />
              </label>
              <input
                type="text"
                disabled
                className="w-full bg-slate-900/50 border border-slate-700/50 rounded-lg px-4 py-2 text-slate-500 cursor-not-allowed"
                value={formData.account}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1 flex items-center gap-1">
                代码 (锁定) <Lock className="w-3 h-3" />
              </label>
              <input
                type="text"
                disabled
                className="w-full bg-slate-900/50 border border-slate-700/50 rounded-lg px-4 py-2 text-slate-500 cursor-not-allowed uppercase"
                value={formData.symbol}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">公司名称</label>
            <input
              type="text"
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">持股数</label>
              <input
                type="number"
                required
                min="0.00001"
                step="any"
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none"
                value={formData.shares}
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
                value={formData.avgCost}
                onChange={e => setFormData({ ...formData, avgCost: parseFloat(e.target.value) })}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">板块</label>
            <select
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none"
              value={formData.sector}
              onChange={e => setFormData({ ...formData, sector: e.target.value })}
            >
              <option value="Technology">科技</option>
              <option value="Financial">金融</option>
              <option value="Healthcare">医疗</option>
              <option value="Consumer Cyclical">消费周期</option>
              <option value="Consumer Defensive">消费防御</option>
              <option value="Communication">通讯</option>
              <option value="Energy">能源</option>
              <option value="Industrial">工业</option>
              <option value="Basic Materials">原材料</option>
              <option value="Real Estate">房地产</option>
              <option value="Utilities">公用事业</option>
            </select>
          </div>

          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 active:scale-[0.99] text-white font-bold py-3 rounded-lg transition-all flex items-center justify-center gap-2 mt-6 touch-manipulation"
          >
            <Save className="w-5 h-5" />
            保存修改
          </button>
        </form>
      </div>
    </div>
  );
};

export default EditHoldingModal;