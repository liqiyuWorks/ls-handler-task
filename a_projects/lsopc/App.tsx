import React from 'react';
import { BrowserRouter, Routes, Route, useNavigate, Navigate } from 'react-router-dom';
import Header from './components/Header';
import Footer from './components/Footer';
import Hero from './components/Hero';
import CozeChat from './components/CozeChat';
import WeChatWidget from './components/WeChatWidget';
import KnowledgeBaseManager from './components/KnowledgeBaseManager';
import PersonalCenter from './components/PersonalCenter';
import ImageGeneration from './components/ImageGeneration';
import VideoGeneration from './components/VideoGeneration';
import PromptEngineering from './components/PromptEngineering';
import VideoCourses from './components/VideoCourses';

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
  quickSuggestions?: string[];
}

const ChatLayout: React.FC<ChatLayoutProps> = ({ title, botId, initialMessage, placeholder, quickSuggestions }) => {
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
          <p className="text-[10px] md:text-xs text-gray-500 font-medium pl-5">
            已就绪，随时为您服务
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
          quickSuggestions={quickSuggestions}
        />
      </div>
    </div>
  );
};

const SavingsChatPage: React.FC = () => {
  return (
    <ChatLayout
      title="省钱大王 · 随时帮您"
      initialMessage="嗨，我是您的省钱小助手～\n\n想买什么直接说，或者**粘贴商品链接**给我，我帮您比全网低价、找隐藏优惠券，能省一点是一点。"
      placeholder="说说想买啥，或贴个链接都行～"
      quickSuggestions={['粘贴商品链接帮我比价', '推荐今日好价']}
    />
  );
};

const FinanceChatPage: React.FC = () => {
  return (
    <ChatLayout
      title="财报分析 · 随时帮您"
      botId={APP_CONFIG.COZE_BOT_ID_FINANCE}
      initialMessage="您好呀，我是您的财报小助手～\n\n您可以**上传或粘贴财报数据**，或直接告诉我**公司名称**，我来帮您解读经营状况和风险要点。"
      placeholder="输入公司名或粘贴财报内容..."
      quickSuggestions={['输入公司名称查询', '粘贴财报数据解读']}
    />
  );
};

const ArticleCoverChatPage: React.FC = () => {
  return (
    <ChatLayout
      title="封面助手 · 随时帮您"
      botId={APP_CONFIG.COZE_BOT_ID_ARTICLE_COVER}
      initialMessage="嗨，我是您的封面小助手～\n\n发我**文章主题或摘录一段文字**，我帮您生成一张好看又贴题的封面图，直接可用。"
      placeholder="输入文章主题或摘录一段文字..."
      quickSuggestions={['根据文章主题生成封面', '摘录一段文字生成封面']}
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
            <Route path="/image-generation" element={<ImageGeneration />} />
            <Route path="/video-generation" element={<VideoGeneration />} />
            <Route path="/savings-agent" element={<SavingsChatPage />} />
            <Route path="/finance-agent" element={<FinanceChatPage />} />
            <Route path="/article-cover-agent" element={<ArticleCoverChatPage />} />
            <Route path="/profile" element={<PersonalCenter />} />
            <Route path="/prompt-engineering" element={<PromptEngineering />} />
            <Route path="/video-courses" element={<VideoCourses />} />
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
