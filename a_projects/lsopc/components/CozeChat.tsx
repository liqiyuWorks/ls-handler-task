import React, { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { chatWithCoze } from '../services/coze';
import { Bot, User, Send, Zap, Sparkles, CornerDownLeft } from 'lucide-react';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

interface CozeChatProps {
    botId?: string;
    initialMessage?: string;
    placeholder?: string;
}

const CozeChat: React.FC<CozeChatProps> = ({
    botId,
    initialMessage = '您好！我是您的省钱大王助手。请问想买点什么？我可以帮您比价、找券、推荐好物。',
    placeholder = '输入您想购买的商品...'
}) => {
    const [messages, setMessages] = useState<Message[]>([
        { role: 'assistant', content: initialMessage }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Handle auto-resize textarea
    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
        }
    }, [input]);

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
                },
                botId
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
        <div className="flex flex-col h-full bg-[#0a0a0a]/40 backdrop-blur-xl text-white">
            {/* Messages Area */}
            <div className="flex-grow overflow-y-auto px-3 md:px-6 py-6 space-y-8 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
                {messages.map((msg, index) => (
                    <div
                        key={index}
                        className={`flex gap-3 md:gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                    >
                        {/* Avatar */}
                        <div className={`flex-shrink-0 w-8 h-8 md:w-10 md:h-10 rounded-full flex items-center justify-center border ${msg.role === 'user'
                            ? 'bg-orange-500/20 border-orange-500/30 text-orange-400'
                            : 'bg-white/5 border-white/10 text-gray-400'
                            }`}>
                            {msg.role === 'user' ? <User className="w-4 h-4 md:w-5 md:h-5 text-current" /> : <Bot className="w-4 h-4 md:w-5 md:h-5 text-current" />}
                        </div>

                        {/* Message Bubble */}
                        <div className={`flex flex-col max-w-[85%] md:max-w-[75%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                            <div
                                className={`rounded-2xl px-4 py-3 md:px-5 md:py-3.5 leading-relaxed shadow-lg relative ${msg.role === 'user'
                                    ? 'bg-gradient-to-br from-orange-500 to-orange-600 text-white rounded-tr-none'
                                    : 'bg-white/5 text-gray-200 rounded-tl-none border border-white/10 backdrop-blur-md'
                                    }`}
                            >
                                {msg.role === 'assistant' ? (
                                    <div className="prose prose-invert prose-p:my-1 prose-pre:bg-black/40 prose-pre:border prose-pre:border-white/10 prose-code:text-orange-300 prose-code:bg-orange-500/10 prose-code:px-1 prose-code:rounded max-w-none text-sm md:text-[15px]">
                                        <ReactMarkdown
                                            remarkPlugins={[remarkGfm]}
                                            components={{
                                                table: ({ node, ...props }) => <div className="overflow-x-auto my-3 rounded-xl border border-white/10 shadow-inner"><table className="min-w-full divide-y divide-white/10 bg-white/5" {...props} /></div>,
                                                thead: ({ node, ...props }) => <thead className="bg-white/10" {...props} />,
                                                th: ({ node, ...props }) => <th className="px-4 py-3 text-left text-xs font-bold text-orange-400 uppercase tracking-widest border-b border-white/10" {...props} />,
                                                td: ({ node, ...props }) => <td className="px-4 py-3 text-sm text-gray-300 border-b border-white/5 font-medium" {...props} />,
                                                li: ({ node, ...props }) => <li className="marker:text-orange-500" {...props} />
                                            }}
                                        >
                                            {msg.content}
                                        </ReactMarkdown>
                                    </div>
                                ) : (
                                    <span className="text-sm md:text-[15px] whitespace-pre-wrap">{msg.content}</span>
                                )}
                            </div>

                            {/* Timestamp or Status (Optional) */}
                            <div className="mt-1.5 px-1 flex items-center gap-1.5 opacity-40 text-[10px] md:text-xs">
                                {msg.role === 'assistant' && <Sparkles className="w-3 h-3 text-orange-400" />}
                                <span>{msg.role === 'user' ? '已发送' : 'AI 助手'}</span>
                            </div>
                        </div>
                    </div>
                ))}

                {isLoading && (
                    <div className="flex gap-3 md:gap-4">
                        <div className="flex-shrink-0 w-8 h-8 md:w-10 md:h-10 rounded-full flex items-center justify-center bg-white/5 border border-white/10 text-gray-400 animate-pulse">
                            <Bot className="w-4 h-4 md:w-5 md:h-5" />
                        </div>
                        <div className="bg-white/5 rounded-2xl rounded-tl-none px-5 py-4 border border-white/10 backdrop-blur-md">
                            <div className="flex gap-2">
                                <div className="w-1.5 h-1.5 bg-orange-500/60 rounded-full animate-bounce"></div>
                                <div className="w-1.5 h-1.5 bg-orange-500/60 rounded-full animate-bounce [animation-delay:0.2s]"></div>
                                <div className="w-1.5 h-1.5 bg-orange-500/60 rounded-full animate-bounce [animation-delay:0.4s]"></div>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} className="h-4" />
            </div>

            {/* Input Area */}
            <div className="p-4 md:p-6 bg-gradient-to-t from-black to-transparent pt-8 relative">
                <div className="max-w-4xl mx-auto relative group">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-orange-500/20 to-orange-600/20 rounded-2xl blur opacity-0 group-focus-within:opacity-100 transition duration-500"></div>
                    <div className="relative">
                        <textarea
                            ref={textareaRef}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyPress}
                            placeholder={placeholder}
                            rows={1}
                            className="w-full bg-[#111]/80 backdrop-blur-xl text-white text-base md:text-[15px] rounded-2xl pl-5 pr-14 py-4 focus:outline-none focus:ring-1 focus:ring-orange-500/50 resize-none overflow-hidden placeholder-gray-600 border border-white/10 transition-all shadow-xl group-hover:border-white/20"
                            style={{ minHeight: '56px' }}
                        />
                        <div className="absolute right-3 bottom-3 flex items-center gap-2">
                            <button
                                type="button"
                                onMouseDown={(e) => e.preventDefault()}
                                onClick={handleSend}
                                disabled={!input.trim() || isLoading}
                                className={`p-2 rounded-xl transition-all shadow-lg active:scale-90 flex items-center justify-center ${!input.trim() || isLoading
                                    ? 'bg-white/5 text-gray-600'
                                    : 'bg-orange-500 text-white hover:bg-orange-400 hover:shadow-orange-500/20'
                                    }`}
                                aria-label="发送消息"
                            >
                                {isLoading ? (
                                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                ) : (
                                    <Send className="w-5 h-5" />
                                )}
                            </button>
                        </div>
                    </div>
                </div>

                <div className="flex justify-between items-center max-w-4xl mx-auto mt-3 px-2">
                    <div className="flex items-center gap-4 text-[10px] md:text-xs text-gray-600 font-medium">
                        <div className="flex items-center gap-1">
                            <CornerDownLeft className="w-3 h-3" />
                            <span>发送</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <span className="font-bold">Shift + Enter</span>
                            <span>换行</span>
                        </div>
                    </div>
                    <div className="flex items-center gap-1 text-[10px] md:text-xs text-gray-700 font-medium">
                        <Zap className="w-3 h-3 text-orange-500/50 fill-orange-500/10" />
                        <span>Powered by Coze</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CozeChat;
