import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { APP_CONFIG } from '../constants';
import { MonitorPlay, Database, Home as HomeIcon, Menu, X, User, LogOut, Image as ImageIcon } from 'lucide-react';
import AuthModal from './AuthModal';
import { getCurrentUser, clearAuth, isAuthenticated } from '../services/auth';

const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [currentUser, setCurrentUser] = useState<string | null>(null);
  const [showUserMenu, setShowUserMenu] = useState(false);

  // 检查登录状态
  useEffect(() => {
    if (isAuthenticated()) {
      const user = getCurrentUser();
      if (user && user.username) {
        setCurrentUser(user.username);
      }
    }
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

  const handleAuthSuccess = (username: string) => {
    setCurrentUser(username);
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
        <nav className="hidden md:flex items-center gap-1 bg-white/5 p-1.5 rounded-full border border-white/5 backdrop-blur-sm">
          <button
            onClick={() => navigate('/')}
            className={`flex items-center gap-2 px-5 py-2 rounded-full text-sm font-medium transition-all duration-300 ${isActive('/')
              ? 'bg-white/10 text-white shadow-sm ring-1 ring-white/5'
              : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
          >
            <HomeIcon size={16} className={isActive('/') ? 'text-orange-400' : ''} />
            首页
          </button>

          <button
            onClick={() => navigate('/knowledge-base')}
            className={`flex items-center gap-2 px-5 py-2 rounded-full text-sm font-medium transition-all duration-300 ${isActive('/knowledge-base')
              ? 'bg-white/10 text-white shadow-sm ring-1 ring-white/5'
              : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
          >
            <Database size={16} className={isActive('/knowledge-base') ? 'text-purple-400' : ''} />
            知识库
          </button>

          <button
            onClick={() => navigate('/image-generation')}
            className={`flex items-center gap-2 px-5 py-2 rounded-full text-sm font-medium transition-all duration-300 ${isActive('/image-generation')
              ? 'bg-white/10 text-white shadow-sm ring-1 ring-white/5'
              : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
          >
            <ImageIcon size={16} className={isActive('/image-generation') ? 'text-pink-400' : ''} />
            图片生成
          </button>

          <a
            href="/overview.html"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-5 py-2 rounded-full text-sm font-medium text-gray-400 hover:text-white hover:bg-white/5 transition-all duration-300"
          >
            <MonitorPlay size={16} />
            演示
          </a>
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
                <div className="absolute right-0 top-full mt-2 w-40 bg-gray-900 border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50 animate-fadeIn">
                  <div className="p-2 border-b border-white/5 text-xs text-gray-500 text-center">
                    账号管理
                  </div>
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

          <button
            onClick={() => { navigate('/knowledge-base'); setIsMenuOpen(false); }}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all ${isActive('/knowledge-base')
                ? 'bg-white/10 text-white'
                : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
          >
            <Database size={20} className={isActive('/knowledge-base') ? 'text-purple-400' : ''} />
            知识库
          </button>

          <button
            onClick={() => { navigate('/image-generation'); setIsMenuOpen(false); }}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all ${isActive('/image-generation')
                ? 'bg-white/10 text-white'
                : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
          >
            <ImageIcon size={20} className={isActive('/image-generation') ? 'text-pink-400' : ''} />
            图片生成
          </button>

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
