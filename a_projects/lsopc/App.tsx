import React from 'react';
import { BrowserRouter, Routes, Route, useNavigate, Navigate } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import Hero from './components/Hero';
import CozeChat from './components/CozeChat';
import WeChatWidget from './components/WeChatWidget';

const Home: React.FC = () => {
  const navigate = useNavigate();
  return (
    <div className="flex flex-col">
      <Hero onStartChat={() => navigate('/savings-agent')} />
      <div className="text-center pb-12">
        <a
          href="/overview.html"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 px-6 py-3 border border-white/10 rounded-full text-xs text-gray-400 hover:text-white hover:border-orange-500 hover:bg-white/5 transition-all duration-300 tracking-widest uppercase group"
        >
          <span className="w-2 h-2 rounded-full bg-orange-500/50 group-hover:bg-orange-500 transition-colors"></span>
          进入演示模式 (Presentation Mode)
        </a>
      </div>
    </div>
  );
};

const ChatPage: React.FC = () => {
  const navigate = useNavigate();
  return (
    <div className="flex-grow flex flex-col gap-4 animate-fadeIn h-[calc(100vh-120px)] md:h-auto">
      <div className="flex justify-between items-center mb-1 md:mb-2 px-2">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <span className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></span>
          省钱助手正在待命
        </h2>
        <button
          onClick={() => navigate('/')}
          className="text-gray-400 hover:text-white transition-colors text-sm underline align-middle"
        >
          返回首页
        </button>
      </div>

      <div className="flex-grow glass-morphism rounded-xl md:rounded-2xl overflow-hidden min-h-0 relative">
        <CozeChat />
      </div>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col text-white bg-[#050505]">
        <Header />

        <main className="flex-grow flex flex-col container mx-auto px-2 md:px-4 py-4 md:py-6">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/savings-agent" element={<ChatPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        <Footer />
        {/* Floating WeChat Widget - Visible on all pages */}
        <WeChatWidget />
      </div>
    </BrowserRouter>
  );
};

export default App;
