import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { chatWithCoze } from '../src/services/coze';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

const CozeChat: React.FC = () => {
    const [messages, setMessages] = useState<Message[]>([
        { role: 'assistant', content: '您好！我是您的省钱大王助手。请问想买点什么？我可以帮您比价、找券、推荐好物。' }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        const userMessage = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setIsLoading(true);

        try {
            const history = messages.map(msg => ({
                role: msg.role,
                content: msg.content,
                content_type: 'text'
            }));

            let botMessageContent = '';
            setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

            await chatWithCoze(
                [...history, { role: 'user', content: userMessage, content_type: 'text' }],
                (chunk) => {
                    botMessageContent += chunk;
                    setMessages(prev => {
                        const newMessages = [...prev];
                        newMessages[newMessages.length - 1].content = botMessageContent;
                        return newMessages;
                    });
                },
                () => {
                    setIsLoading(false);
                },
                (error) => {
                    console.error('Chat error:', error);
                    setIsLoading(false);
                    setMessages(prev => [...prev, { role: 'assistant', content: '抱歉，我现在遇到了一些问题，请稍后再试。' }]);
                }
            );
        } catch (error) {
            console.error('Failed to send message:', error);
            setIsLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="flex flex-col h-full bg-[#1a1a1a] text-white rounded-2xl overflow-hidden shadow-2xl border border-white/10">
            {/* Messages Area */}
            <div className="flex-grow overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-orange-500/20 scrollbar-track-transparent">
                {messages.map((msg, index) => (
                    <div
                        key={index}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-[85%] rounded-2xl px-5 py-3.5 leading-relaxed shadow-md ${msg.role === 'user'
                                    ? 'bg-orange-600 text-white rounded-tr-none'
                                    : 'bg-white/10 text-gray-200 rounded-tl-none border border-white/5'
                                }`}
                        >
                            {msg.role === 'assistant' ? (
                                <div className="prose prose-invert prose-p:my-1 prose-pre:bg-black/30 prose-code:text-orange-300 max-w-none text-sm">
                                    <ReactMarkdown
                                        remarkPlugins={[remarkGfm]}
                                        components={{
                                            table: ({ node, ...props }) => <div className="overflow-x-auto my-2 rounded-lg border border-white/10"><table className="min-w-full divide-y divide-white/10 bg-white/5" {...props} /></div>,
                                            thead: ({ node, ...props }) => <thead className="bg-white/10" {...props} />,
                                            th: ({ node, ...props }) => <th className="px-3 py-2 text-left text-xs font-medium text-orange-400 uppercase tracking-wider border-b border-white/10" {...props} />,
                                            td: ({ node, ...props }) => <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-300 border-b border-white/5" {...props} />,
                                        }}
                                    >
                                        {msg.content}
                                    </ReactMarkdown>
                                </div>
                            ) : (
                                msg.content
                            )}
                        </div>
                    </div>
                ))}
                {isLoading && (
                    <div className="flex justify-start animate-pulse">
                        <div className="bg-white/10 rounded-2xl rounded-tl-none px-5 py-3.5 border border-white/5">
                            <div className="flex gap-1.5">
                                <div className="w-2 h-2 bg-orange-500/50 rounded-full animate-bounce"></div>
                                <div className="w-2 h-2 bg-orange-500/50 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                                <div className="w-2 h-2 bg-orange-500/50 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="p-3 md:p-4 bg-[#111] border-t border-white/10">
                <div className="relative">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyPress}
                        placeholder="输入您想购买的商品..."
                        rows={1}
                        className="w-full bg-white/5 text-white text-base md:text-sm rounded-xl pl-4 pr-12 py-3.5 focus:outline-none focus:ring-1 focus:ring-orange-500/50 resize-none overflow-hidden placeholder-gray-500 border border-white/5 transition-all focus:bg-white/10"
                        style={{ minHeight: '52px' }}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || isLoading}
                        className="absolute right-2 bottom-2 p-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6 md:w-5 md:h-5">
                            <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
                        </svg>
                    </button>
                </div>
                <div className="text-center text-xs text-gray-600 mt-2">
                    AI 生成内容仅供参考
                </div>
            </div>
        </div>
    );
};

export default CozeChat;
