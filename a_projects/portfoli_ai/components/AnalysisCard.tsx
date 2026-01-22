import React, { useState } from 'react';
import { Sparkles, RefreshCcw, ShieldAlert, ShieldCheck, Shield } from 'lucide-react';
import { analyzePortfolio } from '../services/geminiService';
import { Holding, Quote, AIAnalysisResponse } from '../types';

interface AnalysisCardProps {
  holdings: Holding[];
  quotes: Record<string, Quote>;
}

const AnalysisCard: React.FC<AnalysisCardProps> = ({ holdings, quotes }) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<AIAnalysisResponse | null>(null);

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      const result = await analyzePortfolio(holdings, quotes);
      setData(result);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const getRiskIcon = (level: string) => {
    switch (level) {
      case 'Low': return <ShieldCheck className="w-5 h-5 text-emerald-400" />;
      case 'High': return <ShieldAlert className="w-5 h-5 text-rose-400" />;
      default: return <Shield className="w-5 h-5 text-yellow-400" />;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400';
    if (score >= 60) return 'text-yellow-400';
    return 'text-rose-400';
  };

  return (
    <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-lg">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold flex items-center gap-2 text-white">
          <Sparkles className="w-5 h-5 text-purple-400" />
          AI Portfolio Advisor
        </h2>
        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors text-sm font-medium disabled:opacity-50"
        >
          {loading ? <RefreshCcw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {data ? 'Re-Analyze' : 'Analyze Portfolio'}
        </button>
      </div>

      {!data && !loading && (
        <div className="text-slate-400 text-center py-8">
          <p>Tap "Analyze Portfolio" to get Gemini-powered insights on your holdings.</p>
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center py-8 space-y-4">
          <div className="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
          <p className="text-slate-400 animate-pulse">Consulting Gemini...</p>
        </div>
      )}

      {data && !loading && (
        <div className="space-y-6 animate-fade-in">
          {/* Top Row: Score & Risk */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700">
              <span className="text-slate-400 text-xs uppercase tracking-wider">Health Score</span>
              <div className={`text-3xl font-bold mt-1 ${getScoreColor(data.score)}`}>
                {data.score}/100
              </div>
            </div>
            <div className="bg-slate-900/50 p-4 rounded-lg border border-slate-700">
              <span className="text-slate-400 text-xs uppercase tracking-wider">Risk Level</span>
              <div className="flex items-center gap-2 mt-1">
                {getRiskIcon(data.riskLevel)}
                <span className="text-xl font-bold text-white">{data.riskLevel}</span>
              </div>
            </div>
          </div>

          {/* Analysis Text */}
          <div className="bg-slate-700/30 p-4 rounded-lg border-l-4 border-purple-500">
            <p className="text-slate-200 text-sm leading-relaxed">{data.analysis}</p>
          </div>

          {/* Suggestions */}
          <div>
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Suggested Actions</h3>
            <ul className="space-y-2">
              {data.suggestions.map((s, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-slate-300 bg-slate-900/30 p-3 rounded-lg">
                  <span className="flex-shrink-0 w-5 h-5 bg-purple-500/20 text-purple-400 rounded-full flex items-center justify-center text-xs font-bold">
                    {i + 1}
                  </span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default AnalysisCard;
