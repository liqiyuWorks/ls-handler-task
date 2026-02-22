import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { APP_CONFIG } from '../constants';
import { Sparkles, Compass, Crown } from 'lucide-react';

interface HeroProps {
  onStartChat: () => void;
}

const Hero: React.FC<HeroProps> = ({ onStartChat }) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'apps' | 'pro'>('apps');

  return (
    <div className="flex flex-col items-center justify-center py-20 md:py-32 relative min-h-[80vh]">
      {/* Background Ambience */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-gradient-to-tr from-orange-500/5 to-purple-500/5 blur-[120px] rounded-full pointer-events-none"></div>

      <div className="text-center mb-10 relative z-10">
        <h1 className="text-5xl md:text-7xl font-black mb-4 tracking-tighter text-white drop-shadow-2xl flex flex-col md:flex-row items-center justify-center gap-2 md:gap-4">
          <span>LiSheng AI</span>
          <span className="text-orange-500/80 text-3xl md:text-5xl transform rotate-0">✖️</span>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-amber-200">OPC</span>
        </h1>
        <div className="flex flex-col items-center justify-center gap-6 text-gray-400 font-light text-sm md:text-base tracking-[0.3em] uppercase opacity-90 mb-5">
          <span>{APP_CONFIG.SLOGAN}</span>
        </div>

        {/* Tab Switcher */}
        <div className="grid grid-cols-2 bg-white/5 backdrop-blur-md border border-white/10 p-1.5 rounded-full shadow-2xl relative mx-auto mt-2 w-[340px] md:w-[400px]">
          {/* Animated Highlight */}
          <div
            className="absolute top-1.5 bottom-1.5 w-[calc(50%-6px)] bg-gradient-to-r from-orange-500 to-amber-500 rounded-full transition-all duration-300 ease-out shadow-[0_0_15px_rgba(249,115,22,0.4)]"
            style={{ left: activeTab === 'apps' ? '6px' : '50%' }}
          ></div>

          <button
            onClick={() => setActiveTab('apps')}
            className={`relative z-10 flex items-center justify-center gap-2 py-2.5 rounded-full font-bold transition-colors duration-300 text-sm md:text-base ${activeTab === 'apps' ? 'text-white' : 'text-gray-400 hover:text-white'}`}
          >
            <Compass size={18} className={activeTab === 'apps' ? 'text-white' : 'text-gray-500'} /><span>探索应用</span>
          </button>

          <button
            onClick={() => setActiveTab('pro')}
            className={`relative z-10 flex items-center justify-center gap-2 py-2.5 rounded-full font-bold transition-colors duration-300 text-sm md:text-base ${activeTab === 'pro' ? 'text-white' : 'text-gray-400 hover:text-white'}`}
          >
            <Crown size={18} className={activeTab === 'pro' ? 'text-white' : 'text-gray-500'} /><span>进阶创作</span>
          </button>
        </div>
      </div>

      <div className="w-full max-w-6xl z-10 px-6 mt-10 md:mt-16 min-h-[500px]">

        {/* Section 1: Free Tools & Tutorials */}
        <div className={`transition-all duration-700 w-full ${activeTab === 'apps' ? 'opacity-100 translate-y-0 relative z-20' : 'opacity-0 translate-y-10 absolute pointer-events-none'}`}>
          <section id="explore-apps" className="w-full">
            <div className="mb-10 text-center md:text-left flex flex-col items-center md:items-start">
              <h2 className="text-3xl font-bold text-white flex items-center gap-3">
                📚 智能助手与资源
              </h2>
              <p className="text-gray-400 mt-2 font-light">内置多个实用智能助手，助您提升效率。</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Savings Agent */}
              <div className="group bg-white/5 backdrop-blur-sm border border-white/5 rounded-2xl p-6 hover:bg-white/10 hover:border-white/20 transition-all duration-300">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 bg-gray-800 rounded-xl flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">👑</div>
                  <h3 className="text-lg font-bold text-white">省钱大王</h3>
                </div>
                <p className="text-gray-400 text-sm mb-6 h-10 line-clamp-2">全网比价、隐藏券搜索，帮您把价格狠狠打下来！</p>
                <button onClick={onStartChat} className="text-sm font-medium text-gray-300 group-hover:text-white flex items-center gap-1">开始对话 <span className="group-hover:translate-x-1 transition-transform">→</span></button>
              </div>

              {/* Finance Agent */}
              <div className="group bg-white/5 backdrop-blur-sm border border-white/5 rounded-2xl p-6 hover:bg-white/10 hover:border-white/20 transition-all duration-300">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 bg-gray-800 rounded-xl flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">📊</div>
                  <h3 className="text-lg font-bold text-white">财报分析</h3>
                </div>
                <p className="text-gray-400 text-sm mb-6 h-10 line-clamp-2">轻松解读财务数据，洞察企业经营状况与风险。</p>
                <button onClick={() => navigate('/finance-agent')} className="text-sm font-medium text-gray-300 group-hover:text-white flex items-center gap-1">开始对话 <span className="group-hover:translate-x-1 transition-transform">→</span></button>
              </div>

              {/* Cover Agent */}
              <div className="group bg-white/5 backdrop-blur-sm border border-white/5 rounded-2xl p-6 hover:bg-white/10 hover:border-white/20 transition-all duration-300">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 bg-gray-800 rounded-xl flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">🎨</div>
                  <h3 className="text-lg font-bold text-white">封面助手</h3>
                </div>
                <p className="text-gray-400 text-sm mb-6 h-10 line-clamp-2">一键生成吸睛的公众号与自媒体文章封面。</p>
                <button onClick={() => navigate('/article-cover-agent')} className="text-sm font-medium text-gray-300 group-hover:text-white flex items-center gap-1">开始对话 <span className="group-hover:translate-x-1 transition-transform">→</span></button>
              </div>

              {/* Placeholder Tutorial 1 */}
              <div className="md:col-span-1 border border-dashed border-white/10 rounded-2xl p-6 flex flex-col items-center justify-center text-center opacity-50 relative overflow-hidden">
                <div className="absolute inset-0 bg-repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,0.02) 10px, rgba(255,255,255,0.02) 20px)"></div>
                <div className="text-3xl mb-3">📖</div>
                <h3 className="text-base font-medium text-white mb-2">AI 提效实战指南</h3>
                <p className="text-xs text-gray-400 tracking-wider">COMING SOON</p>
              </div>

              {/* Placeholder Tutorial 2 */}
              <div className="md:col-span-2 border border-dashed border-white/10 rounded-2xl p-6 flex flex-col items-center justify-center text-center opacity-50 relative overflow-hidden">
                <div className="absolute inset-0 bg-repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,0.02) 10px, rgba(255,255,255,0.02) 20px)"></div>
                <div className="text-3xl mb-3">🛠️</div>
                <h3 className="text-base font-medium text-white mb-2">如何利用大模型分析行业报告</h3>
                <p className="text-xs text-gray-400 tracking-wider">COMING SOON</p>
              </div>
            </div>
          </section>
        </div>

        {/* Section 2: Advanced Creation Engines (VIP/Pro) */}
        <div className={`transition-all duration-700 w-full ${activeTab === 'pro' ? 'opacity-100 translate-y-0 relative z-20' : 'opacity-0 translate-y-10 absolute pointer-events-none'}`}>
          <section id="advanced-creation" className="w-full">
            <div className="mb-10 text-center md:text-left flex flex-col md:flex-row items-center md:items-end gap-3 md:gap-6">
              <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-amber-200 to-amber-500 flex items-center justify-center md:justify-start gap-3">
                <Sparkles className="text-amber-400" size={32} />
                Pro 旗舰创研引擎
              </h2>
              <p className="text-gray-400 mt-2 md:mb-1 font-light tracking-wide text-sm">基于多项核心自研多模态模型，根据业务需求深度对齐的最先进创作能力。</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Image Generation */}
              <div className="group relative bg-gradient-to-br from-white/5 to-black/40 backdrop-blur-md border border-white/10 rounded-3xl p-8 hover:border-amber-500/40 transition-all duration-500 shadow-xl overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/10 rounded-full blur-3xl group-hover:bg-amber-500/20 transition-colors"></div>

                <div className="mb-8 relative z-10">
                  <div className="flex items-center justify-between mb-6">
                    <div className="w-16 h-16 bg-gradient-to-br from-amber-500/20 to-amber-600/10 rounded-2xl flex items-center justify-center text-4xl shadow-inner border border-amber-500/20">
                      🖼️
                    </div>
                    <div className="px-3 py-1 rounded-full bg-gradient-to-r from-amber-200 to-amber-500 text-amber-950 text-xs font-bold flex items-center gap-1 shadow-[0_0_15px_rgba(251,191,36,0.3)]">
                      <Sparkles size={12} />
                      PRO
                    </div>
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-3 tracking-wide flex items-center gap-2">
                    AI 创意工坊 <span className="text-amber-500/80 font-light text-xl">Pro</span>
                  </h3>
                  <p className="text-gray-400 text-sm leading-relaxed h-12 line-clamp-2 font-light">
                    自研商业级高保真生图大模型，支持超精细画质与多比例控制，让专业想象力自由落地。
                  </p>
                </div>

                <button
                  onClick={() => navigate('/image-generation')}
                  className="relative z-10 w-full py-4 rounded-xl font-bold text-amber-950 bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 transition-all duration-300 shadow-[0_0_20px_rgba(251,191,36,0.2)] hover:shadow-[0_0_30px_rgba(251,191,36,0.4)]"
                >
                  开始生成
                </button>
              </div>

              {/* Video Generation */}
              <div className="group relative bg-gradient-to-br from-white/5 to-black/40 backdrop-blur-md border border-white/10 rounded-3xl p-8 hover:border-amber-500/40 transition-all duration-500 shadow-xl overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/10 rounded-full blur-3xl group-hover:bg-amber-500/20 transition-colors"></div>

                <div className="mb-8 relative z-10">
                  <div className="flex items-center justify-between mb-6">
                    <div className="w-16 h-16 bg-gradient-to-br from-amber-500/20 to-amber-600/10 rounded-2xl flex items-center justify-center text-4xl shadow-inner border border-amber-500/20">
                      🎬
                    </div>
                    <div className="px-3 py-1 rounded-full bg-gradient-to-r from-amber-200 to-amber-500 text-amber-950 text-xs font-bold flex items-center gap-1 shadow-[0_0_15px_rgba(251,191,36,0.3)]">
                      <Sparkles size={12} />
                      PRO
                    </div>
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-3 tracking-wide flex items-center gap-2">
                    AI 视频生成 <span className="text-amber-500/80 font-light text-xl">Pro</span>
                  </h3>
                  <p className="text-gray-400 text-sm leading-relaxed h-12 line-clamp-2 font-light">
                    行业领先的自研动态视频生成技术，支持根据特定需求深度定制。图生视频、文生视频为您开启影视级创作之旅。
                  </p>
                </div>

                <button
                  onClick={() => navigate('/video-generation')}
                  className="relative z-10 w-full py-4 rounded-xl font-bold text-amber-950 bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 transition-all duration-300 shadow-[0_0_20px_rgba(251,191,36,0.2)] hover:shadow-[0_0_30px_rgba(251,191,36,0.4)]"
                >
                  开始生成
                </button>
              </div>
            </div>
          </section>
        </div>

      </div>
    </div>
  );
};

export default Hero;
