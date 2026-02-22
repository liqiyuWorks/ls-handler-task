import React from 'react';
import { useNavigate } from 'react-router-dom';
import { MonitorPlay, Database, ChevronRight } from 'lucide-react';

const PlatformTools: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="w-full max-w-5xl mx-auto px-4 mt-12 mb-20">
            <div className="flex items-center gap-3 mb-8 justify-center md:justify-start">
                <div className="w-1.5 h-6 bg-blue-500 rounded-full shadow-[0_0_15px_rgba(59,130,246,0.5)]"></div>
                <h2 className="text-xl font-bold tracking-wide">平台工具</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Presentation Mode Card */}
                <a
                    href="/overview.html"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group relative bg-[#0f172a] border border-white/5 rounded-2xl p-6 hover:border-blue-500/30 transition-all duration-300 hover:shadow-[0_0_30px_rgba(59,130,246,0.15)] flex flex-col md:flex-row items-center md:items-start gap-4"
                >
                    <div className="p-4 bg-blue-500/10 rounded-xl group-hover:bg-blue-500/20 transition-colors">
                        <MonitorPlay className="w-8 h-8 text-blue-400" />
                    </div>
                    <div className="flex-1 text-center md:text-left">
                        <h3 className="text-lg font-bold text-white mb-2 group-hover:text-blue-400 transition-colors">
                            进入演示模式
                        </h3>
                        <p className="text-gray-400 text-sm mb-4">
                            开启全屏沉浸式演示视图，适合会议展示与汇报。
                        </p>
                        <span className="inline-flex items-center text-xs font-bold text-blue-500 uppercase tracking-wider group-hover:translate-x-1 transition-transform">
                            Open Presentation <ChevronRight className="w-3 h-3 ml-1" />
                        </span>
                    </div>
                </a>

                {/* Knowledge Base Card */}
                <div
                    onClick={() => window.open('/knowledge-base', '_blank')}
                    className="group relative bg-[#0f172a] border border-white/5 rounded-2xl p-6 hover:border-purple-500/30 transition-all duration-300 hover:shadow-[0_0_30px_rgba(168,85,247,0.15)] flex flex-col md:flex-row items-center md:items-start gap-4 cursor-pointer"
                >
                    <div className="p-4 bg-purple-500/10 rounded-xl group-hover:bg-purple-500/20 transition-colors">
                        <Database className="w-8 h-8 text-purple-400" />
                    </div>
                    <div className="flex-1 text-center md:text-left">
                        <h3 className="text-lg font-bold text-white mb-2 group-hover:text-purple-400 transition-colors">
                            扣子知识库管理
                        </h3>
                        <p className="text-gray-400 text-sm mb-4">
                            管理 AI 助手的核心知识数据，支持文件上传与 URL 索引。
                        </p>
                        <span className="inline-flex items-center text-xs font-bold text-purple-500 uppercase tracking-wider group-hover:translate-x-1 transition-transform">
                            Manage Knowledge Base <ChevronRight className="w-3 h-3 ml-1" />
                        </span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PlatformTools;
