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

interface ChatLayoutProps {
  title: string;
  botId?: string;
  initialMessage?: string;
  placeholder?: string;
}

const ChatLayout: React.FC<ChatLayoutProps> = ({ title, botId, initialMessage, placeholder }) => {
  const navigate = useNavigate();
  return (
    <div className="flex-grow flex flex-col gap-4 animate-fadeIn h-[calc(100vh-120px)] md:h-auto">
      <div className="flex justify-between items-center mb-1 md:mb-2 px-2">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <span className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></span>
          {title}
        </h2>
        <button
          onClick={() => navigate('/')}
          className="text-gray-400 hover:text-white transition-colors text-sm underline align-middle"
        >
          返回首页
        </button>
      </div>

      <div className="flex-grow glass-morphism rounded-xl md:rounded-2xl overflow-hidden min-h-0 relative">
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
