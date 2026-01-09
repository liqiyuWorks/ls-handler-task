
import React from 'react';
import { APP_CONFIG } from '../constants';

const Header: React.FC = () => {
  return (
    <header className="py-6 px-8 flex justify-between items-center border-b border-white/10 sticky top-0 z-50 glass-morphism">
      <div className="flex items-center gap-4">
        <div className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-orange-600 to-yellow-600 rounded-xl opacity-75 group-hover:opacity-100 transition duration-1000 group-hover:duration-200 blur"></div>
          <img
            src="/avatar.jpg"
            alt="Li Sheng Avatar"
            className="relative w-12 h-12 rounded-xl object-cover shadow-2xl border border-white/10"
          />
        </div>
        <div>
          <div className="font-extrabold text-xl tracking-tight leading-none">{APP_CONFIG.COMPANY_NAME}</div>
        </div>
      </div>
      {/* Slogan removed from header as per request */}
    </header>
  );
};

export default Header;
