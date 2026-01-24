import React from 'react';
import { useNavigate } from 'react-router-dom';
import { APP_CONFIG } from '../constants';

interface HeroProps {
  onStartChat: () => void;
}

const Hero: React.FC<HeroProps> = ({ onStartChat }) => {
  const navigate = useNavigate();
  return (
    <div className="flex flex-col items-center justify-center py-20 md:py-32 relative min-h-[80vh]">
      {/* Background Ambience */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-gradient-to-tr from-orange-500/5 to-purple-500/5 blur-[120px] rounded-full pointer-events-none"></div>

      <div className="text-center mb-24 relative z-10">
        <h1 className="text-5xl md:text-7xl font-black mb-8 tracking-tighter text-white drop-shadow-2xl flex flex-col md:flex-row items-center justify-center gap-2 md:gap-4">
          <span>LiSheng AI</span>
          <span className="text-orange-500/80 text-3xl md:text-5xl transform rotate-0">✖️</span>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-amber-200">OPC</span>
        </h1>
        <div className="flex items-center justify-center gap-6 text-gray-400 font-light text-sm md:text-base tracking-[0.3em] uppercase opacity-70">
          <span>{APP_CONFIG.SLOGAN}</span>
        </div>
      </div>

      <div className="w-full max-w-6xl z-10 px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Active Card */}
          <div className="group relative bg-white/5 backdrop-blur-sm border border-white/5 rounded-3xl p-8 hover:bg-white/10 hover:border-orange-500/20 transition-all duration-500 hover:-translate-y-1">
            <div className="absolute top-6 right-6">
              <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]"></span>
            </div>

            <div className="mb-8">
              <div className="w-14 h-14 bg-gradient-to-br from-orange-500/20 to-orange-600/5 rounded-2xl flex items-center justify-center text-3xl mb-6 group-hover:scale-110 transition-transform duration-500">
                👑
              </div>
              <h3 className="text-xl font-bold text-white mb-3 tracking-wide">
                省钱大王
              </h3>
              <p className="text-gray-400 text-sm leading-relaxed h-12 line-clamp-2 font-light">
                全网比价、隐藏券搜索，帮您把价格狠狠打下来！
              </p>
            </div>

            <button
              onClick={onStartChat}
              className="w-full py-3 rounded-xl border border-white/10 text-sm font-medium text-gray-300 group-hover:text-white group-hover:border-orange-500/50 group-hover:bg-orange-500/10 transition-all duration-300 flex items-center justify-center gap-2"
            >
              <span>开始对话</span>
              <svg className="w-4 h-4 opacity-50 group-hover:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 8l4 4m0 0l-4 4m4-4H3"></path></svg>
            </button>
          </div>

          {/* Finance Card */}
          <div className="group relative bg-white/5 backdrop-blur-sm border border-white/5 rounded-3xl p-8 hover:bg-white/10 hover:border-blue-500/20 transition-all duration-500 hover:-translate-y-1">
            <div className="absolute top-6 right-6">
              <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]"></span>
            </div>

            <div className="mb-8">
              <div className="w-14 h-14 bg-gradient-to-br from-blue-500/20 to-blue-600/5 rounded-2xl flex items-center justify-center text-3xl mb-6 group-hover:scale-110 transition-transform duration-500">
                📊
              </div>
              <h3 className="text-xl font-bold text-white mb-3 tracking-wide">
                财报分析
              </h3>
              <p className="text-gray-400 text-sm leading-relaxed h-12 line-clamp-2 font-light">
                轻松解读财务数据，洞察企业经营状况与风险。
              </p>
            </div>

            <button
              onClick={() => navigate('/finance-agent')}
              className="w-full py-3 rounded-xl border border-white/10 text-sm font-medium text-gray-300 group-hover:text-white group-hover:border-blue-500/50 group-hover:bg-blue-500/10 transition-all duration-300 flex items-center justify-center gap-2"
            >
              <span>开始对话</span>
              <svg className="w-4 h-4 opacity-50 group-hover:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 8l4 4m0 0l-4 4m4-4H3"></path></svg>
            </button>
          </div>

          {/* Article Cover Card */}
          <div className="group relative bg-white/5 backdrop-blur-sm border border-white/5 rounded-3xl p-8 hover:bg-white/10 hover:border-purple-500/20 transition-all duration-500 hover:-translate-y-1">
            <div className="absolute top-6 right-6">
              <span className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]"></span>
            </div>

            <div className="mb-8">
              <div className="w-14 h-14 bg-gradient-to-br from-purple-500/20 to-purple-600/5 rounded-2xl flex items-center justify-center text-3xl mb-6 group-hover:scale-110 transition-transform duration-500">
                🎨
              </div>
              <h3 className="text-xl font-bold text-white mb-3 tracking-wide">
                封面助手
              </h3>
              <p className="text-gray-400 text-sm leading-relaxed h-12 line-clamp-2 font-light">
                一键生成吸睛的公众号与自媒体文章封面。
              </p>
            </div>

            <button
              onClick={() => navigate('/article-cover-agent')}
              className="w-full py-3 rounded-xl border border-white/10 text-sm font-medium text-gray-300 group-hover:text-white group-hover:border-purple-500/50 group-hover:bg-purple-500/10 transition-all duration-300 flex items-center justify-center gap-2"
            >
              <span>开始对话</span>
              <svg className="w-4 h-4 opacity-50 group-hover:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 8l4 4m0 0l-4 4m4-4H3"></path></svg>
            </button>
          </div>

        </div>
      </div>
    </div>
  );
};

export default Hero;
