import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate, useLocation } from 'react-router-dom';
import { APP_CONFIG } from '../constants';
import { MonitorPlay, Database, Home as HomeIcon, Menu, X, User, LogOut, Image as ImageIcon, Video, Settings, Sparkles, ChevronDown, Layers, LayoutGrid, Compass, BookOpen } from 'lucide-react';
import AuthModal from './AuthModal';
import { getCurrentUser, clearAuth, isAuthenticated } from '../services/auth';

const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<string | null>(null);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showProMenu, setShowProMenu] = useState(false);
  const [showExploreMenu, setShowExploreMenu] = useState(false);
  const [showTutorialMenu, setShowTutorialMenu] = useState(false);
  const [showVideoModal, setShowVideoModal] = useState(false);

  const videoUrl = "https://weixin.qq.com/sph/AOQouN7yb";
  const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(videoUrl)}`;

  const refreshDisplayName = () => {
    if (!isAuthenticated()) {
      setCurrentUser(null);
      return;
    }
    const user = getCurrentUser();
    if (user) setCurrentUser(user.nickname || user.username || '');
  };

  useEffect(() => {
    refreshDisplayName();
  }, []);

  useEffect(() => {
    window.addEventListener('storage', refreshDisplayName);
    window.addEventListener('authStateChanged', refreshDisplayName);
    return () => {
      window.removeEventListener('storage', refreshDisplayName);
      window.removeEventListener('authStateChanged', refreshDisplayName);
    };
  }, []);

  // 监听全局登录请求事件
  useEffect(() => {
    const handleOpenAuthModal = () => {
      setIsAuthModalOpen(true);
    };

    window.addEventListener('openAuthModal', handleOpenAuthModal);
    return () => {
      window.removeEventListener('openAuthModal', handleOpenAuthModal);
    };
  }, []);

  const handleAuthSuccess = (displayName: string) => {
    setCurrentUser(displayName);
  };

  const handleLogout = () => {
    clearAuth();
    setCurrentUser(null);
    setShowUserMenu(false);
    navigate('/'); // 登出后返回首页
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md bg-black/50 border-b border-white/5 transition-all duration-300">
      <div className="max-w-7xl mx-auto px-6 h-20 flex justify-between items-center">
        {/* Logo Area */}
        <div
          className="flex items-center gap-3 cursor-pointer group"
          onClick={() => navigate('/')}
        >
          <div className="relative">
            <div className="absolute -inset-1 bg-gradient-to-r from-orange-600 to-yellow-600 rounded-lg opacity-0 group-hover:opacity-50 transition duration-500 blur-sm"></div>
            <img
              src="/avatar.jpg"
              alt="Li Sheng Avatar"
              className="relative w-10 h-10 rounded-lg object-cover border border-white/10 shadow-lg"
            />
          </div>
          <div className="font-bold text-lg tracking-tight text-white/90 group-hover:text-white transition-colors">
            {APP_CONFIG.COMPANY_NAME}
          </div>
        </div>

        {/* Navigation */}
        <nav className="hidden md:flex items-center gap-2 bg-white/5 px-3 py-1.5 rounded-full border border-white/10 backdrop-blur-md">
          <button
            onClick={() => navigate('/')}
            className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${isActive('/')
              ? 'bg-white/10 text-white shadow-sm'
              : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
          >
            <HomeIcon size={16} className={isActive('/') ? 'text-orange-400' : ''} />
            首页
          </button>

          {/* Tutorial Dropdown Menu */}
          <div
            className="relative"
            onMouseEnter={() => setShowTutorialMenu(true)}
            onMouseLeave={() => setShowTutorialMenu(false)}
          >
            <button
              onClick={() => setShowTutorialMenu(!showTutorialMenu)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${showTutorialMenu
                ? 'bg-white/10 text-white shadow-sm'
                : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
            >
              <BookOpen size={16} className={showTutorialMenu ? 'text-purple-400' : ''} />
              教程
              <ChevronDown size={14} className={`transition-transform duration-300 ${showTutorialMenu ? 'rotate-180' : ''} ${showTutorialMenu ? 'text-purple-200' : 'text-gray-500'}`} />
            </button>

            {/* Tutorial Dropdown Content */}
            {showTutorialMenu && (
              <div className="absolute top-full left-0 mt-2 w-60 bg-[#111] rounded-2xl shadow-2xl overflow-hidden z-50 border border-white/10 py-2 animate-fadeIn">
                <div className="px-5 py-3 border-b border-white/5">
                  <span className="font-bold text-white text-sm">进阶实战指南</span>
                </div>

                <div className="p-2 space-y-0.5">
                  <button
                    onClick={() => { navigate('/prompt-engineering'); setShowTutorialMenu(false); }}
                    className="w-full flex items-start gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors text-left group"
                  >
                    <div className="mt-0.5 text-gray-400 group-hover:text-purple-400 transition-colors">
                      <Layers size={18} />
                    </div>
                    <div>
                      <div className="font-medium text-white text-sm mb-0.5 group-hover:text-purple-300 transition-colors">提示词工程</div>
                      <div className="text-[11px] text-gray-500 tracking-wide">掌握与 AI 对话的核心技术</div>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      if (window.innerWidth < 768) {
                        window.open(videoUrl, '_blank');
                      } else {
                        setShowVideoModal(true);
                      }
                      setShowTutorialMenu(false);
                    }}
                    className="w-full flex items-start gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors text-left group"
                  >
                    <div className="mt-0.5 text-gray-400 group-hover:text-red-400 transition-colors">
                      <Video size={18} />
                    </div>
                    <div>
                      <div className="font-medium text-white text-sm mb-0.5 group-hover:text-red-300 transition-colors">自研 Agent：研报自动化</div>
                      <div className="text-[11px] text-gray-500 tracking-wide">打通研报自动化的“最后一公里”</div>
                    </div>
                  </button>
                </div>
              </div>
            )}
          </div>
          <div
            className="relative"
            onMouseEnter={() => setShowExploreMenu(true)}
            onMouseLeave={() => setShowExploreMenu(false)}
          >
            <button
              onClick={() => setShowExploreMenu(!showExploreMenu)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${showExploreMenu || isActive('/knowledge-base')
                ? 'bg-white/10 text-white shadow-sm'
                : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
            >
              <Compass size={16} className={showExploreMenu || isActive('/knowledge-base') ? 'text-blue-400' : ''} />
              探索
              <ChevronDown size={14} className={`transition-transform duration-300 ${showExploreMenu ? 'rotate-180' : ''} ${showExploreMenu || isActive('/knowledge-base') ? 'text-blue-200' : 'text-gray-500'}`} />
            </button>

            {/* Explore Dropdown Content */}
            {showExploreMenu && (
              <div className="absolute top-full left-0 mt-2 w-64 bg-[#111] rounded-2xl shadow-2xl overflow-hidden z-50 border border-white/10 py-2 animate-fadeIn">

                <div className="px-5 py-3 border-b border-white/5">
                  <span className="font-bold text-white text-sm">发现更多可能</span>
                </div>

                <div className="p-2 space-y-0.5">
                  <a
                    href="/overview.html"
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => setShowExploreMenu(false)}
                    className="w-full flex items-start gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors text-left group"
                  >
                    <div className="mt-0.5 text-gray-400 group-hover:text-blue-400 transition-colors">
                      <MonitorPlay size={18} />
                    </div>
                    <div>
                      <div className="font-medium text-white text-sm mb-0.5 group-hover:text-blue-300 transition-colors">演示体验</div>
                      <div className="text-[11px] text-gray-500 tracking-wide">全方位了解产品能力</div>
                    </div>
                  </a>

                  <button
                    onClick={() => { navigate('/knowledge-base'); setShowExploreMenu(false); }}
                    className="w-full flex items-start gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors text-left group"
                  >
                    <div className="mt-0.5 text-gray-400 group-hover:text-purple-400 transition-colors">
                      <BookOpen size={18} />
                    </div>
                    <div>
                      <div className="font-medium text-white text-sm mb-0.5 group-hover:text-purple-300 transition-colors">知识库</div>
                      <div className="text-[11px] text-gray-500 tracking-wide">沉淀行业经验与最佳实践</div>
                    </div>
                  </button>

                  <button
                    onClick={() => {
                      const appsSection = document.getElementById('apps-resources');
                      if (appsSection) appsSection.scrollIntoView({ behavior: 'smooth' });
                      setShowExploreMenu(false);
                    }}
                    className="w-full flex items-start gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors text-left group"
                  >
                    <div className="mt-0.5 text-gray-400 group-hover:text-green-400 transition-colors">
                      <Database size={18} />
                    </div>
                    <div>
                      <div className="font-medium text-white text-sm mb-0.5 group-hover:text-green-300 transition-colors">智能应用</div>
                      <div className="text-[11px] text-gray-500 tracking-wide">探索未来赛道与实用插件</div>
                    </div>
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="w-px h-4 bg-white/10 mx-1"></div>

          {/* Pro Dropdown Menu */}
          <div
            className="relative"
            onMouseEnter={() => setShowProMenu(true)}
            onMouseLeave={() => setShowProMenu(false)}
          >
            <button
              onClick={() => setShowProMenu(!showProMenu)}
              className={`flex items-center gap-1.5 px-5 py-2 rounded-full text-sm font-bold transition-all duration-300 shadow-[0_0_15px_rgba(251,191,36,0.15)] border border-amber-500/30 ${showProMenu || isActive('/image-generation') || isActive('/video-generation')
                ? 'bg-gradient-to-r from-amber-100 to-amber-50 text-amber-900 border-amber-300 shadow-[0_0_20px_rgba(251,191,36,0.3)]'
                : 'bg-amber-900/20 text-amber-400 hover:bg-amber-500/20 hover:text-amber-300'
                }`}
            >
              <Sparkles size={16} className={showProMenu || isActive('/image-generation') || isActive('/video-generation') ? 'text-amber-600' : 'text-amber-400'} />
              Pro
              <ChevronDown size={14} className={`transition-transform duration-300 ${showProMenu ? 'rotate-180' : ''} ${showProMenu || isActive('/image-generation') || isActive('/video-generation') ? 'text-amber-700' : 'text-amber-500/70'}`} />
            </button>

            {/* Dropdown Content */}
            {showProMenu && (
              <div className="absolute top-full right-0 md:left-1/2 md:-translate-x-1/2 mt-2 w-72 bg-white rounded-2xl shadow-2xl overflow-hidden z-50 animate-fadeIn border border-gray-100 py-2">

                <div className="px-5 py-3 flex items-center gap-2 border-b border-gray-100">
                  <span className="font-bold text-gray-900 text-sm">自研视觉创作引擎</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-amber-500 text-white leading-none uppercase">进阶创作</span>
                </div>

                <div className="p-2 space-y-1">
                  <button
                    onClick={() => { navigate('/image-generation'); setShowProMenu(false); }}
                    className="w-full flex items-start gap-4 p-3 rounded-xl hover:bg-gray-50 transition-colors text-left group"
                  >
                    <div className="mt-0.5 text-gray-400 group-hover:text-amber-500 transition-colors">
                      <Layers size={20} />
                    </div>
                    <div>
                      <div className="font-bold text-gray-900 text-sm mb-0.5 group-hover:text-amber-600 transition-colors">AI 创意工坊</div>
                      <div className="text-xs text-gray-500 tracking-tight">自研顶尖底图图像生成与编辑</div>
                    </div>
                  </button>

                  <button
                    onClick={() => { navigate('/video-generation'); setShowProMenu(false); }}
                    className="w-full flex items-start gap-4 p-3 rounded-xl hover:bg-gray-50 transition-colors text-left group"
                  >
                    <div className="mt-0.5 text-gray-400 group-hover:text-amber-500 transition-colors">
                      <LayoutGrid size={20} />
                    </div>
                    <div>
                      <div className="font-bold text-gray-900 text-sm mb-0.5 group-hover:text-amber-600 transition-colors">AI 视频生成</div>
                      <div className="text-xs text-gray-500 tracking-tight">根据需求深度定制的影视级动态视觉</div>
                    </div>
                  </button>
                </div>

                <div className="p-2 border-t border-gray-100 border-dashed mt-1">
                  <button className="w-full flex items-start gap-4 p-3 rounded-xl hover:bg-amber-50 transition-colors text-left group">
                    <div className="mt-0.5 text-amber-500">
                      <Sparkles size={20} />
                    </div>
                    <div>
                      <div className="font-bold text-gray-900 text-sm mb-0.5 group-hover:text-amber-700 transition-colors">开通 Pro</div>
                      <div className="text-xs text-gray-500">解锁每日不限量生成及商业授权</div>
                    </div>
                  </button>
                </div>

              </div>
            )}
          </div>

        </nav>

        {/* User Auth Area - Desktop */}
        <div className="hidden md:flex items-center gap-3">
          {currentUser ? (
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-sm font-medium text-white transition-all"
              >
                <User size={16} className="text-orange-400" />
                {currentUser}
              </button>

              {/* User Dropdown Menu */}
              {showUserMenu && (
                <div className="absolute right-0 top-full mt-2 w-44 bg-gray-900 border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50 animate-fadeIn">
                  <button
                    onClick={() => { navigate('/profile'); setShowUserMenu(false); }}
                    className="w-full flex items-center gap-2 px-4 py-3 text-sm text-white hover:bg-white/5 transition-all text-left"
                  >
                    <Settings size={16} className="text-orange-400" />
                    个人中心
                  </button>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-4 py-3 text-sm text-red-400 hover:bg-white/5 transition-all"
                  >
                    <LogOut size={16} />
                    退出登录
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={() => setIsAuthModalOpen(true)}
              className="flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-orange-500 to-yellow-500 hover:from-orange-600 hover:to-yellow-600 rounded-full text-sm font-medium text-white shadow-lg shadow-orange-500/25 hover:shadow-orange-500/40 transition-all"
            >
              <User size={16} />
              登录 / 注册
            </button>
          )}
        </div>

        {/* Mobile menu trigger */}
        <div className="md:hidden">
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="p-2 text-gray-400 hover:text-white transition-colors"
          >
            {isMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Overlay */}
      {isMenuOpen && (
        <div className="absolute top-20 left-0 right-0 bg-black/95 backdrop-blur-xl border-b border-white/10 p-6 md:hidden animate-slideIn flex flex-col gap-4 shadow-2xl h-[calc(100vh-80px)]">
          <button
            onClick={() => { navigate('/'); setIsMenuOpen(false); }}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all ${isActive('/')
              ? 'bg-white/10 text-white'
              : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
          >
            <HomeIcon size={20} className={isActive('/') ? 'text-orange-400' : ''} />
            首页
          </button>

          <div className="mx-4 mt-2 px-2">
            <div className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1">
              <Compass size={12} />
              探索
            </div>
            <div className="flex flex-col gap-1">
              <a
                href="/overview.html"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 px-4 py-2.5 rounded-xl font-medium text-gray-400 hover:text-white hover:bg-white/5 transition-all text-sm"
              >
                <MonitorPlay size={18} />
                演示体验
              </a>

              <button
                onClick={() => { navigate('/knowledge-base'); setIsMenuOpen(false); }}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-xl font-medium transition-all text-sm ${isActive('/knowledge-base')
                  ? 'bg-white/10 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
              >
                <BookOpen size={18} className={isActive('/knowledge-base') ? 'text-purple-400' : ''} />
                知识库
              </button>
            </div>
          </div>

          <div className="mx-4 mt-2 px-2">
            <div className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-1">
              <BookOpen size={12} />
              教程
            </div>
            <div className="flex flex-col gap-1">
              <button
                onClick={() => { navigate('/prompt-engineering'); setIsMenuOpen(false); }}
                className="flex items-center gap-3 px-4 py-2.5 rounded-xl font-medium text-gray-400 hover:text-white hover:bg-white/5 transition-all text-sm w-full text-left"
              >
                <Layers size={18} />
                提示词工程
              </button>
              <button
                onClick={() => { window.open(videoUrl, '_blank'); setIsMenuOpen(false); }}
                className="flex items-center gap-3 px-4 py-2.5 rounded-xl font-medium text-gray-400 hover:text-white hover:bg-white/5 transition-all text-sm w-full text-left"
              >
                <Video size={18} />
                自研 Agent：研报自动化
              </button>
            </div>
          </div>

          <div className="mx-4 mt-2 mb-1 px-2">
            <div className="text-xs font-bold text-amber-500/70 uppercase tracking-wider mb-2 flex items-center gap-1">
              <Sparkles size={12} />
              Pro 视觉生成
            </div>
            <div className="flex flex-col gap-2">
              <button
                onClick={() => { navigate('/image-generation'); setIsMenuOpen(false); }}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all ${isActive('/image-generation')
                  ? 'bg-gradient-to-r from-amber-500/20 to-transparent text-amber-400 border border-amber-500/20'
                  : 'text-amber-500/70 hover:text-amber-400 hover:bg-amber-500/10'
                  }`}
              >
                <Layers size={20} />
                AI 创意工坊
              </button>

              <button
                onClick={() => { navigate('/video-generation'); setIsMenuOpen(false); }}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all ${isActive('/video-generation')
                  ? 'bg-gradient-to-r from-amber-500/20 to-transparent text-amber-400 border border-amber-500/20'
                  : 'text-amber-500/70 hover:text-amber-400 hover:bg-amber-500/10'
                  }`}
              >
                <LayoutGrid size={20} />
                AI 视频生成
              </button>
            </div>
          </div>

          <a
            href="/overview.html"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-gray-400 hover:text-white hover:bg-white/5 transition-all"
          >
            <MonitorPlay size={20} />
            演示模式
          </a>

          {/* Mobile Auth Button */}
          <div className="border-t border-white/10 pt-4 mt-auto pb-8">
            {currentUser ? (
              <div className="space-y-4">
                <div className="flex items-center gap-3 px-4 py-3 bg-white/5 rounded-xl text-white border border-white/5">
                  <div className="w-10 h-10 rounded-full bg-orange-500/20 flex items-center justify-center text-orange-400">
                    <User size={20} />
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">当前登录</div>
                    <div className="font-medium">{currentUser}</div>
                  </div>
                </div>
                <button
                  onClick={() => { navigate('/profile'); setIsMenuOpen(false); }}
                  className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl font-medium text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-all"
                >
                  <Settings size={20} />
                  个人中心
                </button>
                <button
                  onClick={() => { handleLogout(); setIsMenuOpen(false); }}
                  className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl font-medium text-red-400 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 transition-all"
                >
                  <LogOut size={20} />
                  退出登录
                </button>
              </div>
            ) : (
              <button
                onClick={() => { setIsAuthModalOpen(true); setIsMenuOpen(false); }}
                className="w-full flex items-center justify-center gap-2 px-4 py-4 bg-gradient-to-r from-orange-500 to-yellow-500 rounded-xl font-bold text-white shadow-lg shadow-orange-500/20"
              >
                <User size={20} />
                登录 / 注册
              </button>
            )}
          </div>
        </div>
      )}

      {/* Video Channel Modal - Rendered via Portal to escape header constraints */}
      {showVideoModal && createPortal(
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 animate-fadeIn">
          <div className="absolute inset-0 bg-black/90 backdrop-blur-md" onClick={() => setShowVideoModal(false)}></div>
          <div className="relative w-full max-w-[360px] bg-[#0a0a0a] border border-white/10 rounded-[32px] overflow-hidden shadow-[0_0_50px_rgba(0,0,0,0.5)] animate-scaleIn">
            {/* Close Button - more prominent */}
            <button
              onClick={() => setShowVideoModal(false)}
              className="absolute top-6 right-6 p-2.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-all z-[60]"
            >
              <X size={22} />
            </button>

            <div className="p-10 flex flex-col items-center text-center">
              <div className="w-14 h-14 bg-red-500/10 rounded-2xl flex items-center justify-center mb-6">
                <Video size={28} className="text-red-500" />
              </div>

              <h3 className="text-xl font-bold text-white mb-2 tracking-tight">微信视频号 · 进阶实战</h3>
              <p className="text-gray-400 text-xs mb-8 leading-relaxed max-w-[240px]">
                作为投研人，带你通过实战演示打通研报自动化的“最后一公里”
              </p>

              <div className="relative p-5 bg-white rounded-3xl mb-8 group transition-all hover:shadow-[0_0_30px_rgba(255,255,255,0.1)]">
                <img
                  src={qrCodeUrl}
                  alt="WeChat Video Channel QR Code"
                  className="w-40 h-40"
                />
                <div className="absolute inset-0 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-white/60 backdrop-blur-[1px] rounded-3xl">
                  <div className="p-2 bg-black rounded-lg mb-2">
                    <User size={16} className="text-white" />
                  </div>
                  <p className="text-black font-extrabold text-xs">微信扫码观看</p>
                </div>
              </div>

              <div className="w-full space-y-3">
                <button
                  onClick={() => window.open(videoUrl, '_blank')}
                  className="w-full py-4 bg-white text-black font-bold rounded-2xl hover:bg-gray-100 transition-all flex items-center justify-center gap-2 text-sm"
                >
                  在网页浏览器打开
                  <MonitorPlay size={18} />
                </button>

                <p className="text-[10px] text-gray-500 font-medium">
                  推荐在移动端直接观看体验更佳
                </p>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthSuccess={handleAuthSuccess}
      />
    </header>
  );
};

export default Header;
