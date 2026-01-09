
import React from 'react';
import { APP_CONFIG } from '../constants';

const Footer: React.FC = () => {
  return (
    <footer className="py-8 border-t border-white/5 flex flex-col items-center gap-4 bg-[#080808]">
      <div className="flex gap-6 text-gray-500 text-xs tracking-[0.2em] uppercase font-semibold">
        <span>Optimization</span>
        <span className="text-gray-800">•</span>
        <span>Purchase</span>
        <span className="text-gray-800">•</span>
        <span>Consulting</span>
      </div>
      <div className="text-[10px] text-gray-600 tracking-[0.3em] font-light">
        {APP_CONFIG.FOOTER_TEXT}
      </div>
    </footer>
  );
};

export default Footer;
