
import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { APP_CONFIG } from '../constants';
import { MonitorPlay, Database, Home as HomeIcon, Menu, X } from 'lucide-react';

const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);

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
        <div className="absolute top-20 left-0 right-0 bg-black/95 backdrop-blur-xl border-b border-white/10 p-6 md:hidden animate-slideIn flex flex-col gap-4 shadow-2xl">
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

          <a
            href="/overview.html"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 px-4 py-3 rounded-xl font-medium text-gray-400 hover:text-white hover:bg-white/5 transition-all"
          >
            <MonitorPlay size={20} />
            演示模式
          </a>
        </div>
      )}
    </header>
  );
};

export default Header;
