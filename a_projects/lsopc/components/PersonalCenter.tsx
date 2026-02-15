import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  User,
  Wallet,
  CreditCard,
  TrendingDown,
  History,
  ArrowLeft,
  Save,
  ChevronRight,
  Coins,
  Image as ImageIcon,
  Video,
  MessageSquare,
  FileText,
  Info,
} from 'lucide-react';
import { getCurrentUser, isAuthenticated, saveAuth } from '@/services/auth';
import { getMe, updateProfile, recharge as rechargeApi, getUsageRecords, type UsageRecord } from '@/services/profile';
import { getImageOptions } from '@/services/image';
import { getVideoOptions } from '@/services/video';
import { formatBeijingTime } from '@/utils/date';

type TabId = 'profile' | 'account' | 'pricing';

const VIDEO_MODEL_LABELS: Record<string, string> = {
  'veo-3.1': '竖屏 · 标准',
  'veo-3.1-fast': '竖屏 · 快速',
  'veo-3.1-landscape': '横屏 · 标准',
  'veo-3.1-landscape-fast': '横屏 · 快速',
  'veo-3.1-fl': '竖屏 · 标准（图生）',
  'veo-3.1-fast-fl': '竖屏 · 快速（图生）',
  'veo-3.1-landscape-fl': '横屏 · 标准（图生）',
  'veo-3.1-landscape-fast-fl': '横屏 · 快速（图生）',
};

const Card: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <div className={`glass-morphism rounded-xl border border-white/10 p-6 ${className}`}>{children}</div>
);

const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'profile', label: '个人信息', icon: <User size={18} /> },
  { id: 'account', label: '账户与消费', icon: <Wallet size={18} /> },
  { id: 'pricing', label: '费用说明', icon: <Info size={18} /> },
];

const PersonalCenter: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabId>('account');
  const [profile, setProfile] = useState({ username: '', email: '', nickname: '' });
  const [balance, setBalance] = useState<number>(0);
  const [totalSpent, setTotalSpent] = useState<number>(0);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [records, setRecords] = useState<UsageRecord[]>([]);
  const [recordsLoading, setRecordsLoading] = useState(false);
  const [recordsError, setRecordsError] = useState<string | null>(null);
  const [rechargeLoading, setRechargeLoading] = useState(false);
  const [rechargeError, setRechargeError] = useState<string | null>(null);
  const [meLoading, setMeLoading] = useState(true);
  const [meError, setMeError] = useState<string | null>(null);
  const [imagePricing, setImagePricing] = useState<{ cny_per_image?: string } | null>(null);
  const [videoPricing, setVideoPricing] = useState<{
    text_models_with_price?: { model: string; price_cny: number }[];
    image_models_with_price?: { model: string; price_cny: number }[];
  } | null>(null);
  const [pricingLoading, setPricingLoading] = useState(false);

  // 拉取当前用户信息与余额
  const fetchMe = async () => {
    try {
      setMeError(null);
      const data = await getMe();
      setProfile({
        username: data.username,
        email: data.email ?? '',
        nickname: data.nickname ?? data.username ?? '',
      });
      setBalance(data.balance ?? 0);
      setTotalSpent(data.total_spent ?? 0);
      const token = localStorage.getItem('auth_token');
      if (token) {
        saveAuth(token, { username: data.username, email: data.email ?? undefined, nickname: data.nickname ?? undefined });
      }
    } catch (e) {
      setMeError(e instanceof Error ? e.message : '获取用户信息失败');
    } finally {
      setMeLoading(false);
    }
  };

  useEffect(() => {
    if (!isAuthenticated()) {
      navigate('/', { replace: true });
      return;
    }
    fetchMe();
  }, [navigate]);

  // 进入「账户与消费」时拉取调用记录
  useEffect(() => {
    if (activeTab === 'account' && isAuthenticated()) {
      setRecordsError(null);
      setRecordsLoading(true);
      getUsageRecords(50, 0)
        .then(setRecords)
        .catch((e) => setRecordsError(e instanceof Error ? e.message : '获取失败'))
        .finally(() => setRecordsLoading(false));
    }
  }, [activeTab]);

  // 进入「费用说明」时拉取价格表
  useEffect(() => {
    if (activeTab === 'pricing') {
      setPricingLoading(true);
      Promise.all([getImageOptions(), getVideoOptions()])
        .then(([img, vid]) => {
          setImagePricing((img as { pricing?: { cny_per_image?: string } }).pricing ?? null);
          setVideoPricing({
            text_models_with_price: (vid as { text_models_with_price?: { model: string; price_cny: number }[] }).text_models_with_price ?? [],
            image_models_with_price: (vid as { image_models_with_price?: { model: string; price_cny: number }[] }).image_models_with_price ?? [],
          });
        })
        .catch(() => {
          setImagePricing(null);
          setVideoPricing(null);
        })
        .finally(() => setPricingLoading(false));
    }
  }, [activeTab]);

  const handleSaveProfile = async () => {
    setProfileSaving(true);
    setProfileSaved(false);
    setProfileError(null);
    try {
      const data = await updateProfile({ email: profile.email || undefined, nickname: profile.nickname || undefined });
      setProfile((p) => ({ ...p, email: data.email ?? '', nickname: data.nickname ?? p.username }));
      setProfileSaved(true);
      setTimeout(() => setProfileSaved(false), 2000);
      const token = localStorage.getItem('auth_token');
      if (token) saveAuth(token, { username: data.username, email: data.email ?? undefined, nickname: data.nickname ?? undefined });
    } catch (e) {
      setProfileError(e instanceof Error ? e.message : '保存失败');
    } finally {
      setProfileSaving(false);
    }
  };

  const handleRecharge = async (amount: number) => {
    setRechargeLoading(true);
    setRechargeError(null);
    try {
      const res = await rechargeApi(amount);
      setBalance(res.balance);
      setRechargeLoading(false);
    } catch (e) {
      setRechargeError(e instanceof Error ? e.message : '充值失败');
    } finally {
      setRechargeLoading(false);
    }
  };

  if (!isAuthenticated()) return null;

  return (
    <div className="pt-20 pb-12 min-h-screen">
      <div className="max-w-5xl mx-auto px-4">
        {/* 顶部返回 */}
        <div className="flex items-center justify-between mb-6 animate-fadeIn">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-gray-400 hover:text-white transition-all text-sm"
          >
            <ArrowLeft size={18} />
            返回首页
          </button>
          <h1 className="text-xl font-bold text-white/90">个人中心</h1>
          <div className="w-24" />
        </div>

        <div className="flex flex-col md:flex-row gap-6 animate-fadeIn">
          {/* 左侧导航 - 桌面 */}
          <aside className="md:w-52 flex-shrink-0">
            <nav className="glass-morphism rounded-xl border border-white/10 overflow-hidden p-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center justify-between gap-2 px-4 py-3 rounded-lg text-left text-sm font-medium transition-all ${
                    activeTab === tab.id
                      ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                      : 'text-gray-400 hover:text-white hover:bg-white/5 border border-transparent'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    {tab.icon}
                    {tab.label}
                  </span>
                  <ChevronRight size={16} className={activeTab === tab.id ? 'text-orange-400' : 'text-gray-500'} />
                </button>
              ))}
            </nav>
          </aside>

          {/* 移动端 Tab 条 */}
          <div className="md:hidden flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                  activeTab === tab.id ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' : 'bg-white/5 text-gray-400 border border-white/10'
                }`}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>

          {/* 主内容区 */}
          <main className="flex-1 min-w-0">
            {activeTab === 'profile' && (
              <Card className="animate-fadeIn">
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <User size={20} className="text-orange-400" />
                  个人信息
                </h2>
                {meLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <span className="w-8 h-8 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
                  </div>
                ) : (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">用户名</label>
                    <input
                      type="text"
                      value={profile.username}
                      readOnly
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2.5 text-white/80 cursor-not-allowed"
                    />
                    <p className="text-xs text-gray-500 mt-1">用户名不可修改</p>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">昵称</label>
                    <input
                      type="text"
                      value={profile.nickname}
                      onChange={(e) => setProfile((p) => ({ ...p, nickname: e.target.value }))}
                      placeholder="选填"
                      className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">邮箱</label>
                    <input
                      type="email"
                      value={profile.email}
                      onChange={(e) => setProfile((p) => ({ ...p, email: e.target.value }))}
                      placeholder="your@email.com"
                      className="w-full bg-black/20 border border-white/10 rounded-lg px-4 py-2.5 text-white focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/50"
                    />
                  </div>
                  {profileError && <p className="text-sm text-red-400">{profileError}</p>}
                  <button
                    onClick={handleSaveProfile}
                    disabled={profileSaving}
                    className="flex items-center gap-2 px-5 py-2.5 bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white font-medium rounded-lg transition-all"
                  >
                    {profileSaving ? (
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    ) : (
                      <Save size={18} />
                    )}
                    {profileSaved ? '已保存' : '保存修改'}
                  </button>
                </div>
                )}
                {meError && <p className="text-sm text-red-400 mt-2">{meError}</p>}
              </Card>
            )}

            {activeTab === 'account' && (
              <div className="space-y-6 animate-fadeIn">
                {/* 1. 账户余额 + 累计消费 并排 */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Card>
                    <h2 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
                      <Wallet size={18} className="text-orange-400" />
                      账户余额
                    </h2>
                    {meLoading ? (
                      <div className="flex justify-center py-6">
                        <span className="w-6 h-6 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center gap-3 p-4 rounded-xl bg-gradient-to-br from-orange-500/10 to-yellow-500/5 border border-orange-500/20">
                          <div className="w-12 h-12 rounded-full bg-orange-500/20 flex items-center justify-center">
                            <Coins size={24} className="text-orange-400" />
                          </div>
                          <div>
                            <p className="text-xs text-gray-400">当前余额（元）</p>
                            <p className="text-2xl font-bold text-white">{balance.toFixed(2)}</p>
                          </div>
                        </div>
                        <p className="text-xs text-gray-500 mt-3">图片生成与视频生成计费，余额用完后请充值。</p>
                      </>
                    )}
                    {meError && <p className="text-sm text-red-400 mt-2">{meError}</p>}
                  </Card>
                  <Card>
                    <h2 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
                      <TrendingDown size={18} className="text-orange-400" />
                      累计消费
                    </h2>
                    {meLoading ? (
                      <div className="flex justify-center py-6">
                        <span className="w-6 h-6 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center gap-3 p-4 rounded-xl bg-white/5 border border-white/10">
                          <div className="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center">
                            <TrendingDown size={24} className="text-gray-400" />
                          </div>
                          <div>
                            <p className="text-xs text-gray-400">累计消费（元）</p>
                            <p className="text-2xl font-bold text-white">¥{totalSpent.toFixed(2)}</p>
                          </div>
                        </div>
                        <p className="text-xs text-gray-500 mt-3">统计图片生成与视频生成的消费总额。</p>
                      </>
                    )}
                  </Card>
                </div>

                {/* 2. 充值 */}
                <Card>
                  <h2 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
                    <CreditCard size={18} className="text-orange-400" />
                    充值
                  </h2>
                  <p className="text-gray-400 text-sm mb-3">选择金额，确认后即时到账。</p>
                  {rechargeError && <p className="text-sm text-red-400 mb-2">{rechargeError}</p>}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {[10, 30, 50, 100, 200, 500].map((amount) => (
                      <button
                        key={amount}
                        disabled={rechargeLoading}
                        onClick={() => handleRecharge(amount)}
                        className="py-3 px-4 rounded-xl border border-white/10 bg-white/5 hover:bg-orange-500/10 hover:border-orange-500/30 text-white font-medium transition-all disabled:opacity-50"
                      >
                        ¥{amount}
                      </button>
                    ))}
                  </div>
                  {rechargeLoading && <p className="text-sm text-gray-400 mt-2">充值处理中…</p>}
                </Card>

                {/* 3. 调用记录（图片生成 + 视频生成） */}
                <Card className="overflow-hidden">
                  <h2 className="text-base font-semibold text-white mb-2 flex items-center gap-2">
                    <History size={18} className="text-orange-400" />
                    调用记录
                  </h2>
                  <p className="text-gray-500 text-sm mb-3">包含图片生成与视频生成的计费记录，按时间倒序。</p>
                  {recordsError && <p className="text-sm text-red-400 mb-2">{recordsError}</p>}
                  {recordsLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <span className="w-8 h-8 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-left text-gray-400 border-b border-white/10">
                            <th className="pb-3 font-medium">类型</th>
                            <th className="pb-3 font-medium">时间</th>
                            <th className="pb-3 font-medium">次数</th>
                            <th className="pb-3 font-medium">消耗（元）</th>
                          </tr>
                        </thead>
                        <tbody>
                          {records.length === 0 ? (
                            <tr>
                              <td colSpan={4} className="py-8 text-center text-gray-500">暂无调用记录</td>
                            </tr>
                          ) : (
                            records.map((r) => (
                              <tr key={r.id} className="border-b border-white/5 text-gray-300">
                                <td className="py-3 flex items-center gap-2">
                                  {r.record_type === 'image' && <ImageIcon size={16} className="text-pink-400" />}
                                  {r.record_type === 'video' && <Video size={16} className="text-teal-400" />}
                                  {r.record_type === 'chat' && <MessageSquare size={16} className="text-blue-400" />}
                                  {r.record_type === 'knowledge' && <FileText size={16} className="text-purple-400" />}
                                  {r.type_label}
                                </td>
                                <td className="py-3 text-gray-500">{formatBeijingTime(r.created_at)}</td>
                                <td className="py-3">{r.count}</td>
                                <td className="py-3 text-orange-400/90">¥{r.amount.toFixed(2)}</td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Card>
              </div>
            )}

            {activeTab === 'pricing' && (
              <div className="animate-fadeIn space-y-6 max-w-2xl">
                <div className="flex items-center gap-2 mb-1">
                  <Info size={20} className="text-orange-400" />
                  <h2 className="text-lg font-semibold text-white">费用说明</h2>
                </div>
                <p className="text-gray-500 text-sm">以下为图片生成与视频生成的计费标准，实际扣款以生成成功为准。</p>

                {pricingLoading ? (
                  <div className="flex justify-center py-12">
                    <span className="w-8 h-8 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
                  </div>
                ) : (
                  <>
                    {/* 一块：图片生成 */}
                    <Card>
                      <h3 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
                        <ImageIcon size={18} className="text-pink-400" />
                        图片生成
                      </h3>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="text-left text-gray-400 border-b border-white/10">
                              <th className="pb-2 font-medium">说明</th>
                              <th className="pb-2 font-medium text-right">价格</th>
                            </tr>
                          </thead>
                          <tbody className="text-gray-300">
                            {imagePricing?.cny_per_image ? (
                              <tr className="border-b border-white/5">
                                <td className="py-2">按张计费</td>
                                <td className="py-2 text-right text-orange-400/90">{imagePricing.cny_per_image}</td>
                              </tr>
                            ) : (
                              <tr>
                                <td colSpan={2} className="py-2 text-gray-500">暂无价格信息</td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </Card>

                    {/* 一块：视频生成 */}
                    <Card>
                      <h3 className="text-base font-semibold text-white mb-3 flex items-center gap-2">
                        <Video size={18} className="text-teal-400" />
                        视频生成
                      </h3>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="text-left text-gray-400 border-b border-white/10">
                              <th className="pb-2 font-medium">规格</th>
                              <th className="pb-2 font-medium text-right">价格</th>
                            </tr>
                          </thead>
                          <tbody className="text-gray-300">
                            {videoPricing?.text_models_with_price?.map((m) => (
                              <tr key={m.model} className="border-b border-white/5">
                                <td className="py-2">{VIDEO_MODEL_LABELS[m.model] ?? m.model}</td>
                                <td className="py-2 text-right text-orange-400/90">¥{m.price_cny.toFixed(2)}/次</td>
                              </tr>
                            ))}
                            {videoPricing?.image_models_with_price?.length
                              ? videoPricing.image_models_with_price.map((m) => (
                                  <tr key={m.model} className="border-b border-white/5">
                                    <td className="py-2">{VIDEO_MODEL_LABELS[m.model] ?? m.model}</td>
                                    <td className="py-2 text-right text-orange-400/90">¥{m.price_cny.toFixed(2)}/次</td>
                                  </tr>
                                ))
                              : null}
                            {(!videoPricing?.text_models_with_price?.length && !videoPricing?.image_models_with_price?.length) && (
                              <tr>
                                <td colSpan={2} className="py-2 text-gray-500">暂无价格信息</td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </Card>
                  </>
                )}
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
};

export default PersonalCenter;
