import React from 'react';
import { BrowserRouter, Routes, Route, useNavigate, Navigate } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import Hero from './components/Hero';
import CozeChat from './components/CozeChat';
import WeChatWidget from './components/WeChatWidget';
import KnowledgeBaseManager from './components/KnowledgeBaseManager';

const Home: React.FC = () => {
  const navigate = useNavigate();
  return (
    <div className="flex flex-col">
      <Hero onStartChat={() => navigate('/savings-agent')} />
    </div>
  );
};

import { APP_CONFIG } from './constants';
import { ArrowLeft, Home as HomeIcon, MessageSquare, Bot, User, Send, Zap } from 'lucide-react';

interface ChatLayoutProps {
  title: string;
  botId?: string;
  initialMessage?: string;
  placeholder?: string;
}

const ChatLayout: React.FC<ChatLayoutProps> = ({ title, botId, initialMessage, placeholder }) => {
  const navigate = useNavigate();
  return (
    <div className="flex-grow flex flex-col gap-3 md:gap-4 animate-fadeIn h-[calc(100dvh-100px)] md:h-[calc(100vh-140px)] pt-16 md:pt-20">
      <div className="flex justify-between items-center px-2 md:px-0">
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-2">
            <div className="relative flex items-center justify-center">
              <span className="w-2.5 h-2.5 bg-green-500 rounded-full animate-pulse"></span>
              <span className="absolute w-2.5 h-2.5 bg-green-500 rounded-full animate-ping opacity-75"></span>
            </div>
            <h2 className="text-lg md:text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
              {title}
            </h2>
          </div>
          <p className="text-[10px] md:text-xs text-gray-500 font-medium uppercase tracking-widest pl-5">
            System Online • Protocol Secure
          </p>
        </div>

        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 px-3 py-1.5 md:px-4 md:py-2 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 transition-all text-xs md:text-sm text-gray-400 hover:text-white group"
        >
          <ArrowLeft className="w-3.5 h-3.5 group-hover:-translate-x-0.5 transition-transform" />
          <span>返回首页</span>
        </button>
      </div>

      <div className="flex-grow glass-morphism rounded-2xl md:rounded-3xl overflow-hidden min-h-0 relative shadow-2xl border border-white/10 ring-1 ring-white/5">
        <CozeChat
          botId={botId}
          initialMessage={initialMessage}
          placeholder={placeholder}
        />
      </div>
    </div>
  );
};

const SavingsChatPage: React.FC = () => {
  return (
    <ChatLayout
      title="省钱助手正在待命"
      initialMessage="您好！我是您的省钱大王助手。请告诉我您想买什么，或者粘贴商品链接，我将为您寻找全网最低价和隐藏优惠券。"
      placeholder="输入商品名称或粘贴链接..."
    />
  );
};

const FinanceChatPage: React.FC = () => {
  return (
    <ChatLayout
      title="财报分析助手正在待命"
      botId={APP_CONFIG.COZE_BOT_ID_FINANCE}
      initialMessage="您好！我是您的财报分析助手。请上传或粘贴您想分析的财报数据，或者直接询问某家公司的财务状况。"
      placeholder="输入公司名称或粘贴财报数据..."
    />
  );
};

const ArticleCoverChatPage: React.FC = () => {
  return (
    <ChatLayout
      title="文章封面助手正在待命"
      botId={APP_CONFIG.COZE_BOT_ID_ARTICLE_COVER}
      initialMessage="您好！我是您的文章封面助手。请告诉我您的文章主题或从文章中摘录一段文字，我将为您生成一张精美的封面图。"
      placeholder="输入文章主题或关键词..."
    />
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
            <Route path="/knowledge-base" element={<KnowledgeBaseManager />} />
            <Route path="/savings-agent" element={<SavingsChatPage />} />
            <Route path="/finance-agent" element={<FinanceChatPage />} />
            <Route path="/article-cover-agent" element={<ArticleCoverChatPage />} />
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
