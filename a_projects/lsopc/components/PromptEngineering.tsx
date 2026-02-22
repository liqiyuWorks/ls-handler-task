import React, { useState, useEffect } from 'react';
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
    MonitorPlay
} from 'lucide-react';

const PromptEngineering: React.FC = () => {
    const navigate = useNavigate();
    const [activeSection, setActiveSection] = useState('intro');

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

    const copyToClipboard = (text: string) => {
        navigator.clipboard.writeText(text);
    };

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
                    <div className="flex items-center gap-6 p-6 rounded-2xl bg-gradient-to-br from-purple-500/5 to-transparent border border-white/5 flex-wrap">
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
                </section>

                {/* Chapter 1 */}
                <section id="ch1" className="mb-24 scroll-mt-24 text-left">
                    <div className="flex items-center gap-4 mb-8">
                        <span className="text-5xl font-black text-white/5 select-none shrink-0">01</span>
                        <h2 className="text-2xl font-bold text-white tracking-tight">认识 AI 提示词</h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
                        <div className="p-8 rounded-3xl bg-white/5 border border-white/10 flex flex-col gap-4">
                            <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center text-white">
                                <Info size={24} />
                            </div>
                            <h3 className="text-xl font-bold text-white">什么是提示词？</h3>
                            <p className="text-gray-400 text-sm leading-relaxed">
                                通俗解释：提示词（Prompt）就像给 AI 下达的“工作指令”。它决定了 AI 的思考空间与输出质量。
                            </p>
                        </div>
                        <div className="p-8 rounded-3xl bg-white/5 border border-white/10 flex flex-col gap-4">
                            <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center text-white">
                                <Bookmark size={24} />
                            </div>
                            <h3 className="text-xl font-bold text-white">为什么重要？</h3>
                            <p className="text-gray-400 text-sm leading-relaxed">
                                同样的 AI，不同的提示词效果差 10 倍。提示词就是 AI 的“使用说明书”，好的提示词能直接节省你的创作时间。
                            </p>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <h4 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-4">实例对比</h4>
                        <div className="p-1 gap-2 grid grid-cols-1 md:grid-cols-2 rounded-3xl bg-white/5 border border-white/5 overflow-hidden">
                            <div className="p-6 md:p-8 bg-black/40 rounded-[28px]">
                                <div className="flex items-center gap-2 text-red-400 font-bold mb-4 text-sm">
                                    <AlertTriangle size={16} /> 糟糕的提示词
                                </div>
                                <div className="p-4 rounded-xl bg-red-400/5 border border-red-400/20 text-gray-300 text-sm font-mono">
                                    "写一篇文章"
                                </div>
                            </div>
                            <div className="p-6 md:p-8 bg-purple-500/5 rounded-[28px]">
                                <div className="flex items-center gap-2 text-green-400 font-bold mb-4 text-sm">
                                    <CheckCircle2 size={16} /> 优秀的提示词
                                </div>
                                <div className="p-4 rounded-xl bg-green-400/5 border border-green-400/20 text-gray-200 text-sm font-mono leading-relaxed">
                                    "写一篇 500 字的科技博客，主题是 AI 在教育领域的应用，用通俗易懂的语言，包含 3 个具体案例。"
                                </div>
                            </div>
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
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-y-8 gap-x-4 mb-10">
                                {[
                                    { k: 'Who', v: '角色定位', d: 'AI 扮演什么角色' },
                                    { k: 'What', v: '核心任务', d: '具体要做什么' },
                                    { k: 'Why', v: '目的意图', d: '解决什么问题' },
                                    { k: 'When', v: '背景时刻', d: '时间或阶段' },
                                    { k: 'Where', v: '应用场景', d: '输出在哪里用' },
                                    { k: 'How', v: '风格要求', d: '语气或结构' },
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
                                    <div className="space-y-2">
                                        <div className="text-[11px] text-gray-500 uppercase tracking-widest">输入构成</div>
                                        <div className="text-xs text-gray-400 leading-relaxed font-mono bg-black/30 p-3 rounded-lg border border-white/5">
                                            角色：你是一位资深的小学语文老师<br />
                                            任务：帮我设计一个成语接龙游戏<br />
                                            目的：让三年级学生在课堂上学习成语<br />
                                            方式：游戏要简单有趣，包含规则和10个示例
                                        </div>
                                    </div>
                                    <div className="space-y-2">
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
                                <div className="space-y-4">
                                    {[
                                        { l: 'Instruction', d: '明确的任务指令' },
                                        { l: 'Context', d: '背景信息' },
                                        { l: 'Input', d: '具体输入内容' },
                                        { l: 'Output', d: '期望输出格式' },
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
                                <div className="flex flex-col items-center gap-2">
                                    <div className="w-full p-4 bg-blue-500/20 rounded-xl border border-blue-500/30">
                                        <div className="text-blue-300 font-bold text-sm text-center">第一层：角色定位 (Who)</div>
                                        <p className="text-[10px] text-blue-400/70 text-center mt-1">"你是一个..."</p>
                                    </div>
                                    <div className="w-[85%] p-4 bg-blue-500/10 rounded-xl border border-blue-500/20">
                                        <div className="text-blue-200/80 font-bold text-sm text-center">第二层：任务描述 (What + Context)</div>
                                        <p className="text-[10px] text-blue-300/50 text-center mt-1">"我需要你帮我...，背景是..."</p>
                                    </div>
                                    <div className="w-[70%] p-4 bg-white/5 rounded-xl border border-white/10">
                                        <div className="text-gray-500 font-bold text-sm text-center">第三层：要求细节 (How + Format)</div>
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

                    <p className="text-gray-400 mb-8 leading-relaxed">
                        给 AI 装上“专业大脑”，让它从“泛泛而谈”变身为深耕特定领域的专家。这里我们从四个核心维度来构建角色：
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-12">
                        {[
                            { t: '身份背景', d: '定义姓名、从业经历、擅长领域', icon: Bookmark },
                            { t: '专业技能', d: '具体能力清单（如数据分析、商业思维）', icon: Layers },
                            { t: '工作风格', d: '逻辑严谨、务实高效、善于教学', icon: Zap },
                            { t: '限制条件', d: '避免术语、明确底线、交互禁忌', icon: AlertTriangle },
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

                    <div className="relative group p-1 rounded-3xl bg-gradient-to-r from-purple-500/20 to-blue-500/20 overflow-hidden mb-12">
                        <div className="bg-[#050505] rounded-[22px] p-8 border border-white/5">
                            <div className="flex justify-between items-center mb-6 flex-wrap gap-4">
                                <h4 className="text-white font-bold flex items-center gap-2">
                                    <div className="w-2 h-2 bg-purple-500 rounded-full shrink-0"></div>
                                    通用角色定义模板
                                </h4>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => copyToClipboard('# 角色定义\n你是{{姓名}}，一位{{职位}}，拥有{{年限}}年{{领域}}经验。\n## 专业背景\n- 工作经历：{{关键经历}}\n- 核心专长：{{专长1}}、{{专长2}}\n- 成功案例：{{代表性案例}}\n## 技能清单\n1. {{技能1}}：{{具体描述}}')}
                                        className="p-2 text-gray-500 hover:text-white rounded-lg hover:bg-white/5 transition-all text-xs flex items-center gap-2"
                                    >
                                        <Copy size={14} /> 复制专家版
                                    </button>
                                </div>
                            </div>
                            <div className="font-mono text-xs md:text-sm text-gray-400 md:leading-8 leading-6 overflow-x-auto">
                                <span className="text-gray-500"># 角色定义</span><br />
                                你是 <span className="text-purple-400">{"{{姓名}}"}</span>，一位 <span className="text-purple-400">{"{{职位}}"}</span>，拥有 <span className="text-purple-400">{"{{年限}}"}</span> 年 <span className="text-purple-400">{"{{领域}}"}</span> 经验。<br />
                                <span className="text-gray-500">## 专业背景</span><br />
                                - 工作经历：<span className="text-blue-400">{"{{关键经历}}"}</span><br />
                                - 核心专长：<span className="text-blue-400">{"{{专长1}}"}</span>、<span className="text-blue-400">{"{{专长2}}"}</span><br />
                                <span className="text-gray-500">## 技能清单</span><br />
                                1. <span className="text-green-400">{"{{技能1}}"}</span>：<span className="text-green-400/70">{"{{具体能力描述}}"}</span>
                            </div>
                        </div>
                    </div>

                    <h4 className="text-sm font-bold text-gray-500 uppercase tracking-widest mb-6">不同场景的角色实战</h4>
                    <div className="grid grid-cols-1 gap-6 mb-12">
                        {[
                            {
                                scene: '场景1：教育培训',
                                title: '高中数学特级教师',
                                desc: '擅长把复杂概念简单化，总能找到学生的理解盲点。',
                                style: ['先问后讲，引导思考', '举生活化的例子', '用图示辅助理解'],
                                skills: ['知识体系构建', '错题分析', '应试技巧', '心理辅导']
                            },
                            {
                                scene: '场景2：商业咨询',
                                title: '麦肯锡前咨询顾问',
                                desc: '具备深度行业洞察力，擅长结构化解决复杂商业问题。',
                                style: ['逻辑严谨：结论先行，论据支撑', '用框架结构化分析问题', '数据可视化，配图表说明'],
                                skills: ['战略规划 (SWOT/BCG)', '市场研究', '财务分析 (ROI测算)', '项目管理']
                            },
                            {
                                scene: '场景3：技术开发',
                                title: '资深全栈开发工程师',
                                desc: 'GitHub 5000+ stars 贡献者，精通系统架构设计。',
                                style: ['代码简洁：遵循标准规范', '注重性能与可维护性', '防御性编程与异常处理'],
                                skills: ['前后端架构', 'DevOps 交付流', 'AI/ML 集成', '自动化测试']
                            }
                        ].map((item, idx) => (
                            <div key={idx} className="p-8 rounded-3xl bg-white/5 border border-white/10 hover:border-purple-500/30 transition-all">
                                <div className="flex justify-between items-start mb-6">
                                    <div>
                                        <div className="text-[10px] text-purple-400 font-bold uppercase tracking-widest mb-1">{item.scene}</div>
                                        <h5 className="text-xl font-bold text-white mb-2">{item.title}</h5>
                                        <p className="text-sm text-gray-500">{item.desc}</p>
                                    </div>
                                    <div className="hidden sm:flex -space-x-2">
                                        {[1, 2].map(i => (
                                            <div key={i} className="w-8 h-8 rounded-full border border-white/10 bg-gray-800 flex items-center justify-center overflow-hidden">
                                                <img src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${item.title + i}`} alt="Avatar" />
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                    <div>
                                        <div className="text-[11px] text-gray-500 font-bold uppercase tracking-widest mb-3">教学/工作风格</div>
                                        <ul className="space-y-2">
                                            {item.style.map((s, i) => (
                                                <li key={i} className="text-xs text-gray-400 flex items-center gap-2">
                                                    <div className="w-1.5 h-1.5 rounded-full bg-purple-500/40"></div> {s}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                    <div>
                                        <div className="text-[11px] text-gray-500 font-bold uppercase tracking-widest mb-3">核心技能</div>
                                        <div className="flex flex-wrap gap-2">
                                            {item.skills.map((s, i) => (
                                                <span key={i} className="px-2.5 py-1 rounded-md bg-white/5 border border-white/5 text-[10px] text-gray-400">
                                                    {s}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Chapter 4 */}
                <section id="ch4" className="mb-24 scroll-mt-24 text-left">
                    <div className="flex items-center gap-4 mb-10">
                        <span className="text-5xl font-black text-white/5 select-none shrink-0">04</span>
                        <h2 className="text-2xl font-bold text-white tracking-tight">限制与约束技巧</h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div className="space-y-6">
                            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                <Target size={20} className="text-orange-400 shrink-0" />
                                结构化输出限制
                            </h3>
                            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 space-y-4">
                                <div className="p-4 rounded-xl bg-orange-400/5 border border-orange-400/10">
                                    <div className="text-[11px] text-orange-400/70 font-bold uppercase mb-2">重要 JSON 规则</div>
                                    <ul className="space-y-1 text-[10px] text-gray-500 list-disc pl-4">
                                        <li>所有字段必须存在，不能省略</li>
                                        <li>字符串用双引号，不要用单引号</li>
                                        <li>数字类型不加引号</li>
                                        <li>最后一个字段后面不要加逗号</li>
                                    </ul>
                                </div>
                                <div className="flex items-start gap-4">
                                    <div className="mt-1 w-4 h-4 bg-orange-400/20 border border-orange-400/40 rounded flex items-center justify-center shrink-0">
                                        <ChevronRight size={10} className="text-orange-400" />
                                    </div>
                                    <div>
                                        <p className="text-white font-bold text-sm">Markdown 表格/列表</p>
                                        <p className="text-gray-500 text-xs">通过指定列名，让 AI 输出严整的财务对比或清单。</p>
                                    </div>
                                </div>
                                <div className="flex items-start gap-4 group">
                                    <div className="mt-1 w-4 h-4 bg-orange-400/20 border border-orange-400/40 rounded flex items-center justify-center shrink-0">
                                        <ChevronRight size={10} className="text-orange-400" />
                                    </div>
                                    <div className="flex-grow">
                                        <p className="text-white font-bold text-sm">JSON 格式化</p>
                                        <p className="text-gray-500 text-xs">适合工程师与程序对接，强制每一项内容按 Key-Value 排列。</p>
                                        <div className="hidden group-hover:block mt-3 p-3 bg-black/40 rounded-lg border border-white/10 font-mono text-[9px] text-orange-300/80 animate-fadeIn">
                                            {"{"} "sentiment": "positive", "confidence": 0.95 {"}"}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="space-y-6">
                            <h3 className="text-lg font-bold text-white flex items-center gap-2">
                                <AlertTriangle size={20} className="text-red-400 shrink-0" />
                                多重限制机制
                            </h3>
                            <div className="p-6 rounded-2xl bg-white/5 border border-white/10 space-y-4">
                                {[
                                    { l: '字数限制', v: '严格控制在 50 字以内' },
                                    { l: '风格限制', v: '严禁使用专业术语，需通俗易懂' },
                                    { l: '逻辑限制', v: '先说结论，后说理由，分三点陈述' },
                                ].map((x, i) => (
                                    <div key={i} className="flex justify-between items-center py-1 border-b border-white/5 last:border-0 gap-4">
                                        <span className="text-gray-400 text-xs shrink-0">{x.l}</span>
                                        <span className="text-red-400/80 font-mono text-xs text-right">{x.v}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
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
                                    onClick={() => copyToClipboard('角色：你是某电商平台的客服代表，叫小美。\n任务：回复用户的售后咨询。\n\n语言限制：\n✅ 必须做到：\n- 称呼用"您"，显示尊重\n- 第一句表示理解和歉意（如果是问题）\n- 用"我们会..."展示负责态度\n- 结尾询问"还有什么可以帮您的吗？"\n\n❌ 严格禁止：\n- 使用"亲"、"哦"等过于随意的词\n- 推卸责任的表达（"这不是我们的问题"）\n- 空洞的套话（"感谢您的反馈"就结束）\n- 冰冷的机器人式回复\n\n风格要求：\n- 语气：专业且有温度\n- 节奏：先共情，再解决，后确认\n- 长度：80-150字\n\n格式要求：\n第一段：表示理解（20字内）\n第二段：解决方案（50-80字）\n第三段：后续跟进（30字内）')}
                                    className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-xl transition-all text-sm font-bold flex items-center gap-2 border border-white/10"
                                >
                                    <Copy size={16} /> 复制客服模板
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

                    <div className="p-8 rounded-[40px] bg-gradient-to-br from-purple-600/10 to-transparent border border-white/10 mb-12">
                        <h3 className="text-xl font-bold text-white mb-4">什么是 Few-Shot？</h3>
                        <p className="text-gray-400 leading-relaxed mb-8">
                            如果你无法用文字精准描述某种“感觉”，那就给 AI 两个例子。AI 具备强大的模式识别能力，能通过范例快速学习你的文风、逻辑和格式。
                        </p>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                            {[
                                { t: '1. 提供案例', d: '展示你想要的理想输出', c: 'bg-purple-500/20' },
                                { t: '2. 提炼规律', d: '让 AI 理解内在逻辑', c: 'bg-blue-500/20' },
                                { t: '3. 处理新文', d: '完成新任务的批处理', c: 'bg-green-500/20' },
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
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-24">
                        <div className="p-6 rounded-3xl bg-white/5 border border-white/10">
                            <h4 className="text-sm font-bold text-purple-400 mb-4 flex items-center gap-2">
                                <Zap size={14} /> 案例 1：小红书文风学习
                            </h4>
                            <div className="space-y-4">
                                <div className="p-3 bg-black/40 rounded-lg border border-white/5">
                                    <div className="text-[10px] text-gray-500 mb-2 font-mono">Input Examples</div>
                                    <p className="text-[11px] text-gray-400 italic">"示例1：💰省钱攻略｜这样买菜一个月省1000！主妇必看..."</p>
                                </div>
                                <div className="p-3 bg-purple-500/5 rounded-lg border border-purple-500/10">
                                    <div className="text-[10px] text-purple-400/70 mb-2 font-bold">提炼规律</div>
                                    <ul className="text-[10px] text-gray-500 space-y-1 list-disc pl-4">
                                        <li>Emoji 开头</li>
                                        <li>用 | 分隔制造悬念</li>
                                        <li>包含数字增加可信度</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        <div className="p-6 rounded-3xl bg-white/5 border border-white/10">
                            <h4 className="text-sm font-bold text-blue-400 mb-4 flex items-center justify-between">
                                <span className="flex items-center gap-2"><Database size={14} /> 案例 2：从文本提取 JSON</span>
                                <button
                                    onClick={() => copyToClipboard('你是内容分析专家。分析用户输入的{{user_content}}，提取关键信息。\n\n输出要求：必须是标准JSON格式，方便后续节点解析\n{\n  "sentiment": "positive|neutral|negative",\n  "keywords": ["关键词1", "关键词2", "关键词3"],\n  "category": "分类名称",\n  "summary": "一句话总结",\n  "action_items": [\n    "待办事项1",\n    "待办事项2"\n  ],\n  "confidence_score": 0.95\n}\n\n注意：\n- sentiment只能是这三个值之一\n- keywords最多5个\n- confidence_score是0-1之间的小数')}
                                    className="p-1.5 hover:bg-white/10 rounded-lg text-gray-500 hover:text-white transition-colors"
                                >
                                    <Copy size={12} />
                                </button>
                            </h4>
                            <div className="space-y-4">
                                <div className="p-3 bg-black/40 rounded-lg border border-white/5 overflow-x-auto">
                                    <div className="text-[10px] text-gray-500 mb-2 font-mono flex gap-2"><span className="text-green-400">✅ 标准化输出示例</span></div>
                                    <pre className="text-[10px] text-blue-300/80 font-mono leading-relaxed">
                                        {`{
  "sentiment": "positive|neutral|negative",
  "keywords": ["关键词1", "关键词2"],
  "category": "分类名称",
  "summary": "一句话总结",
  "action_items": [
    "待办事项1"
  ],
  "confidence_score": 0.95
}`}
                                    </pre>
                                </div>
                                <div className="p-3 bg-blue-500/5 rounded-lg border border-blue-500/10">
                                    <div className="text-[10px] text-blue-400/70 mb-2 font-bold block">严格注意项</div>
                                    <ul className="text-[10px] text-gray-400 space-y-1 list-disc pl-4">
                                        <li>sentiment 只能是预设三个值之一</li>
                                        <li>keywords 最多5个</li>
                                        <li>confidence_score 是0-1之间的小数</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        {[
                            { t: '文风模范', d: '学习特定作家、KOL 或企业的公关腔调', icon: CheckCircle2 },
                            { t: '链式思推', d: '引导 AI 按特定步骤进行深度逻辑推理', icon: Zap },
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
                    <h2 className="text-2xl md:text-3xl font-black mb-4">进阶学习建议</h2>
                    <p className="text-gray-600 mb-10 max-w-2xl mx-auto font-medium text-sm md:text-base">
                        提示词优化不是一次到位的艺术，而是不断调试的过程。建议从简单的 5W1H 开始，逐步增加约束和示例，最终构建属于你自己的 Prompt 库。
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
