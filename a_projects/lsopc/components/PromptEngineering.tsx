import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    ArrowLeft,
    Target,
    Lightbulb,
    AlertTriangle,
    CheckCircle2,
    Layers,
    Cpu,
    Copy,
    ChevronRight,
    Bookmark,
    Zap,
    Info,
    Rocket,
    User,
    Database,
    MonitorPlay,
    Check
} from 'lucide-react';

/** 可复制的提示词块：统一样式 + 复制按钮 + 已复制反馈 */
const CopyableBlock: React.FC<{
    id: string;
    title?: string;
    copyText: string;
    copiedId: string | null;
    onCopy: (text: string, id: string) => void;
    children: React.ReactNode;
    className?: string;
    titleIcon?: React.ReactNode;
}> = ({ id, title, copyText, copiedId, onCopy, children, className = '', titleIcon }) => {
    const isCopied = copiedId === id;
    return (
        <div className={`rounded-2xl bg-black/30 border border-white/10 overflow-hidden ${className}`}>
            {(title || copyText) && (
                <div className="flex justify-between items-center gap-3 px-4 py-3 border-b border-white/5 bg-white/[0.03]">
                    {title && (
                        <span className="text-sm font-bold text-white/90 flex items-center gap-2 truncate">
                            {titleIcon}
                            {title}
                        </span>
                    )}
                    <button
                        type="button"
                        onClick={() => onCopy(copyText, id)}
                        className={`shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                            isCopied
                                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                                : 'bg-white/10 text-gray-400 hover:bg-white/20 hover:text-white border border-white/10'
                        }`}
                    >
                        {isCopied ? <Check size={14} /> : <Copy size={14} />}
                        {isCopied ? '已复制' : '复制'}
                    </button>
                </div>
            )}
            <div className="p-4">{children}</div>
        </div>
    );
};

const PromptEngineering: React.FC = () => {
    const navigate = useNavigate();
    const [activeSection, setActiveSection] = useState('intro');
    const [copiedId, setCopiedId] = useState<string | null>(null);

    // TOC monitoring
    useEffect(() => {
        const handleScroll = () => {
            const sections = ['intro', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'summary'];
            const scrollPosition = window.scrollY + 100;

            for (const section of sections) {
                const element = document.getElementById(section);
                if (element && scrollPosition >= element.offsetTop) {
                    setActiveSection(section);
                }
            }
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    const scrollTo = (id: string) => {
        const element = document.getElementById(id);
        if (element) {
            window.scrollTo({
                top: element.offsetTop - 80,
                behavior: 'smooth'
            });
        }
    };

    const handleCopy = useCallback((text: string, id: string) => {
        navigator.clipboard.writeText(text);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 1800);
    }, []);

    const TOCItem = ({ id, title, icon: Icon }: { id: string, title: string, icon: any }) => (
        <button
            onClick={() => scrollTo(id)}
            className={`flex items-center gap-3 w-full px-4 py-3 rounded-xl transition-all text-sm font-medium ${activeSection === id
                ? 'bg-purple-500/10 text-purple-400 border-l-2 border-purple-500 shadow-sm'
                : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                }`}
        >
            <Icon size={16} className={activeSection === id ? 'text-purple-400' : 'text-gray-600'} />
            {title}
        </button>
    );

    return (
        <div className="flex flex-col md:flex-row gap-8 relative pt-20 pb-20 max-w-7xl mx-auto px-4">
            {/* Sticky TOC - Desktop only */}
            <aside className="hidden md:block w-72 h-[calc(100vh-120px)] sticky top-24 shrink-0 overflow-y-auto no-scrollbar">
                <div className="flex flex-col gap-1 p-2 bg-white/5 backdrop-blur-md rounded-2xl border border-white/10">
                    <div className="px-4 py-4 border-b border-white/5 mb-2">
                        <h3 className="text-sm font-bold text-white/90">课程大纲</h3>
                        <p className="text-[10px] text-gray-500 mt-1 uppercase tracking-widest">Mastering AI Interaction</p>
                    </div>
                    <TOCItem id="intro" title="序言：AI ✖️ OPC" icon={Rocket} />
                    <TOCItem id="ch1" title="01. 认识提示词" icon={Lightbulb} />
                    <TOCItem id="ch2" title="02. 基础结构" icon={Layers} />
                    <TOCItem id="ch3" title="03. 角色与技能" icon={User} />
                    <TOCItem id="ch4" title="04. 限制与约束" icon={AlertTriangle} />
                    <TOCItem id="ch5" title="05. 示例学习法" icon={Cpu} />
                    <TOCItem id="summary" title="总结与建议" icon={CheckCircle2} />
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-grow min-w-0 animate-fadeIn overflow-hidden">
                {/* Back Button */}
                <button
                    onClick={() => navigate('/')}
                    className="flex items-center gap-2 mb-8 px-4 py-2 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-sm text-gray-400 hover:text-white transition-all w-fit"
                >
                    <ArrowLeft size={16} />
                    返回首页
                </button>

                {/* Hero Title */}
                <section id="intro" className="mb-16">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-bold mb-6">
                        <Zap size={14} />
                        进阶课程
                    </div>
                    <h1 className="text-4xl md:text-5xl font-black mb-6 tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-500 leading-tight">
                        AI ✖️ OPC 之提示词优化
                    </h1>
                    <p className="text-lg text-gray-400 leading-relaxed max-w-3xl mb-8">
                        本文通过实战视角，深度解析提示词的原理与高级技巧，助你打通与 AI 高效协作的“最后一公里”。
                    </p>
                    <div className="flex flex-wrap items-center justify-between gap-4 p-6 rounded-2xl bg-gradient-to-br from-purple-500/5 to-transparent border border-white/5">
                        <div className="flex items-center gap-4 flex-wrap">
                            <div className="flex -space-x-3">
                                {[1, 2, 3].map(i => (
                                    <div key={i} className="w-10 h-10 rounded-full border-2 border-[#050505] bg-gray-800 flex items-center justify-center overflow-hidden shrink-0">
                                        <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${i + 123}`} alt="User" />
                                    </div>
                                ))}
                            </div>
                            <div className="text-sm">
                                <p className="text-white/80 font-medium whitespace-nowrap">已有 1,200+ 同学通过本课程提升效率</p>
                                <p className="text-gray-500 text-xs mt-0.5">最后更新：2026年1月12日</p>
                            </div>
                        </div>
                        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/20 text-green-400 text-xs font-medium">
                            <Copy size={12} />
                            本页所有提示词均可复制，直接用于 AI 对话
                        </div>
                    </div>
                </section>

                {/* Chapter 1 */}
                <section id="ch1" className="mb-24 scroll-mt-24 text-left">
                    <div className="flex items-center gap-4 mb-8">
                        <span className="text-5xl font-black text-white/5 select-none shrink-0">01</span>
                        <h2 className="text-2xl font-bold text-white tracking-tight">认识 AI 提示词</h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                        <div className="p-8 rounded-3xl bg-white/5 border border-white/10 flex flex-col gap-4">
                            <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center text-white">
                                <Info size={24} />
                            </div>
                            <h3 className="text-xl font-bold text-white">什么是提示词？</h3>
                            <p className="text-gray-400 text-sm leading-relaxed mb-3">
                                通俗解释：提示词（Prompt）就像给 AI 下达的“工作指令”。它决定了 AI 的思考空间与输出质量。
                            </p>
                            <p className="text-gray-500 text-xs leading-relaxed italic border-l-2 border-purple-500/40 pl-3">
                                类比：就像你对助手说话，说得越清楚，助手做得越好。
                            </p>
                        </div>
                        <div className="p-8 rounded-3xl bg-white/5 border border-white/10 flex flex-col gap-4">
                            <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center text-white">
                                <Bookmark size={24} />
                            </div>
                            <h3 className="text-xl font-bold text-white">为什么提示词很重要？</h3>
                            <ul className="text-gray-400 text-sm leading-relaxed space-y-2">
                                <li>• 同样的 AI，不同的提示词效果差 10 倍</li>
                                <li>• 提示词 = AI 的“使用说明书”</li>
                                <li>• 好提示词能节省时间、提高质量</li>
                            </ul>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <h4 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-4">实例对比（可复制到 AI 中对比效果）</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <CopyableBlock
                                id="ch1-bad"
                                title="糟糕的提示词"
                                copyText="写一篇文章"
                                copiedId={copiedId}
                                onCopy={handleCopy}
                                titleIcon={<AlertTriangle size={14} className="text-red-400" />}
                            >
                                <p className="text-red-400/90 text-sm font-bold mb-2">❌ 过于笼统</p>
                                <p className="text-gray-300 text-sm font-mono">"写一篇文章"</p>
                            </CopyableBlock>
                            <CopyableBlock
                                id="ch1-good"
                                title="优秀的提示词"
                                copyText="写一篇 500 字的科技博客，主题是 AI 在教育领域的应用，用通俗易懂的语言，包含 3 个具体案例。"
                                copiedId={copiedId}
                                onCopy={handleCopy}
                                titleIcon={<CheckCircle2 size={14} className="text-green-400" />}
                            >
                                <p className="text-green-400/90 text-sm font-bold mb-2">✅ 具体可执行</p>
                                <p className="text-gray-200 text-sm font-mono leading-relaxed">"写一篇 500 字的科技博客，主题是 AI 在教育领域的应用，用通俗易懂的语言，包含 3 个具体案例。"</p>
                            </CopyableBlock>
                        </div>
                    </div>
                </section>

                {/* Chapter 2 */}
                <section id="ch2" className="mb-24 scroll-mt-24 text-left">
                    <div className="flex items-center gap-4 mb-10">
                        <span className="text-5xl font-black text-white/5 select-none shrink-0">02</span>
                        <h2 className="text-2xl font-bold text-white tracking-tight">提示词的基础结构</h2>
                    </div>

                    <div className="space-y-8">
                        <div className="p-8 md:p-10 rounded-[40px] bg-gradient-to-b from-white/5 to-transparent border border-white/10">
                            <div className="flex items-center gap-3 mb-6">
                                <div className="p-2 bg-blue-500/20 rounded-lg text-blue-400 shrink-0">
                                    <Layers size={20} />
                                </div>
                                <h3 className="text-xl font-bold text-white">经典的 5W1H 结构</h3>
                            </div>
                            <p className="text-gray-400 text-sm mb-6">
                                用 Who / What / Why / When / Where / How 六个维度把任务说清楚，AI 才能稳定输出高质量结果。
                            </p>
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-y-8 gap-x-4 mb-10">
                                {[
                                    { k: 'Who', v: '角色', d: '你是谁 / AI 扮演什么角色' },
                                    { k: 'What', v: '任务', d: '要做什么' },
                                    { k: 'Why', v: '目的', d: '为什么做' },
                                    { k: 'When', v: '时间', d: '什么时候的背景' },
                                    { k: 'Where', v: '场景', d: '在什么场景下' },
                                    { k: 'How', v: '方式', d: '怎么做 / 用什么风格' },
                                ].map(item => (
                                    <div key={item.k} className="group">
                                        <div className="text-blue-400 font-black text-sm mb-1 group-hover:translate-x-1 transition-transform">{item.k}</div>
                                        <div className="text-white font-bold text-md mb-1">{item.v}</div>
                                        <div className="text-gray-500 text-xs">{item.d}</div>
                                    </div>
                                ))}
                            </div>

                            <div className="p-6 rounded-2xl bg-blue-500/5 border border-blue-500/10">
                                <h4 className="text-sm font-bold text-blue-400 mb-4 flex items-center gap-2">
                                    <Rocket size={14} /> 实战案例：设计成语接龙
                                </h4>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    <CopyableBlock
                                        id="ch2-idiom"
                                        title="5W1H 输入示例（复制即用）"
                                        copyText={`角色：你是一位资深的小学语文老师
任务：帮我设计一个成语接龙游戏
目的：让三年级学生在课堂上学习成语
方式：游戏要简单有趣，包含规则和 10 个示例成语`}
                                        copiedId={copiedId}
                                        onCopy={handleCopy}
                                    >
                                        <div className="text-xs text-gray-400 leading-relaxed font-mono whitespace-pre-line">
                                            角色：你是一位资深的小学语文老师<br />
                                            任务：帮我设计一个成语接龙游戏<br />
                                            目的：让三年级学生在课堂上学习成语<br />
                                            方式：游戏要简单有趣，包含规则和 10 个示例成语
                                        </div>
                                    </CopyableBlock>
                                    <div className="space-y-2 p-4 rounded-xl bg-white/5 border border-white/5">
                                        <div className="text-[11px] text-green-500/70 uppercase tracking-widest">💡 专家点评</div>
                                        <p className="text-xs text-gray-500 leading-relaxed italic">
                                            通过明确 Who (语文老师) 和 Why (三年级学生)，AI 会自动调整语言风格为形象易懂，并确保成语难度适中。
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="p-8 rounded-3xl bg-white/5 border border-white/10">
                                <h3 className="text-lg font-bold mb-6 flex items-center gap-2 text-white">
                                    <div className="w-6 h-6 rounded-full bg-purple-500/20 flex items-center justify-center text-[10px] text-purple-400 shrink-0">01</div>
                                    ICIO 结构 (进阶必备)
                                </h3>
                                <p className="text-gray-500 text-xs mb-4">进阶场景下用 ICIO 把指令、背景、输入、输出拆开写，便于复用和调试。</p>
                                <div className="space-y-4">
                                    {[
                                        { l: 'Instruction（指令）', d: '明确的任务指令' },
                                        { l: 'Context（上下文）', d: '提供背景信息' },
                                        { l: 'Input（输入）', d: '具体的输入内容' },
                                        { l: 'Output（输出）', d: '期望的输出格式' },
                                    ].map(x => (
                                        <div key={x.l} className="flex items-center gap-4">
                                            <div className="w-1 h-3 bg-purple-500/40 rounded-full shrink-0"></div>
                                            <div className="flex-grow">
                                                <span className="text-white font-bold text-sm block">{x.l}</span>
                                                <span className="text-gray-500 text-[11px]">{x.d}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="p-8 rounded-3xl bg-white/5 border border-white/10">
                                <h3 className="text-lg font-bold mb-6 flex items-center gap-2 text-white">
                                    <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center text-[10px] text-blue-400 shrink-0">02</div>
                                    三层金字塔结构
                                </h3>
                                <p className="text-gray-500 text-xs mb-4">从角色到任务再到格式，层层收窄，输出更可控。</p>
                                <div className="flex flex-col items-center gap-2">
                                    <div className="w-full p-4 bg-blue-500/20 rounded-xl border border-blue-500/30">
                                        <div className="text-blue-300 font-bold text-sm text-center">📍 第一层：角色定位（Who）</div>
                                        <p className="text-[10px] text-blue-400/70 text-center mt-1">"你是一个..."</p>
                                    </div>
                                    <div className="w-[85%] p-4 bg-blue-500/10 rounded-xl border border-blue-500/20">
                                        <div className="text-blue-200/80 font-bold text-sm text-center">📍 第二层：任务描述（What + Context）</div>
                                        <p className="text-[10px] text-blue-300/50 text-center mt-1">"我需要你帮我...，背景是..."</p>
                                    </div>
                                    <div className="w-[70%] p-4 bg-white/5 rounded-xl border border-white/10">
                                        <div className="text-gray-500 font-bold text-sm text-center">📍 第三层：要求细节（How + Format）</div>
                                        <p className="text-[10px] text-gray-600 text-center mt-1">"请用...风格，输出格式为..."</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Chapter 3 */}
                <section id="ch3" className="mb-24 scroll-mt-24 text-left">
                    <div className="flex items-center gap-4 mb-10">
                        <span className="text-5xl font-black text-white/5 select-none shrink-0">03</span>
                        <h2 className="text-2xl font-bold text-white tracking-tight">角色与技能定义</h2>
                    </div>

                    <div className="p-6 rounded-2xl bg-white/5 border border-white/10 mb-8">
                        <h3 className="text-lg font-bold text-white mb-3">为什么要定义角色？</h3>
                        <p className="text-gray-400 text-sm leading-relaxed mb-4">
                            原理：角色设定 = 给 AI 装上“专业大脑”。效果对比：无角色时“写一个营销方案”容易泛泛而谈；有角色时“你是资深品牌营销总监...”则输出专业深入、可直接落地。
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-xl bg-black/30 border border-white/5">
                            <div className="flex items-start gap-2">
                                <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
                                <div>
                                    <div className="text-amber-400/90 font-bold text-xs mb-1">无角色</div>
                                    <p className="text-gray-500 text-xs">“写一个营销方案” → 泛泛而谈</p>
                                </div>
                            </div>
                            <div className="flex items-start gap-2">
                                <CheckCircle2 size={16} className="text-green-400 shrink-0 mt-0.5" />
                                <div>
                                    <div className="text-green-400/90 font-bold text-xs mb-1">有角色</div>
                                    <p className="text-gray-500 text-xs">“你是资深品牌营销总监...” → 专业深入</p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <h4 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-4">角色定义的四个维度</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                        {[
                            { t: '维度1：身份背景', d: '从基础版到顶级版：姓名、年限、领域、关键经历、代表性案例', icon: Bookmark },
                            { t: '维度2：专业技能', d: '技能列表式：数据分析、可视化、商业思维、沟通表达等', icon: Layers },
                            { t: '维度3：工作风格', d: '逻辑严谨、务实高效、善于教学、追求完美', icon: Zap },
                            { t: '维度4：限制条件', d: '不滥用术语、不给出无法验证的建议、遇不确定时明确指出', icon: AlertTriangle },
                        ].map(dim => (
                            <div key={dim.t} className="p-6 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/[0.08] transition-all group">
                                <div className="flex items-center gap-4">
                                    <div className="p-2 border border-white/10 rounded-xl group-hover:scale-110 transition-transform shrink-0">
                                        <dim.icon size={18} className="text-gray-400" />
                                    </div>
                                    <div>
                                        <div className="text-white font-bold text-sm">{dim.t}</div>
                                        <div className="text-gray-500 text-xs mt-0.5">{dim.d}</div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    <div className="p-6 rounded-2xl bg-white/5 border border-white/10 mb-8 space-y-6">
                        <h4 className="text-sm font-bold text-white">维度示例：身份背景（从基础到顶级）</h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                            <div className="p-4 rounded-xl bg-black/30 border border-white/5">
                                <div className="text-gray-500 font-bold mb-2">基础版</div>
                                <p className="text-gray-400 font-mono">你是程序员</p>
                            </div>
                            <div className="p-4 rounded-xl bg-black/30 border border-white/5">
                                <div className="text-gray-500 font-bold mb-2">进阶版</div>
                                <p className="text-gray-400 font-mono">你是有 8 年经验的全栈工程师，精通 React 和 Node.js，曾在字节担任技术负责人</p>
                            </div>
                            <div className="p-4 rounded-xl bg-black/30 border border-purple-500/20">
                                <div className="text-purple-400 font-bold mb-2">顶级版</div>
                                <p className="text-gray-300 font-mono">你是张三，15 年经验的技术架构师，主导过 3 个千万级用户产品架构，擅长用通俗语言解释复杂技术，代码注重可维护性与性能</p>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="p-4 rounded-xl bg-black/30 border border-white/5">
                                <div className="text-gray-500 font-bold mb-2 text-xs">专业技能（列表式）</div>
                                <ul className="text-gray-400 text-xs space-y-1 font-mono">
                                    <li>✓ 数据分析：精通 Excel、SQL、Python</li>
                                    <li>✓ 可视化：用图表呈现数据洞察</li>
                                    <li>✓ 商业思维：理解业务目标，可落地建议</li>
                                    <li>✓ 沟通表达：用非技术语言向管理层汇报</li>
                                </ul>
                            </div>
                            <div className="p-4 rounded-xl bg-black/30 border border-white/5">
                                <div className="text-gray-500 font-bold mb-2 text-xs">工作风格 + 限制条件</div>
                                <ul className="text-gray-400 text-xs space-y-1">
                                    <li>逻辑严谨、务实高效、善于教学</li>
                                    <li>❌ 不使用专业术语或首次使用时解释</li>
                                    <li>❌ 不给出无法验证的假设性建议</li>
                                    <li>✅ 遇到不确定时明确指出并建议如何求证</li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    <CopyableBlock
                        id="ch3-template"
                        title="模板 A：专业顾问型角色定义"
                        copyText={`# 角色定义
你是{{姓名}}，一位{{职位}}，拥有{{年限}}年{{领域}}经验。
## 专业背景
- 工作经历：{{关键经历}}
- 核心专长：{{专长1}}、{{专长2}}、{{专长3}}
- 成功案例：{{代表性案例}}
## 技能清单
1. {{技能1}}：{{具体能力描述}}
2. {{技能2}}：{{具体能力描述}}
3. {{技能3}}：{{具体能力描述}}
## 工作原则
- 原则1：{{具体描述}}
- 原则2：{{具体描述}}
- 原则3：{{具体描述}}
## 输出风格
- 语言：{{正式/轻松/专业}}
- 结构：{{逻辑清晰/故事性强}}
- 深度：{{深入浅出/专业详尽}}
现在，请以这个角色完成以下任务：{{任务描述}}`}
                        copiedId={copiedId}
                        onCopy={handleCopy}
                        className="mb-8 border-purple-500/20"
                        titleIcon={<div className="w-2 h-2 bg-purple-500 rounded-full shrink-0" />}
                    >
                        <div className="font-mono text-xs md:text-sm text-gray-400 md:leading-8 leading-6 overflow-x-auto space-y-1">
                            <div><span className="text-gray-500"># 角色定义</span><br />你是 <span className="text-purple-400">{"{{姓名}}"}</span>，一位 <span className="text-purple-400">{"{{职位}}"}</span>，拥有 <span className="text-purple-400">{"{{年限}}"}</span> 年 <span className="text-purple-400">{"{{领域}}"}</span> 经验。</div>
                            <div><span className="text-gray-500">## 专业背景</span><br />- 工作经历：<span className="text-blue-400">{"{{关键经历}}"}</span><br />- 核心专长：<span className="text-blue-400">{"{{专长1}}"}</span>、<span className="text-blue-400">{"{{专长2}}"}</span>、<span className="text-blue-400">{"{{专长3}}"}</span><br />- 成功案例：<span className="text-blue-400">{"{{代表性案例}}"}</span></div>
                            <div><span className="text-gray-500">## 技能清单</span><br />1. <span className="text-green-400">{"{{技能1}}"}</span>：<span className="text-green-400/70">{"{{具体能力描述}}"}</span><br />2. <span className="text-green-400">{"{{技能2}}"}</span>：<span className="text-green-400/70">{"{{具体能力描述}}"}</span><br />3. <span className="text-green-400">{"{{技能3}}"}</span>：<span className="text-green-400/70">{"{{具体能力描述}}"}</span></div>
                            <div><span className="text-gray-500">## 工作原则</span><br />- 原则1：<span className="text-amber-400/80">{"{{具体描述}}"}</span><br />- 原则2：<span className="text-amber-400/80">{"{{具体描述}}"}</span><br />- 原则3：<span className="text-amber-400/80">{"{{具体描述}}"}</span></div>
                            <div><span className="text-gray-500">## 输出风格</span><br />- 语言：<span className="text-cyan-400/80">{"{{正式/轻松/专业}}"}</span><br />- 结构：<span className="text-cyan-400/80">{"{{逻辑清晰/故事性强}}"}</span><br />- 深度：<span className="text-cyan-400/80">{"{{深入浅出/专业详尽}}"}</span><br />现在，请以这个角色完成以下任务：<span className="text-white">{"{{任务描述}}"}</span></div>
                        </div>
                    </CopyableBlock>

                    <CopyableBlock
                        id="ch3-lisa"
                        title="实战案例：小红书运营专家（Lisa）"
                        copyText={`# 角色定义
你是Lisa，一位小红书资深运营专家，拥有5年新媒体运营经验。
## 专业背景
- 工作经历：曾操盘3个从0到10万粉的账号
- 核心专长：爆款选题策划、用户心理洞察、数据化运营
- 成功案例：单篇笔记最高获赞8.2万，转化ROI达1:15
## 技能清单
1. 选题策划：精准把握热点趋势，挖掘用户痛点
2. 文案撰写：擅长种草文案，转化率提升30%以上
3. 数据分析：通过后台数据优化内容策略
4. 社群运营：构建高粘性用户社群，复购率50%+
## 工作原则
- 用户第一：所有内容从用户需求出发
- 数据驱动：用测试验证假设，用数据指导决策
- 真诚分享：杜绝虚假宣传，保持账号信任度
## 输出风格
- 语言：亲切自然，像闺蜜聊天
- 结构：开头抓眼球，中间有干货，结尾有互动
- 深度：实操性强，拿来就能用
现在，请帮我分析这个产品的小红书推广策略：{{产品信息}}`}
                        copiedId={copiedId}
                        onCopy={handleCopy}
                        className="mb-10"
                        titleIcon={<Rocket size={14} className="text-purple-400" />}
                    >
                        <div className="font-mono text-xs text-gray-400 leading-relaxed space-y-3 whitespace-pre-line">
                            <p><span className="text-gray-500"># 角色定义</span><br />你是 Lisa，一位小红书资深运营专家，拥有 5 年新媒体运营经验。</p>
                            <p><span className="text-gray-500">## 专业背景</span><br />- 工作经历：曾操盘 3 个从 0 到 10 万粉的账号<br />- 核心专长：爆款选题策划、用户心理洞察、数据化运营<br />- 成功案例：单篇笔记最高获赞 8.2 万，转化 ROI 达 1:15</p>
                            <p><span className="text-gray-500">## 技能清单</span><br />1. 选题策划：精准把握热点趋势，挖掘用户痛点<br />2. 文案撰写：擅长种草文案，转化率提升 30% 以上<br />3. 数据分析：通过后台数据优化内容策略<br />4. 社群运营：构建高粘性用户社群，复购率 50%+</p>
                            <p><span className="text-gray-500">## 工作原则</span><br />- 用户第一：所有内容从用户需求出发<br />- 数据驱动：用测试验证假设，用数据指导决策<br />- 真诚分享：杜绝虚假宣传，保持账号信任度</p>
                            <p><span className="text-gray-500">## 输出风格</span><br />- 语言：亲切自然，像闺蜜聊天<br />- 结构：开头抓眼球，中间有干货，结尾有互动<br />- 深度：实操性强，拿来就能用<br />现在，请帮我分析这个产品的小红书推广策略：{"{{产品信息}}"}</p>
                        </div>
                    </CopyableBlock>

                    <h4 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-6">不同场景的角色实战</h4>
                    <div className="grid grid-cols-1 gap-6 mb-12">
                        <div className="p-8 rounded-3xl bg-white/5 border border-white/10 hover:border-purple-500/30 transition-all">
                            <div className="text-[10px] text-purple-400 font-bold uppercase tracking-widest mb-1">场景1：教育培训</div>
                            <h5 className="text-xl font-bold text-white mb-2">王老师 — 高中数学特级教师（20 年教学经验）</h5>
                            <p className="text-sm text-gray-500 mb-4">擅长把复杂概念简单化，总能找到学生的理解盲点。</p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <div className="text-[11px] text-gray-500 font-bold uppercase tracking-widest mb-3">教学风格</div>
                                    <ul className="space-y-2 text-xs text-gray-400">
                                        <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-purple-500/40"></div> 先问后讲，引导思考</li>
                                        <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-purple-500/40"></div> 举生活化的例子</li>
                                        <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-purple-500/40"></div> 用图示辅助理解</li>
                                        <li className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-purple-500/40"></div> 提供举一反三的练习</li>
                                    </ul>
                                </div>
                                <div>
                                    <div className="text-[11px] text-gray-500 font-bold uppercase tracking-widest mb-3">技能特长</div>
                                    <ul className="space-y-1 text-xs text-gray-400">
                                        <li>✓ 知识体系构建：帮学生建立完整知识网络</li>
                                        <li>✓ 错题分析：从错误中找到知识漏洞</li>
                                        <li>✓ 应试技巧：解题套路与时间管理</li>
                                        <li>✓ 心理辅导：缓解考试焦虑，建立信心</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        <div className="p-8 rounded-3xl bg-white/5 border border-white/10 hover:border-purple-500/30 transition-all">
                            <div className="text-[10px] text-purple-400 font-bold uppercase tracking-widest mb-1">场景2：商业咨询</div>
                            <h5 className="text-xl font-bold text-white mb-2">Michael Chen — 麦肯锡前咨询顾问，独立战略顾问</h5>
                            <p className="text-sm text-gray-500 mb-4">专业能力：战略规划（SWOT、波特五力、BCG 矩阵）、市场研究、财务分析（ROI 测算）、项目管理（敏捷、风险管控）。</p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <div className="text-[11px] text-gray-500 font-bold uppercase tracking-widest mb-3">工作方式</div>
                                    <ol className="space-y-1 text-xs text-gray-400 list-decimal pl-4">
                                        <li>先问清楚业务背景和目标</li>
                                        <li>用框架结构化分析问题</li>
                                        <li>提供 3 个以上备选方案，对比优劣</li>
                                        <li>给出清晰的实施路线图</li>
                                        <li>标注关键风险和应对措施</li>
                                    </ol>
                                </div>
                                <div>
                                    <div className="text-[11px] text-gray-500 font-bold uppercase tracking-widest mb-3">输出要求</div>
                                    <ul className="space-y-1 text-xs text-gray-400">
                                        <li>• 使用金字塔原理组织内容</li>
                                        <li>• 结论先行，论据支撑</li>
                                        <li>• 数据可视化，配图表说明</li>
                                        <li>• 提供 Excel 模板等工具</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        <div className="p-8 rounded-3xl bg-white/5 border border-white/10 hover:border-purple-500/30 transition-all">
                            <div className="text-[10px] text-purple-400 font-bold uppercase tracking-widest mb-1">场景3：技术开发</div>
                            <h5 className="text-xl font-bold text-white mb-2">Alex — 资深 Python 开发工程师，GitHub 5000+ stars 贡献者</h5>
                            <p className="text-sm text-gray-500 mb-4">技术栈：后端 Python/Django/Flask/FastAPI，数据库 MySQL/PostgreSQL/MongoDB/Redis，DevOps Docker/K8s/CI/CD，AI/ML TensorFlow/PyTorch/Scikit-learn。</p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <div className="text-[11px] text-gray-500 font-bold uppercase tracking-widest mb-3">编程风格</div>
                                    <ul className="space-y-1 text-xs text-gray-400">
                                        <li>✓ 代码简洁：遵循 PEP 8 规范</li>
                                        <li>✓ 注重性能：时间与空间复杂度</li>
                                        <li>✓ 防御性编程：异常处理、输入校验</li>
                                        <li>✓ 可维护性：清晰注释、模块化设计</li>
                                    </ul>
                                </div>
                                <div>
                                    <div className="text-[11px] text-gray-500 font-bold uppercase tracking-widest mb-3">输出规范</div>
                                    <ol className="space-y-1 text-xs text-gray-400 list-decimal pl-4">
                                        <li>先给出解决方案概述</li>
                                        <li>提供完整可运行代码</li>
                                        <li>添加详细注释说明</li>
                                        <li>列出依赖和环境要求</li>
                                        <li>给出测试用例和使用示例</li>
                                    </ol>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Chapter 4 */}
                <section id="ch4" className="mb-24 scroll-mt-24 text-left">
                    <div className="flex items-center gap-4 mb-10">
                        <span className="text-5xl font-black text-white/5 select-none shrink-0">04</span>
                        <h2 className="text-2xl font-bold text-white tracking-tight">限制与约束技巧</h2>
                    </div>

                    <div className="p-6 rounded-2xl bg-white/5 border border-white/10 mb-10">
                        <h3 className="text-lg font-bold text-white mb-3">为什么需要限制？</h3>
                        <p className="text-gray-400 text-sm leading-relaxed mb-2">不限制 = AI 天马行空，输出不可控；限制 = 把 AI 圈在“规则范围”内。效果：提高输出质量，减少无效内容。</p>
                    </div>

                    <h4 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-4">输出格式限制（结构化输出）</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
                        <div className="space-y-6">
                            <h3 className="text-base font-bold text-white flex items-center gap-2">
                                <Target size={18} className="text-orange-400 shrink-0" />
                                方法1：指定文本格式
                            </h3>
                            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 space-y-4">
                                <div className="p-3 rounded-xl bg-black/30 border border-white/5 font-mono text-xs text-gray-400">
                                    <div className="text-orange-400/80 mb-1">✅ Markdown 格式</div>
                                    <p>请用 Markdown：一级/二级标题、无序/有序列表、粗体/斜体。</p>
                                </div>
                                <div className="p-3 rounded-xl bg-black/30 border border-white/5 font-mono text-xs text-gray-400">
                                    <div className="text-orange-400/80 mb-1">✅ 纯文本格式</div>
                                    <p>请用纯文本输出，不要任何格式符号。</p>
                                </div>
                                <div className="p-3 rounded-xl bg-black/30 border border-white/5 font-mono text-xs text-gray-400">
                                    <div className="text-orange-400/80 mb-1">✅ 表格格式</div>
                                    <p>请用表格：| 列1 | 列2 | 列3 |，数据行对齐。</p>
                                </div>
                            </div>
                        </div>
                        <div className="space-y-6">
                            <h3 className="text-base font-bold text-white flex items-center gap-2">
                                <Database size={18} className="text-blue-400 shrink-0" />
                                方法2：JSON 结构化输出
                            </h3>
                            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 space-y-4">
                                <div className="p-4 rounded-xl bg-orange-400/5 border border-orange-400/10">
                                    <div className="text-[11px] text-orange-400/70 font-bold uppercase mb-2">⚠ 重要规则</div>
                                    <ul className="space-y-1 text-[10px] text-gray-500 list-disc pl-4">
                                        <li>所有字段必须存在，不能省略</li>
                                        <li>字符串用双引号，不要用单引号</li>
                                        <li>数字类型不加引号</li>
                                        <li>数组用方括号，对象用花括号</li>
                                        <li>最后一个字段后面不要加逗号</li>
                                    </ul>
                                </div>
                                <CopyableBlock
                                    id="ch4-json-schema"
                                    title="JSON 输出示例"
                                    copyText={`请严格按照以下JSON格式输出，不要有任何额外内容：
{
  "title": "标题内容",
  "summary": "摘要内容（50字以内）",
  "content": [{"section": "章节名称", "text": "章节内容"}],
  "tags": ["标签1", "标签2", "标签3"],
  "metadata": {"word_count": 数字, "reading_time": "预计阅读时间"}
}`}
                                    copiedId={copiedId}
                                    onCopy={handleCopy}
                                >
                                    <pre className="font-mono text-[10px] text-gray-400 overflow-x-auto">{`{
  "title": "标题内容",
  "summary": "摘要（50字以内）",
  "content": [{"section": "章节名", "text": "内容"}],
  "tags": ["标签1", "标签2"],
  "metadata": {"word_count": 数字, "reading_time": "预计阅读时间"}
}`}</pre>
                                </CopyableBlock>
                            </div>
                        </div>
                    </div>

                    <CopyableBlock
                        id="ch4-coze-json"
                        title="实战案例：扣子工作流中的 JSON 输出"
                        copyText={`你是内容分析专家。分析用户输入的{{user_content}}，提取关键信息。
输出要求：必须是标准JSON格式，方便后续节点解析
{
  "sentiment": "positive|neutral|negative",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "category": "分类名称",
  "summary": "一句话总结",
  "action_items": ["待办1", "待办2"],
  "confidence_score": 0.95
}
注意：sentiment只能是这三个值之一；keywords最多5个；confidence_score是0-1之间的小数。`}
                        copiedId={copiedId}
                        onCopy={handleCopy}
                        className="mb-10"
                        titleIcon={<Database size={14} className="text-blue-400" />}
                    >
                        <p className="text-gray-500 text-xs mb-3">你是内容分析专家。分析用户输入的 {"{{user_content}}"}，提取关键信息。输出要求：必须是标准 JSON 格式，方便后续节点解析。</p>
                        <pre className="p-4 rounded-xl bg-black/40 border border-white/5 font-mono text-[10px] text-blue-300/90 overflow-x-auto">{`{
  "sentiment": "positive|neutral|negative",
  "keywords": ["关键词1", "关键词2", "关键词3"],
  "category": "分类名称",
  "summary": "一句话总结",
  "action_items": ["待办1", "待办2"],
  "confidence_score": 0.95
}`}</pre>
                        <p className="text-gray-500 text-[10px] mt-2">注意：sentiment 只能是三值之一；keywords 最多 5 个；confidence_score 为 0–1 小数。</p>
                    </CopyableBlock>

                    <h4 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-4">输出内容限制</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                        {[
                            { t: '类型1：字数/长度', items: ['精确：标题 10 字、摘要 50 字、正文 500 字±20', '范围：短文案 30–50 字，长文 1000–1500 字', '字符级：推文 ≤280、短信 ≤70、邮件主题 ≤50', '技巧：字数要求写最后并用【】强调'] },
                            { t: '类型2：语言风格', items: ['语气：正式/轻松/专业/亲切', '人称：第一/二/三人称按场景选择', '禁止：绝对化词汇、负面情绪、敏感内容'] },
                            { t: '类型3：内容范围', items: ['主题/时间/地域/受众限制', '知识深度：入门/进阶/专家级', '禁止：政治宗教色情暴力、未证实数据'] },
                            { t: '类型4：逻辑结构', items: ['严格顺序：先问题→分析原因→方案→效果→行动步骤', '每部分单独成段，不跳过或合并'] },
                        ].map((block, i) => (
                            <div key={i} className="p-4 rounded-2xl bg-white/5 border border-white/10">
                                <div className="text-white font-bold text-xs mb-2">{block.t}</div>
                                <ul className="space-y-1 text-[10px] text-gray-500 list-disc pl-3">
                                    {block.items.map((item, j) => (
                                        <li key={j}>{item}</li>
                                    ))}
                                </ul>
                            </div>
                        ))}
                    </div>

                    <h4 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-4">多重限制组合（实战级）</h4>
                    <div className="grid grid-cols-1 gap-6 mb-10">
                        <CopyableBlock
                            id="ch4-xiaohongshu"
                            title="案例1：小红书种草文案（复制即用）"
                            copyText={`# 角色定义
你是小红书美妆博主，粉丝30万，人设是成分党+实测派。
# 任务
为{{产品名}}写一篇种草笔记。
# 格式限制
标题：18字以内，必须包含emoji和数字
正文：分为4段 - 开头段50字抛出痛点；产品段150字；实测段200字；总结段50字。图品建议：3张配图建议描述。
# 内容限制
✅ 必须包含：3个具体产品细节、2个真实场景描述、1个对比说明
❌ 严格禁止：夸大效果、绝对化表达、虚假宣传
# 语言风格
人称：第一人称"我"、"姐妹们"；语气：亲切真诚；emoji：3-5个。总字数：450-500字。`}
                            copiedId={copiedId}
                            onCopy={handleCopy}
                        >
                            <p className="text-gray-500 text-xs mb-3">角色：小红书美妆博主，粉丝 30 万，成分党+实测派人设。任务：为 {"{{产品名}}"} 写种草笔记。</p>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                                <div className="p-3 rounded-xl bg-black/30 border border-white/5">
                                    <div className="text-purple-400/80 font-bold mb-2">格式限制</div>
                                    <p className="text-gray-400">标题 18 字以内含 emoji 和数字；正文 4 段（开头 50 字/产品 150 字/实测 200 字/总结 50 字）；3 张配图建议。</p>
                                </div>
                                <div className="p-3 rounded-xl bg-black/30 border border-white/5">
                                    <div className="text-purple-400/80 font-bold mb-2">内容与语言</div>
                                    <p className="text-gray-400">必须含 3 个产品细节、2 个真实场景、1 个对比说明。禁止夸大、绝对化、虚假宣传。人称“我”“姐妹们”，语气亲切，emoji 3–5 个。总字数 450–500。</p>
                                </div>
                            </div>
                        </CopyableBlock>
                        <CopyableBlock
                            id="ch4-techdoc"
                            title="案例2：技术文档提示词（复制即用）"
                            copyText={`# 角色设定
你是技术文档工程师，擅长写清晰易懂的API文档。
# 任务
为{{API接口}}编写技术文档。
# 结构限制（必须包含以下所有部分）
1. 接口概述（50字）
2. 请求方式（GET/POST/PUT/DELETE）
3. 请求URL
4. 请求参数表格
5. 返回参数表格
6. 请求示例（curl + Python + JavaScript）
7. 返回示例（成功+失败）
8. 错误码说明
9. 注意事项（至少3条）
# 格式限制
表格格式：| 参数名 | 类型 | 必填 | 说明 | 示例 |`}
                            copiedId={copiedId}
                            onCopy={handleCopy}
                        >
                            <p className="text-gray-500 text-xs">角色：技术文档工程师。任务：为 {"{{API 接口}}"} 编写文档。结构必须包含：接口概述、请求方式、URL、请求/返回参数表、请求示例（curl + Python + JS）、返回示例（成功+失败）、错误码说明、注意事项至少 3 条。表格格式统一为：参数名 | 类型 | 必填 | 说明 | 示例。</p>
                        </CopyableBlock>
                    </div>

                    <div className="mt-12 p-1 rounded-3xl bg-gradient-to-br from-green-500/20 to-teal-500/20 overflow-hidden">
                        <div className="bg-[#050505] rounded-[22px] p-8 md:p-10 border border-white/5">
                            <div className="flex justify-between items-center mb-8 flex-wrap gap-4">
                                <h4 className="text-xl font-bold flex items-center gap-3 text-white">
                                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-teal-500 flex items-center justify-center text-white shadow-lg shadow-green-500/20">
                                        <Info size={20} />
                                    </div>
                                    完整示例预览：客服回复提示词 (综合限制)
                                </h4>
                                <button
                                    type="button"
                                    onClick={() => handleCopy('角色：你是某电商平台的客服代表，叫小美。\n任务：回复用户的售后咨询。\n\n语言限制：\n✅ 必须做到：\n- 称呼用"您"，显示尊重\n- 第一句表示理解和歉意（如果是问题）\n- 用"我们会..."展示负责态度\n- 结尾询问"还有什么可以帮您的吗？"\n\n❌ 严格禁止：\n- 使用"亲"、"哦"等过于随意的词\n- 推卸责任的表达（"这不是我们的问题"）\n- 空洞的套话（"感谢您的反馈"就结束）\n- 冰冷的机器人式回复\n\n风格要求：\n- 语气：专业且有温度\n- 节奏：先共情，再解决，后确认\n- 长度：80-150字\n\n格式要求：\n第一段：表示理解（20字内）\n第二段：解决方案（50-80字）\n第三段：后续跟进（30字内）', 'ch4-customer')}
                                    className={`shrink-0 flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold border transition-all ${copiedId === 'ch4-customer' ? 'bg-green-500/20 text-green-400 border-green-500/30' : 'bg-white/10 hover:bg-white/20 text-white border-white/10'}`}
                                >
                                    {copiedId === 'ch4-customer' ? <Check size={16} /> : <Copy size={16} />}
                                    {copiedId === 'ch4-customer' ? '已复制' : '复制客服模板'}
                                </button>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div className="space-y-6">
                                    <div className="bg-white/5 p-6 rounded-2xl border border-white/5">
                                        <h5 className="text-green-400 font-bold mb-4 flex items-center gap-2"><CheckCircle2 size={16} /> ✅ 必须做到</h5>
                                        <ul className="space-y-3 text-sm text-gray-300">
                                            <li className="flex items-start gap-2"><div className="text-green-500 mt-0.5">•</div>称呼用"您"，显示尊重</li>
                                            <li className="flex items-start gap-2"><div className="text-green-500 mt-0.5">•</div>第一句表示理解和歉意</li>
                                            <li className="flex items-start gap-2"><div className="text-green-500 mt-0.5">•</div>用"我们会..."展示负责态度</li>
                                            <li className="flex items-start gap-2"><div className="text-green-500 mt-0.5">•</div>结尾询问"还有什么可以帮您的吗？"</li>
                                        </ul>
                                    </div>
                                    <div className="bg-black/40 p-6 rounded-2xl border border-red-500/20">
                                        <h5 className="text-red-400 font-bold mb-4 flex items-center gap-2"><AlertTriangle size={16} /> ❌ 严格禁止</h5>
                                        <ul className="space-y-3 text-sm text-gray-400">
                                            <li className="flex items-start gap-2"><div className="text-red-500 mt-0.5">×</div>使用"亲"、"哦"等过于随意的词</li>
                                            <li className="flex items-start gap-2"><div className="text-red-500 mt-0.5">×</div>推卸责任（"这不是我们的问题"）</li>
                                            <li className="flex items-start gap-2"><div className="text-red-500 mt-0.5">×</div>空洞的套话（"感谢反馈"就结束）</li>
                                            <li className="flex items-start gap-2"><div className="text-red-500 mt-0.5">×</div>冰冷的机器人式回复</li>
                                        </ul>
                                    </div>
                                </div>
                                <div className="space-y-6">
                                    <div className="bg-white/5 p-6 rounded-2xl border border-white/5 h-full">
                                        <h5 className="text-teal-400 font-bold mb-4 flex items-center gap-2"><Layers size={16} /> 风格与格式要求</h5>
                                        <div className="space-y-6">
                                            <div>
                                                <div className="text-[11px] text-gray-500 uppercase tracking-widest mb-2 font-bold">基础设定</div>
                                                <p className="text-sm text-gray-300">
                                                    角色：某电商平台客服代表小美<br />
                                                    任务：回复用户售后咨询<br />
                                                    总字数：<span className="text-teal-300 font-mono bg-teal-500/20 px-1 rounded">80-150字</span>
                                                </p>
                                            </div>
                                            <div>
                                                <div className="text-[11px] text-gray-500 uppercase tracking-widest mb-2 font-bold">结构化输出</div>
                                                <div className="bg-black/50 rounded-xl p-4 border border-white/5 font-mono text-xs text-gray-400 space-y-3">
                                                    <div className="flex gap-4 border-b border-white/5 pb-2">
                                                        <span className="text-gray-500 w-12">第一段</span>
                                                        <span className="text-gray-300">表示理解（20字内）</span>
                                                    </div>
                                                    <div className="flex gap-4 border-b border-white/5 pb-2">
                                                        <span className="text-gray-500 w-12">第二段</span>
                                                        <span className="text-gray-300">解决方案（50-80字）</span>
                                                    </div>
                                                    <div className="flex gap-4">
                                                        <span className="text-gray-500 w-12">第三段</span>
                                                        <span className="text-gray-300">后续跟进（30字内）</span>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="mt-4 p-4 rounded-xl bg-green-500/5 border border-green-500/20">
                                                <div className="text-[11px] text-green-400/80 font-bold uppercase tracking-widest mb-2">示例回复</div>
                                                <p className="text-sm text-gray-300 leading-relaxed">
                                                    您好，非常抱歉给您带来不便。<br />
                                                    关于您反馈的商品破损问题，我们已经为您申请了退款，预计 3–5 个工作日到账。同时，我已备注您的账号，下次购买可享受额外 9.5 折优惠作为补偿。<br />
                                                    请问还有什么可以帮您的吗？我们会持续改进服务质量。
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Chapter 5 */}
                <section id="ch5" className="mb-24 scroll-mt-24 text-left">
                    <div className="flex items-center gap-4 mb-10">
                        <span className="text-5xl font-black text-white/5 select-none shrink-0">05</span>
                        <h2 className="text-2xl font-bold text-white tracking-tight">示例学习法 (Few-Shot)</h2>
                    </div>

                    <div className="p-8 rounded-[40px] bg-gradient-to-br from-purple-600/10 to-transparent border border-white/10 mb-8">
                        <h3 className="text-xl font-bold text-white mb-4">什么是示例学习（Few-Shot）？</h3>
                        <p className="text-gray-400 leading-relaxed mb-3">
                            原理：给 AI 看几个例子，它就能学会你想要的风格和模式。如果你无法用文字精准描述某种“感觉”，那就直接给范例——AI 具备强大的模式识别能力。
                        </p>
                        <p className="text-gray-500 text-sm mb-4">
                            效果：准确度提升 50%+，比纯文字描述有效得多。<br />
                            <span className="text-purple-400 font-mono text-xs">核心公式：示例1 + 示例2 + 示例3 + 新任务 = 高质量输出</span>
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-6">
                            {[
                                { t: '1. 提供案例', d: '展示你想要的理想输出', c: 'bg-purple-500/20' },
                                { t: '2. 提炼规律', d: '让 AI 理解内在逻辑', c: 'bg-blue-500/20' },
                                { t: '3. 处理新任务', d: '套用学到的模式完成新输入', c: 'bg-green-500/20' },
                            ].map(step => (
                                <div key={step.t} className="flex flex-col gap-2">
                                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-xs shrink-0 ${step.c}`}>
                                        {step.t.split('.')[0]}
                                    </div>
                                    <div className="text-white font-bold text-sm mt-1">{step.t}</div>
                                    <div className="text-gray-500 text-xs leading-relaxed">{step.d}</div>
                                </div>
                            ))}
                        </div>
                        <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                            <h5 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Few-Shot 三步法</h5>
                            <ol className="text-sm text-gray-400 space-y-1 list-decimal pl-4">
                                <li>给示例：1–3 个代表性案例</li>
                                <li>说规律：总结共同特点</li>
                                <li>新任务：套用学到的模式</li>
                            </ol>
                            <p className="text-gray-500 text-xs mt-3">核心原则：示例胜过千言（看例子比读描述有效 10 倍）；由浅入深；正反对照（展示对错让 AI 理解边界）。</p>
                        </div>
                    </div>

                    <CopyableBlock
                        id="ch5-basic-template"
                        title="基本结构模板（Few-Shot）"
                        copyText={`你需要完成{{任务描述}}。
参考以下示例：
【示例1】输入：{{示例输入1}} → 输出：{{示例输出1}}
【示例2】输入：{{示例输入2}} → 输出：{{示例输出2}}
【示例3】输入：{{示例输入3}} → 输出：{{示例输出3}}
现在请处理：输入：{{实际输入}} → 输出：`}
                        copiedId={copiedId}
                        onCopy={handleCopy}
                        className="mb-8"
                    >
                        <pre className="font-mono text-[11px] text-gray-400 overflow-x-auto whitespace-pre-wrap">{`你需要完成 {{任务描述}}。
参考以下示例：
【示例1】输入：{{示例输入1}} → 输出：{{示例输出1}}
【示例2】输入：{{示例输入2}} → 输出：{{示例输出2}}
【示例3】输入：{{示例输入3}} → 输出：{{示例输出3}}
现在请处理：输入：{{实际输入}} → 输出：`}</pre>
                    </CopyableBlock>

                    <h4 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-4">四大应用场景</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                        <CopyableBlock
                            id="ch5-xhs-style"
                            title="场景1：风格学习 — 小红书标题风格"
                            copyText={`学习以下标题特点，生成新标题：
示例1：💰省钱攻略｜这样买菜一个月省1000！主妇必看
示例2：🔥实测3个月｜这个方法让我狂瘦20斤✨
示例3：⚠避雷｜装修5大坑，千万别踩😭
特点总结：emoji开头、用｜分隔制造悬念、包含数字、结尾加情绪emoji
现在生成：主题：{{你的主题}} → 请输出标题`}
                            copiedId={copiedId}
                            onCopy={handleCopy}
                            titleIcon={<Zap size={14} className="text-purple-400" />}
                        >
                            <p className="text-[10px] text-gray-500 mb-2">学习以下标题特点，生成新标题：</p>
                            <div className="space-y-2 mb-3">
                                <p className="text-[11px] text-gray-400 font-mono">示例1：💰省钱攻略｜这样买菜一个月省1000！主妇必看</p>
                                <p className="text-[11px] text-gray-400 font-mono">示例2：🔥实测3个月｜这个方法让我狂瘦20斤✨</p>
                                <p className="text-[11px] text-gray-400 font-mono">示例3：⚠避雷｜装修5大坑，千万别踩😭</p>
                            </div>
                            <div className="p-3 bg-purple-500/5 rounded-lg border border-purple-500/10 mb-3">
                                <div className="text-[10px] text-purple-400/70 mb-2 font-bold">特点总结</div>
                                <ul className="text-[10px] text-gray-500 space-y-1">
                                    <li>✓ emoji 开头</li>
                                    <li>✓ 用｜分隔制造悬念</li>
                                    <li>✓ 包含数字增加可信度</li>
                                    <li>✓ 结尾加情绪 emoji</li>
                                </ul>
                            </div>
                            <p className="text-[10px] text-gray-500">现在生成 — 主题：阳台改造 → 标题：🌸改造日记｜3000元打造梦幻小花园！邻居都来参观</p>
                        </CopyableBlock>
                        <CopyableBlock
                            id="ch5-json-extract"
                            title="场景2：格式学习 — 数据提取 JSON"
                            copyText={`从文本中提取关键信息，输出JSON格式。
【示例】
输入：特斯拉今天宣布Model 3降价2万，起售价22.99万，订单暴增300%
输出：{"brand":"特斯拉","event":"降价","product":"Model 3","amount":"2万元","result":"订单暴增300%"}
现在处理：输入：{{新闻内容}}`}
                            copiedId={copiedId}
                            onCopy={handleCopy}
                            titleIcon={<Database size={14} className="text-blue-400" />}
                        >
                            <div className="space-y-3">
                                <div className="p-3 bg-black/40 rounded-lg border border-white/5">
                                    <div className="text-[10px] text-gray-500 mb-1">示例输入</div>
                                    <p className="text-[11px] text-gray-400">特斯拉今天宣布 Model 3 降价 2 万，起售价 22.99 万，订单暴增 300%</p>
                                </div>
                                <div className="p-3 bg-blue-500/5 rounded-lg border border-blue-500/10 font-mono text-[10px] text-blue-300/90">
                                    {"{"} "brand": "特斯拉", "event": "降价", "product": "Model 3", "amount": "2万元", "result": "订单暴增300%" {"}"}
                                </div>
                            </div>
                        </CopyableBlock>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-24">
                        {[
                            { t: '场景3：文风模范', d: '学习特定作家、KOL 或企业的公关腔调，通过 1–3 个范例让 AI 模仿语气与结构', icon: CheckCircle2 },
                            { t: '场景4：链式推理', d: '引导 AI 按特定步骤进行深度逻辑推理，示例中展示“先 A 再 B 再 C”的思考路径', icon: Zap },
                        ].map(usage => (
                            <div key={usage.t} className="p-5 flex items-start gap-4 bg-white/5 border border-white/5 rounded-2xl">
                                <usage.icon size={18} className="text-purple-400 shrink-0 mt-1" />
                                <div>
                                    <div className="text-white font-bold text-sm mb-1">{usage.t}</div>
                                    <div className="text-gray-500 text-[11px] leading-relaxed">{usage.d}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Final Summary */}
                <section id="summary" className="mb-24 scroll-mt-24 p-8 md:p-12 rounded-[40px] md:rounded-[50px] bg-white text-black text-center relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-8 text-black/5 flex flex-col items-end pointer-events-none group-hover:scale-110 transition-transform duration-700">
                        <Zap size={120} />
                    </div>
                    <CheckCircle2 size={48} className="mx-auto mb-6 text-black shrink-0" />
                    <h2 className="text-2xl md:text-3xl font-black mb-4">总结与建议</h2>
                    <p className="text-gray-600 mb-4 max-w-2xl mx-auto font-medium text-sm md:text-base">
                        提示词优化不是一次到位的艺术，而是不断调试的过程。建议从简单的 5W1H 开始，逐步增加角色定义、限制约束与示例学习，最终构建属于你自己的 Prompt 库。
                    </p>
                    <p className="text-gray-500 mb-10 max-w-2xl mx-auto text-sm">
                        掌握本课程中的基础结构、角色与技能、限制与约束、示例学习法后，你与 AI 的协作效率会显著提升。记得多练、多改、多积累。
                    </p>
                    <button
                        onClick={() => navigate('/savings-agent')}
                        className="px-8 py-4 md:px-10 md:py-5 bg-black text-white rounded-full font-bold hover:scale-105 transition-transform shadow-2xl text-sm md:text-base"
                    >
                        去实战演练
                    </button>
                </section>
            </main>
        </div>
    );
};

export default PromptEngineering;
