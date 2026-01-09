import React from 'react';
import { APP_CONFIG } from '../constants';

interface HeroProps {
  onStartChat: () => void;
}

const Hero: React.FC<HeroProps> = ({ onStartChat }) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 md:py-20 relative">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-[500px] bg-orange-500/10 blur-[120px] rounded-full pointer-events-none"></div>

      <div className="text-center mb-16 relative z-10 selection:bg-orange-500/30">
        <h1 className="text-5xl md:text-7xl font-black mb-6 tracking-tighter">
          Li Sheng <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-yellow-200">OPC</span>
        </h1>
        <div className="flex items-center justify-center gap-4 text-gray-400 font-medium text-sm md:text-base tracking-widest uppercase">
          <span className="h-[1px] w-8 md:w-12 bg-gradient-to-r from-transparent to-gray-600"></span>
          <span>{APP_CONFIG.SLOGAN}</span>
          <span className="h-[1px] w-8 md:w-12 bg-gradient-to-l from-transparent to-gray-600"></span>
        </div>
      </div>

      <div className="w-full max-w-5xl z-10 px-4">
        <div className="flex items-center gap-3 mb-8 justify-center md:justify-start">
          <div className="w-1.5 h-6 bg-orange-500 rounded-full shadow-[0_0_15px_rgba(249,115,22,0.5)]"></div>
          <h2 className="text-xl font-bold tracking-wide">已上线 AI 项目</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
          {/* Active Card */}
          <div className="group relative bg-[#111] border border-white/5 rounded-3xl p-8 hover:border-orange-500/30 transition-all duration-500 hover:shadow-[0_0_40px_rgba(0,0,0,0.5)] overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-70 group-hover:opacity-100 transition-opacity">
              <span className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-900/20 border border-green-500/20 text-green-500 text-xs font-bold tracking-wider">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                运行中
              </span>
            </div>

            <div className="mb-6 relative">
              <div className="absolute -inset-4 bg-orange-500/20 blur-2xl rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
              <div className="w-16 h-16 bg-gradient-to-br from-gray-800 to-black rounded-2xl flex items-center justify-center text-4xl shadow-2xl border border-white/10 relative z-10">
                👑
              </div>
            </div>

            <h3 className="text-2xl font-bold text-white mb-3 group-hover:text-orange-400 transition-colors">
              最优购·省钱大王
            </h3>
            <p className="text-gray-400 text-sm leading-relaxed mb-8 h-12 opacity-80">
              您的 AI 私人导购专家。全网比价、隐藏券搜索、口碑筛选，帮您把价格狠狠打下来！
            </p>

            <button
              onClick={onStartChat}
              className="w-full py-3.5 bg-white text-black font-bold rounded-xl hover:bg-orange-500 hover:text-white transition-all duration-300 transform group-hover:translate-y-[-2px] shadow-lg flex items-center justify-center gap-2"
            >
              <span>立即体验</span>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"></path></svg>
            </button>
          </div>

          {/* Placeholder Card */}
          <div className="group relative bg-[#0a0a0a] border border-white/5 rounded-3xl p-8 opacity-60 hover:opacity-100 transition-all duration-500">
            <div className="absolute top-0 right-0 p-4">
              <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-gray-500 text-xs font-bold tracking-wider">
                筹备中
              </span>
            </div>

            <div className="mb-6 grayscale group-hover:grayscale-0 transition-all duration-500">
              <div className="w-16 h-16 bg-black/50 rounded-2xl flex items-center justify-center text-3xl border border-white/5">
                🚀
              </div>
            </div>

            <h3 className="text-xl font-bold text-gray-300 mb-3">
              更多 AI 智能体
            </h3>
            <p className="text-gray-500 text-sm leading-relaxed mb-8 opacity-80">
              Li Sheng OPC 正在孵化更多垂直领域的 AI 创新项目，敬请期待。
            </p>

            <div className="w-full py-3.5 bg-white/5 text-gray-500 font-bold rounded-xl border border-white/5 flex items-center justify-center text-sm cursor-not-allowed">
              开发中...
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Hero;
