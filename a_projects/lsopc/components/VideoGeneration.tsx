import React, { useState, useEffect, useCallback } from 'react';
import {
  getVideoOptions,
  createVideoText,
  createVideoSingleImage,
  createVideoDualImages,
  getVideoStatus,
  getVideoContent,
  getVideoHistory,
  ensureAbsoluteVideoUrl,
  type VideoOptions,
  type VideoHistoryItem,
} from '../services/video';
import { isAuthenticated } from '../services/auth';
import { formatBeijingTime } from '@/utils/date';
import { Loader2, Video, LogIn, CheckCircle2, Film, Image as ImageIcon, Images, History, Play } from 'lucide-react';

type Mode = 'text' | 'single' | 'dual';

const POLL_INTERVAL_MS = 6000; // 建议 5～10 秒轮询一次
const CONTENT_RETRY_DELAY_MS = 8000; // status=completed 后 content 可能稍晚就绪，首次失败时延迟重试

// 模型 ID → 普通人能看懂的简短说明（竖屏/横屏、标准/快速、图生）
const MODEL_LABELS: Record<string, string> = {
  'veo-3.1': '竖屏 · 标准',
  'veo-3.1-fast': '竖屏 · 快速',
  'veo-3.1-landscape': '横屏 · 标准',
  'veo-3.1-landscape-fast': '横屏 · 快速',
  'veo-3.1-fl': '竖屏 · 标准',
  'veo-3.1-fast-fl': '竖屏 · 快速',
  'veo-3.1-landscape-fl': '横屏 · 标准',
  'veo-3.1-landscape-fast-fl': '横屏 · 快速',
};

const MODE_HINTS: Record<Mode, string> = {
  text: '用文字描述你想要的画面，AI 自动生成视频',
  single: '上传一张图作为视频开头，AI 帮你生成后续动起来的效果',
  dual: '上传开头和结尾两张图，AI 自动生成中间的过渡动画',
};

const VideoGeneration: React.FC = () => {
  const [options, setOptions] = useState<VideoOptions | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [mode, setMode] = useState<Mode>('text');
  const [prompt, setPrompt] = useState('');
  const [modelText, setModelText] = useState('veo-3.1');
  const [modelImage, setModelImage] = useState('veo-3.1-landscape-fl');
  const [fileSingle, setFileSingle] = useState<File | null>(null);
  const [fileFirst, setFileFirst] = useState<File | null>(null);
  const [fileLast, setFileLast] = useState<File | null>(null);
  const [generating, setGenerating] = useState(false);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [statusText, setStatusText] = useState<string>('');
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoggedIn, setIsLoggedIn] = useState(isAuthenticated());
  const [history, setHistory] = useState<VideoHistoryItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    const handleAuthChange = () => setIsLoggedIn(isAuthenticated());
    window.addEventListener('storage', handleAuthChange);
    window.addEventListener('authStateChanged', handleAuthChange);
    return () => {
      window.removeEventListener('storage', handleAuthChange);
      window.removeEventListener('authStateChanged', handleAuthChange);
    };
  }, []);

  useEffect(() => {
    getVideoOptions()
      .then((data) => {
        setOptions(data);
        setModelText(data.text_model_default);
        setModelImage(data.image_model_default);
      })
      .catch(() => setError('加载配置失败'))
      .finally(() => setLoadingOptions(false));
  }, []);

  // 已登录时拉取最近 5 条视频生成记录
  useEffect(() => {
    if (!isAuthenticated()) return;
    setHistoryLoading(true);
    getVideoHistory(5)
      .then(setHistory)
      .catch(() => setHistory([]))
      .finally(() => setHistoryLoading(false));
  }, [isLoggedIn]);

  const fetchContentWithRetry = useCallback(async (id: string): Promise<boolean> => {
    try {
      const c = await getVideoContent(id);
      setVideoUrl(ensureAbsoluteVideoUrl(c.url) || null);
      getVideoHistory(5).then(setHistory);
      return true;
    } catch (contentErr) {
      const msg = contentErr instanceof Error ? contentErr.message : '获取视频失败';
      // 上游 content 可能稍晚就绪，首次失败时延迟重试一次
      if (msg.includes('就绪') || msg.includes('重试')) {
        await new Promise((r) => setTimeout(r, CONTENT_RETRY_DELAY_MS));
        try {
          const c = await getVideoContent(id);
          setVideoUrl(ensureAbsoluteVideoUrl(c.url) || null);
          getVideoHistory(5).then(setHistory);
          return true;
        } catch (e2) {
          setError(e2 instanceof Error ? e2.message : msg);
          return true;
        }
      }
      setError(msg);
      return true;
    }
  }, []);

  const pollStatus = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        const s = await getVideoStatus(id);
        setStatusText(s.status);
        if (s.status === 'completed') {
          return fetchContentWithRetry(id);
        }
        if (s.status === 'failed') {
          setError(s.detail || '视频生成失败');
          return true;
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : '查询失败');
        return true;
      }
      return false;
    },
    [fetchContentWithRetry]
  );

  useEffect(() => {
    if (!videoId || !generating) return;
    const done = async () => {
      const finished = await pollStatus(videoId);
      if (finished) setGenerating(false);
    };
    done();
    const t = setInterval(done, POLL_INTERVAL_MS);
    return () => clearInterval(t);
  }, [videoId, generating, pollStatus]);

  const handleLoginRequired = () => {
    window.dispatchEvent(new CustomEvent('openAuthModal'));
  };

  const handleSubmit = async () => {
    if (!prompt.trim()) {
      setError('请输入视频描述');
      return;
    }
    setGenerating(true);
    setError(null);
    setVideoUrl(null);
    setVideoId(null);
    setStatusText('');

    try {
      let id: string;
      if (mode === 'text') {
        const res = await createVideoText(prompt, modelText);
        id = res.video_id;
      } else if (mode === 'single') {
        if (!fileSingle) {
          setError('请先上传一张图作为视频开头');
          setGenerating(false);
          return;
        }
        const res = await createVideoSingleImage(prompt, fileSingle, modelImage);
        id = res.video_id;
      } else {
        if (!fileFirst || !fileLast) {
          setError('请上传开头和结尾两张图');
          setGenerating(false);
          return;
        }
        const res = await createVideoDualImages(prompt, fileFirst, fileLast, modelImage);
        id = res.video_id;
      }
      setVideoId(id);
      setStatusText('processing');
    } catch (e) {
      setError(e instanceof Error ? e.message : '创建失败');
      setGenerating(false);
    }
  };

  const resetForm = () => {
    setVideoId(null);
    setVideoUrl(null);
    setStatusText('');
    setError(null);
  };

  const modelsWithPrice = mode === 'text'
    ? (options?.text_models_with_price ?? [])
    : (options?.image_models_with_price ?? []);
  const currentModel = mode === 'text' ? modelText : modelImage;
  const setCurrentModel = mode === 'text' ? setModelText : setModelImage;

  if (loadingOptions) {
    return (
      <div className="flex justify-center items-center min-h-[80vh]">
        <div className="relative">
          <div className="w-16 h-16 rounded-full border-4 border-white/5 border-t-teal-500 animate-spin" />
          <Film className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-teal-400 animate-pulse" size={20} />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-80px)] pt-20 pb-8 px-4 md:px-8 max-w-[1600px] mx-auto animate-fadeIn">
      <div className="flex items-center gap-3 mb-8 pl-1">
        <div className="p-2 bg-gradient-to-br from-teal-500/20 to-cyan-500/20 rounded-xl border border-white/10">
          <Film className="text-teal-400" size={24} />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">AI 视频工坊</h1>
          <p className="text-sm text-gray-400 mt-0.5">用文字或图片，一键生成短视频</p>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-6 min-h-[500px]">
        <div className="w-full lg:w-[420px] flex-shrink-0 flex flex-col gap-4">
          <div className="bg-[#0A0A0A]/80 backdrop-blur-xl border border-white/10 rounded-2xl p-5 flex-shrink-0">
            <div className="flex gap-2 mb-2">
              {(['text', 'single', 'dual'] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => { setMode(m); resetForm(); }}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                    mode === m ? 'bg-teal-500/20 text-teal-400 border border-teal-500/40' : 'bg-white/5 text-gray-400 border border-transparent hover:bg-white/10'
                  }`}
                >
                  {m === 'text' && <Video size={16} />}
                  {m === 'single' && <ImageIcon size={16} />}
                  {m === 'dual' && <Images size={16} />}
                  {m === 'text' && '用文字生成'}
                  {m === 'single' && '用一张图生成'}
                  {m === 'dual' && '用两张图生成'}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-500 mb-4">{MODE_HINTS[mode]}</p>

            <div className="space-y-4">
              <div>
                <label className="text-sm font-semibold text-gray-200 block mb-1">视频描述</label>
                <p className="text-xs text-gray-500 mb-1">用一句话描述你想看到的画面</p>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder={
                    mode === 'text'
                      ? '例如：一只猫咪在阳光下的花园里漫步'
                      : mode === 'single'
                        ? '例如：让这张图动起来，镜头慢慢往前推'
                        : '例如：从第一张图慢慢变到第二张图，镜头不动'
                  }
                  className="w-full h-24 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-teal-500/50 resize-none text-sm"
                  disabled={generating}
                />
              </div>

              {(mode === 'text' || mode === 'single' || mode === 'dual') && modelsWithPrice.length > 0 && (
                <div>
                  <label className="text-sm font-semibold text-gray-200 block mb-1">选择视频规格</label>
                  <p className="text-xs text-gray-500 mb-2">竖屏适合手机观看，横屏适合电脑；快速规格出片更快、价格更低</p>
                  <div className="flex flex-wrap gap-2">
                    {modelsWithPrice.map((m) => (
                      <button
                        key={m.model}
                        onClick={() => setCurrentModel(m.model)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                          currentModel === m.model ? 'bg-teal-500/20 text-teal-400 border border-teal-500/40' : 'bg-white/5 text-gray-400 border border-transparent hover:bg-white/10'
                        }`}
                      >
                        {MODEL_LABELS[m.model] ?? m.model}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {mode === 'single' && (
                <div>
                  <label className="text-sm font-semibold text-gray-200 block mb-1">上传一张图（作为视频开头画面）</label>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(e) => setFileSingle(e.target.files?.[0] || null)}
                    className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-teal-500/20 file:text-teal-400"
                    disabled={generating}
                  />
                </div>
              )}

              {mode === 'dual' && (
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-semibold text-gray-200 block mb-1">开头画面（第一张图）</label>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={(e) => setFileFirst(e.target.files?.[0] || null)}
                      className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-teal-500/20 file:text-teal-400"
                      disabled={generating}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-semibold text-gray-200 block mb-1">结尾画面（第二张图）</label>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={(e) => setFileLast(e.target.files?.[0] || null)}
                      className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-teal-500/20 file:text-teal-400"
                      disabled={generating}
                    />
                  </div>
                </div>
              )}

              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">{error}</div>
              )}

              {!isLoggedIn ? (
                <button
                  onClick={handleLoginRequired}
                  className="w-full py-4 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-semibold rounded-xl flex items-center justify-center gap-2"
                >
                  <LogIn size={18} className="text-gray-400" />
                  登录后开始创作
                </button>
              ) : (
                <button
                  onClick={handleSubmit}
                  disabled={generating || !prompt.trim()}
                  className="w-full py-4 bg-gradient-to-r from-teal-600 to-cyan-600 hover:from-teal-500 hover:to-cyan-500 text-white font-bold rounded-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {generating ? (
                    <>
                      <Loader2 className="animate-spin" size={18} />
                      任务已创建，等待生成…
                    </>
                  ) : (
                    <>
                      <Film size={18} />
                      开始生成
                    </>
                  )}
                </button>
              )}

              {videoUrl && (
                <button
                  onClick={resetForm}
                  className="w-full py-2 text-sm text-gray-400 hover:text-white border border-white/10 rounded-lg"
                >
                  重新生成
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="flex-1 min-w-0 bg-[#0A0A0A]/50 backdrop-blur-sm border border-white/5 rounded-2xl overflow-hidden flex flex-col">
          <div className="h-14 border-b border-white/5 flex items-center justify-between px-6 bg-black/20">
            <span className="text-sm text-gray-400">视频预览</span>
            {videoUrl && (
              <span className="text-xs text-green-400 flex items-center gap-1.5 bg-green-500/10 px-2.5 py-1 rounded-full border border-green-500/20">
                <CheckCircle2 size={12} />
                生成完成
              </span>
            )}
          </div>
          <div className="flex-1 flex items-center justify-center p-8">
            {generating && !videoUrl ? (
              <div className="text-center space-y-6">
                <div className="relative">
                  <div className="w-32 h-32 rounded-full border-2 border-white/5 border-t-teal-500 animate-spin mx-auto" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Film className="text-teal-400" size={40} />
                  </div>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">正在生成视频，请稍候…</h3>
                  <p className="text-gray-400 mt-1">通常需要 1～3 分钟，完成后会自动显示</p>
                </div>
              </div>
            ) : videoUrl ? (
              <div className="w-full max-w-3xl">
                <video
                  src={videoUrl}
                  controls
                  autoPlay
                  loop
                  muted
                  playsInline
                  className="w-full rounded-xl shadow-2xl border border-white/10"
                />
              </div>
            ) : (
              <div className="text-center space-y-6 opacity-40">
                <div className="w-40 h-40 rounded-2xl bg-white/5 border-2 border-dashed border-white/10 flex items-center justify-center mx-auto">
                  <Film className="text-white/20" size={64} />
                </div>
                <div>
                  <p className="text-white text-lg font-medium">视频会显示在这里</p>
                  <p className="text-sm text-gray-400 mt-1">点击「开始生成」并等待几分钟，生成完成后将自动播放</p>
                </div>
              </div>
            )}
          </div>
          {isLoggedIn && (
            <div className="border-t border-white/5 px-4 py-3 bg-black/10">
              <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
                <History size={14} />
                最近生成（最多 5 条）
              </div>
              {historyLoading ? (
                <div className="text-xs text-gray-500">加载中…</div>
              ) : history.length === 0 ? (
                <div className="text-xs text-gray-500">暂无历史记录</div>
              ) : (
                <ul className="space-y-2">
                  {history.map((item) => (
                    <li
                      key={item.video_id}
                      className="flex items-start justify-between gap-2 text-xs group border-b border-white/5 pb-2 last:border-0 last:pb-0"
                    >
                      <div className="min-w-0 flex-1">
                        {item.prompt_summary && (
                          <p className="text-gray-300 truncate" title={item.prompt_summary}>
                            {item.prompt_summary}
                          </p>
                        )}
                        <p className="text-gray-500 mt-0.5">
                          {formatBeijingTime(item.created_at)} · {MODEL_LABELS[item.model] ?? item.model}
                        </p>
                      </div>
                      {item.video_url ? (
                        <button
                          type="button"
                          onClick={() => setVideoUrl(ensureAbsoluteVideoUrl(item.video_url) ?? null)}
                          className="shrink-0 flex items-center gap-1 text-teal-400 hover:text-teal-300 mt-0.5"
                        >
                          <Play size={12} />
                          播放
                        </button>
                      ) : (
                        <span className="shrink-0 text-gray-500 mt-0.5">未就绪</span>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VideoGeneration;
