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
  MessageSquare,
  FileText,
} from 'lucide-react';
import { getCurrentUser, isAuthenticated, saveAuth } from '@/services/auth';
import { getMe, updateProfile, recharge as rechargeApi, getUsageRecords, type UsageRecord } from '@/services/profile';

type TabId = 'profile' | 'balance' | 'recharge' | 'consumption' | 'records';

const Card: React.FC<{ children: React.ReactNode; className?: string }> = ({ children, className = '' }) => (
  <div className={`glass-morphism rounded-xl border border-white/10 p-6 ${className}`}>{children}</div>
);

const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'profile', label: '个人信息', icon: <User size={18} /> },
  { id: 'balance', label: '账户余额', icon: <Wallet size={18} /> },
  { id: 'recharge', label: '充值', icon: <CreditCard size={18} /> },
  { id: 'consumption', label: '累计消费', icon: <TrendingDown size={18} /> },
  { id: 'records', label: '调用记录', icon: <History size={18} /> },
];

function formatRecordTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso;
  }
}

const PersonalCenter: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<TabId>('profile');
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

  // 切换到「调用记录」时拉取
  useEffect(() => {
    if (activeTab === 'records' && isAuthenticated()) {
      setRecordsError(null);
      setRecordsLoading(true);
      getUsageRecords(50, 0)
        .then(setRecords)
        .catch((e) => setRecordsError(e instanceof Error ? e.message : '获取失败'))
        .finally(() => setRecordsLoading(false));
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

            {activeTab === 'balance' && (
              <Card className="animate-fadeIn">
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Wallet size={20} className="text-orange-400" />
                  账户余额
                </h2>
                {meLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <span className="w-8 h-8 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-4 p-6 rounded-xl bg-gradient-to-br from-orange-500/10 to-yellow-500/5 border border-orange-500/20">
                      <div className="w-14 h-14 rounded-full bg-orange-500/20 flex items-center justify-center">
                        <Coins size={28} className="text-orange-400" />
                      </div>
                      <div>
                        <p className="text-sm text-gray-400">当前余额（元）</p>
                        <p className="text-3xl font-bold text-white">{balance.toFixed(2)}</p>
                      </div>
                    </div>
                    <p className="text-sm text-gray-500 mt-4">当前仅图片生成计费，其余功能免费。余额用完后请及时充值。</p>
                    <button
                      onClick={() => setActiveTab('recharge')}
                      className="mt-4 flex items-center gap-2 px-5 py-2.5 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-lg transition-all"
                    >
                      <CreditCard size={18} />
                      去充值
                    </button>
                  </>
                )}
                {meError && <p className="text-sm text-red-400 mt-2">{meError}</p>}
              </Card>
            )}

            {activeTab === 'recharge' && (
              <Card className="animate-fadeIn">
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <CreditCard size={20} className="text-orange-400" />
                  充值
                </h2>
                <p className="text-gray-400 text-sm mb-4">当前仅图片生成计费。选择充值金额，确认后即时到账。</p>
                {rechargeError && <p className="text-sm text-red-400 mb-2">{rechargeError}</p>}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {[10, 30, 50, 100, 200, 500].map((amount) => (
                    <button
                      key={amount}
                      disabled={rechargeLoading}
                      onClick={() => handleRecharge(amount)}
                      className="py-4 px-4 rounded-xl border border-white/10 bg-white/5 hover:bg-orange-500/10 hover:border-orange-500/30 text-white font-medium transition-all disabled:opacity-50"
                    >
                      ¥{amount}
                    </button>
                  ))}
                </div>
                {rechargeLoading && <p className="text-sm text-gray-400 mt-2">充值处理中…</p>}
              </Card>
            )}

            {activeTab === 'consumption' && (
              <Card className="animate-fadeIn">
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <TrendingDown size={20} className="text-orange-400" />
                  累计消费
                </h2>
                {meLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <span className="w-8 h-8 border-2 border-orange-500/30 border-t-orange-500 rounded-full animate-spin" />
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-4 p-6 rounded-xl bg-white/5 border border-white/10">
                      <div className="w-14 h-14 rounded-full bg-white/10 flex items-center justify-center">
                        <TrendingDown size={28} className="text-gray-400" />
                      </div>
                      <div>
                        <p className="text-sm text-gray-400">累计消费（元）</p>
                        <p className="text-3xl font-bold text-white">¥{totalSpent.toFixed(2)}</p>
                      </div>
                    </div>
                    <p className="text-sm text-gray-500 mt-4">当前仅图片生成计费，此处统计即图片生成消耗金额。</p>
                  </>
                )}
                {meError && <p className="text-sm text-red-400 mt-2">{meError}</p>}
              </Card>
            )}

            {activeTab === 'records' && (
              <Card className="animate-fadeIn overflow-hidden">
                <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <History size={20} className="text-orange-400" />
                  调用记录
                </h2>
                <p className="text-gray-500 text-sm mb-3">当前仅有图片生成会产生计费记录。</p>
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
                                {r.record_type === 'chat' && <MessageSquare size={16} className="text-blue-400" />}
                                {r.record_type === 'knowledge' && <FileText size={16} className="text-purple-400" />}
                                {r.type_label}
                              </td>
                              <td className="py-3 text-gray-500">{formatRecordTime(r.created_at)}</td>
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
            )}
          </main>
        </div>
      </div>
    </div>
  );
};

export default PersonalCenter;
