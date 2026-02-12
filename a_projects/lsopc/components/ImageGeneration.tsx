import React, { useState, useEffect } from 'react';
import { getImageOptions, generateImage, ImageOptions } from '../services/image';
import { isAuthenticated } from '../services/auth';
import { Loader2, Image as ImageIcon, Download, Sparkles, LogIn, CheckCircle2, Wand2, Maximize2, Ratio } from 'lucide-react';

// 选项描述映射
const resolutionDescriptions: Record<string, string> = {
  '1K': '标准',
  '2K': '高清',
  '4K': '超清'
};

const aspectRatioDescriptions: Record<string, string> = {
  '1:1': '方形',
  '16:9': '宽屏',
  '9:16': '竖屏',
  '4:3': '标准',
  '3:4': '标准竖',
  '3:2': '经典',
  '2:3': '经典竖',
  '21:9': '电影',
  '5:4': '传统',
  '4:5': '社媒'
};

const ImageGeneration: React.FC = () => {
  const handleLoginRequired = () => {
    window.dispatchEvent(new CustomEvent('openAuthModal'));
  };

  const [options, setOptions] = useState<ImageOptions | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  
  const [prompt, setPrompt] = useState('');
  const [resolution, setResolution] = useState('');
  const [aspectRatio, setAspectRatio] = useState('');
  
  const [generating, setGenerating] = useState(false);
  const [generatedImage, setGeneratedImage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const [isLoggedIn, setIsLoggedIn] = useState(isAuthenticated());

  useEffect(() => {
    const handleAuthChange = () => {
      setIsLoggedIn(isAuthenticated());
    };
    
    window.addEventListener('storage', handleAuthChange);
    window.addEventListener('authStateChanged', handleAuthChange);
    
    return () => {
      window.removeEventListener('storage', handleAuthChange);
      window.removeEventListener('authStateChanged', handleAuthChange);
    };
  }, []);

  useEffect(() => {
    async function fetchOptions() {
      try {
        const data = await getImageOptions();
        setOptions(data);
        setResolution(data.resolutions.default);
        setAspectRatio(data.aspect_ratios.default);
      } catch (err) {
        setError('加载配置失败');
      } finally {
        setLoadingOptions(false);
      }
    }
    fetchOptions();
  }, []);

  const handleGenerate = async () => {
    if (!prompt) return;
    
    setGenerating(true);
    setError(null);
    setGeneratedImage(null);

    try {
      const result = await generateImage({
        prompt,
        resolution,
        aspect_ratio: aspectRatio
      });
      setGeneratedImage(result.image_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成图片失败');
    } finally {
      setGenerating(false);
    }
  };

  if (loadingOptions) {
    return (
      <div className="flex items-center justify-center min-h-[80vh]">
        <div className="relative">
          <div className="w-16 h-16 rounded-full border-4 border-white/5 border-t-purple-500 animate-spin"></div>
          <Sparkles className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-purple-500 animate-pulse" size={20} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-80px)] pt-20 pb-8 px-4 md:px-8 max-w-[1600px] mx-auto animate-fadeIn">
      {/* 顶部标题区 */}
      <div className="flex items-center gap-3 mb-8 pl-1">
        <div className="p-2 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-xl border border-white/10">
          <Wand2 className="text-purple-400" size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">AI 创意工坊</h1>
          <p className="text-sm text-gray-400 mt-0.5">将您的想象力转化为视觉杰作</p>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-6 h-auto lg:h-[calc(100vh-220px)] min-h-[600px]">
        
        {/* 左侧：控制面板 */}
        <div className="w-full lg:w-[420px] flex-shrink-0 flex flex-col gap-4">
          
          {/* Prompt 输入卡片 */}
          <div className="bg-[#0A0A0A]/80 backdrop-blur-xl border border-white/10 rounded-2xl p-5 flex-shrink-0 shadow-xl">
            <div className="flex justify-between items-center mb-3">
              <label className="text-sm font-semibold text-gray-200 flex items-center gap-2">
                <Sparkles size={14} className="text-purple-400" />
                画面描述
              </label>
              <span className="text-xs text-gray-500">越详细越精彩</span>
            </div>
            <div className="relative group">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="描述您想生成的画面... 例如：赛博朋克风格的未来城市，霓虹灯光，雨夜，超高清细节"
                className="w-full h-32 px-4 py-3 bg-white/5 border border-white/5 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:bg-white/10 focus:border-purple-500/30 focus:ring-1 focus:ring-purple-500/30 resize-none transition-all text-sm leading-relaxed"
              />
              <div className="absolute bottom-3 right-3 pointer-events-none">
                <Wand2 size={16} className={`text-purple-500 transition-opacity duration-300 ${prompt ? 'opacity-100' : 'opacity-0'}`} />
              </div>
            </div>
          </div>

          {/* 参数设置卡片 */}
          <div className="bg-[#0A0A0A]/80 backdrop-blur-xl border border-white/10 rounded-2xl p-5 flex-1 flex flex-col gap-6 shadow-xl overflow-y-auto custom-scrollbar">
            
            {/* 分辨率 */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm font-semibold text-gray-200 flex items-center gap-2">
                  <Maximize2 size={14} className="text-blue-400" />
                  分辨率
                </label>
                <span className="text-[10px] text-orange-400 px-2 py-0.5 bg-orange-500/10 rounded-full border border-orange-500/20">
                  {options?.resolutions.pricing}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {options?.resolutions.options.map((res) => (
                  <button
                    key={res}
                    onClick={() => setResolution(res)}
                    className={`relative py-3 rounded-xl border transition-all duration-200 group ${
                      resolution === res
                        ? 'bg-purple-500/10 border-purple-500/50 text-white shadow-[0_0_20px_rgba(168,85,247,0.15)]'
                        : 'bg-white/5 border-transparent text-gray-400 hover:bg-white/10 hover:border-white/10 hover:text-gray-200'
                    }`}
                  >
                    <div className="flex flex-col items-center gap-1">
                      <span className="text-sm font-bold">{res}</span>
                      <span className={`text-[10px] ${resolution === res ? 'text-purple-300' : 'text-gray-600 group-hover:text-gray-500'}`}>
                        {resolutionDescriptions[res]}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* 宽高比 */}
            <div className="space-y-3">
              <label className="text-sm font-semibold text-gray-200 flex items-center gap-2">
                <Ratio size={14} className="text-green-400" />
                画幅比例
              </label>
              <div className="grid grid-cols-5 gap-2">
                {options?.aspect_ratios.options.map((ratio) => (
                  <button
                    key={ratio}
                    onClick={() => setAspectRatio(ratio)}
                    className={`py-2 rounded-lg border transition-all duration-200 ${
                      aspectRatio === ratio
                        ? 'bg-purple-500/10 border-purple-500/50 text-white shadow-[0_0_15px_rgba(168,85,247,0.1)]'
                        : 'bg-white/5 border-transparent text-gray-400 hover:bg-white/10 hover:border-white/10 hover:text-gray-200'
                    }`}
                  >
                    <div className="flex flex-col items-center gap-0.5">
                      <span className="text-xs font-bold">{ratio}</span>
                      <span className={`text-[9px] transform scale-90 ${aspectRatio === ratio ? 'text-purple-300' : 'text-gray-600'}`}>
                        {aspectRatioDescriptions[ratio]}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-auto pt-4 space-y-3">
              {/* 错误提示 */}
              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-xs flex items-center justify-center gap-2 animate-fadeIn">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                  {error}
                </div>
              )}

              {/* 生成按钮 */}
              {!isLoggedIn ? (
                <button
                  onClick={handleLoginRequired}
                  className="w-full py-4 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-semibold rounded-xl transition-all flex items-center justify-center gap-2 group"
                >
                  <LogIn size={18} className="text-gray-400 group-hover:text-white transition-colors" />
                  登录后开始创作
                </button>
              ) : (
                <button
                  onClick={handleGenerate}
                  disabled={generating || !prompt}
                  className="w-full py-4 bg-gradient-to-r from-violet-600 to-fuchsia-600 hover:from-violet-500 hover:to-fuchsia-500 text-white font-bold rounded-xl shadow-lg shadow-purple-500/20 hover:shadow-purple-500/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 group relative overflow-hidden"
                >
                  <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20"></div>
                  <div className="relative flex items-center gap-2">
                    {generating ? (
                      <>
                        <Loader2 className="animate-spin" size={18} />
                        <span className="tracking-wide">AI 正在绘图...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles size={18} className="group-hover:rotate-12 transition-transform" />
                        <span className="tracking-wide">立即生成</span>
                      </>
                    )}
                  </div>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* 右侧：预览画布 */}
        <div className="flex-1 min-w-0 bg-[#0A0A0A]/50 backdrop-blur-sm border border-white/5 rounded-2xl relative overflow-hidden flex flex-col h-full">
          {/* 背景光效 */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-purple-500/5 blur-[120px] rounded-full pointer-events-none"></div>

          {/* 顶部工具栏 */}
          <div className="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-black/20">
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <ImageIcon size={16} />
              <span>预览画布</span>
            </div>
            {generatedImage && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-green-400 flex items-center gap-1.5 bg-green-500/10 px-2.5 py-1 rounded-full border border-green-500/20">
                  <CheckCircle2 size={12} />
                  生成完成
                </span>
              </div>
            )}
          </div>

          {/* 画布区域 */}
          <div className="flex-1 relative flex items-center justify-center p-8 overflow-hidden">
            {generating ? (
              <div className="text-center space-y-8 relative z-10">
                <div className="relative">
                  <div className="w-32 h-32 rounded-full border-2 border-white/5 border-t-purple-500 animate-spin mx-auto"></div>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-24 h-24 rounded-full bg-purple-500/10 animate-pulse flex items-center justify-center">
                      <Sparkles className="text-purple-400" size={32} />
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  <h3 className="text-2xl font-bold text-white tracking-tight">AI 正在构思画面...</h3>
                  <p className="text-gray-400">正在渲染光影与细节，请稍候</p>
                </div>
              </div>
            ) : generatedImage ? (
              <div className="relative w-full h-full flex items-center justify-center animate-fadeIn group">
                <img 
                  src={generatedImage} 
                  alt="Generated Result" 
                  className="max-w-full max-h-full object-contain rounded-lg shadow-2xl ring-1 ring-white/10"
                />
                
                {/* 悬浮下载按钮 */}
                <div className="absolute bottom-8 left-1/2 -translate-x-1/2 translate-y-4 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-300 z-20">
                  <a
                    href={generatedImage}
                    download={`generated-${Date.now()}.png`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-6 py-3 bg-white text-black font-bold rounded-full hover:bg-gray-200 shadow-[0_10px_30px_rgba(0,0,0,0.5)] transition-transform hover:scale-105"
                  >
                    <Download size={18} />
                    保存高清原图
                  </a>
                </div>
              </div>
            ) : (
              <div className="text-center space-y-6 max-w-sm mx-auto opacity-40 hover:opacity-60 transition-opacity duration-500">
                <div className="w-40 h-40 rounded-[2rem] bg-white/5 border-2 border-dashed border-white/10 flex items-center justify-center mx-auto">
                  <ImageIcon className="text-white/20" size={64} />
                </div>
                <div className="space-y-2">
                  <p className="text-white text-lg font-medium">画布准备就绪</p>
                  <p className="text-sm text-gray-400">
                    配置左侧参数并点击生成<br/>您的创意将在此呈现
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImageGeneration;
