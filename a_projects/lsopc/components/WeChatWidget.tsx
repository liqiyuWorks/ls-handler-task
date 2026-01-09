import React, { useState } from 'react';

const WeChatWidget: React.FC = () => {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-4">
            {/* QR Code Card - Transitions in/out */}
            <div
                className={`bg-white/10 backdrop-blur-xl border border-white/10 p-4 rounded-2xl shadow-2xl transition-all duration-300 origin-bottom-right ${isOpen ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-95 translate-y-4 pointer-events-none'
                    }`}
            >
                <div className="bg-white p-2 rounded-xl">
                    <img
                        src="/wechat_qr.jpg"
                        alt="WeChat QR Code"
                        className="w-40 h-40 object-cover rounded-lg"
                    />
                </div>
                <p className="text-center text-xs text-white/80 mt-3 font-medium tracking-widest">
                    扫码关注官方账号
                </p>
            </div>

            {/* Floating Button */}
            <button
                onMouseEnter={() => setIsOpen(true)}
                onClick={() => setIsOpen(!isOpen)}
                className="group relative w-12 h-12 bg-gradient-to-br from-green-500 to-emerald-700 rounded-full flex items-center justify-center shadow-lg hover:shadow-green-500/30 transition-all duration-300 hover:scale-110"
            >
                {/* Pulse Effect */}
                <div className="absolute inset-0 bg-green-500 rounded-full animate-ping opacity-20 group-hover:opacity-0"></div>

                {/* WeChat Icon (Simplified SVG) */}
                <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8.5,13.5 C8.5,13.5 10.5,13.5 10.5,13.5 C10.5,13.5 10.5,11.5 10.5,11.5 C10.5,11.5 8.5,11.5 8.5,11.5 C8.5,11.5 8.5,13.5 8.5,13.5 Z M16.5,5.5 C12.4,5.5 9,8 9,11 C9,12.3 9.6,13.5 10.6,14.4 L10,16 L12,15 C16,15 16.5,5.5 16.5,5.5 Z M16.5,5.5 C20.6,5.5 24,8 24,11 C24,13.6 22,15.8 19,16.3 L18,18 L16.5,17 C16.5,17 16.5,17 16.5,17 C16.5,17 16.5,17 16.5,17 L6,17 L4.5,18 L4.5,14.5 C1.7,13.3 0,11.3 0,9 C0,5.7 4.5,3 10,3 C15.5,3 20,5.7 20,9 L20,9.1 C19,7 17,5.5 16.5,5.5 Z" />
                    <path d="M14,14 C14,11.8 12.2,10 10,10 C7.8,10 6,11.8 6,14 C6,16.2 7.8,18 10,18 C12.2,18 14,16.2 14,14 Z M16,9 C16,6.8 17.8,5 20,5 C22.2,5 24,6.8 24,9 C24,11.2 22.2,13 20,13 C17.8,13 16,11.2 16,9 Z M8,13 C8,13 12,13 12,13 C12,13 12,15 12,15 C12,15 8,15 8,15 C8,15 8,13 8,13 Z" fill="none" />
                    {/* Custom simpler Wechat-like bubble path since standard icon is complex */}
                    <path d="M19.5 15c-2.5 0-4.5-1.8-4.5-4s2-1.8 4.5-1.8 4.5 1.8 4.5 4-2 4.2-4.5 4  z M7.5 14c4 0 7.5-2.7 7.5-6s-3.5-6-7.5-6-7.5 2.7-7.5 6c0 1.7 1 3.2 2.5 4.3l-1.5 3.2 3.5-1.5c1 .5 2 .8 3 .8 z M18.5 12.5c.3 0 .5-.2.5-.5s-.2-.5-.5-.5-.5.2-.5.5.2.5.5.5 z M20.5 12.5c.3 0 .5-.2.5-.5s-.2-.5-.5-.5-.5.2-.5.5.2.5.5.5 z M5.5 9c.3 0 .5-.2.5-.5s-.2-.5-.5-.5-.5.2-.5.5.2.5.5.5 z M9.5 9c.3 0 .5-.2.5-.5s-.2-.5-.5-.5-.5.2-.5.5.2.5.5.5 z" fillRule="evenodd" />
                </svg>
            </button>
        </div>
    );
};

export default WeChatWidget;
