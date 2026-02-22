import React, { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { X, Lock, Loader2, Sparkles, LogIn, Smartphone, Eye, EyeOff } from 'lucide-react';
import { saveAuth, sendSmsCode, loginBySms, login, setPassword } from '../services/auth';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthSuccess: (displayName: string) => void;
}

type Step = 'password' | 'sms' | 'set_password';

const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onAuthSuccess }) => {
  const [step, setStep] = useState<Step>('password');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [phone, setPhone] = useState('');
  const [password, setPasswordValue] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [smsCode, setSmsCode] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [newPassword, setNewPassword] = useState('');
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [pendingToken, setPendingToken] = useState<string | null>(null);
  const [pendingUser, setPendingUser] = useState<{ username: string; nickname?: string } | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    let t: ReturnType<typeof setInterval> | null = null;
    if (countdown > 0) {
      t = setInterval(() => setCountdown((c) => (c <= 1 ? 0 : c - 1)), 1000);
    }
    return () => { if (t) clearInterval(t); };
  }, [isOpen, countdown]);

  const resetForm = useCallback(() => {
    setStep('password');
    setPhone('');
    setPasswordValue('');
    setSmsCode('');
    setNewPassword('');
    setNewPasswordConfirm('');
    setError(null);
    setSuccess(null);
    setCountdown(0);
    setPendingToken(null);
    setPendingUser(null);
  }, []);

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSendCode = async () => {
    const p = phone.trim();
    if (!/^\d{11}$/.test(p)) {
      setError('请输入 11 位手机号');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      await sendSmsCode(p);
      setSuccess('验证码已发送，请查收短信');
      setCountdown(60);
    } catch (err) {
      setError(err instanceof Error ? err.message : '发送失败');
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const p = phone.trim();
    if (!/^\d{11}$/.test(p)) {
      setError('请输入 11 位手机号');
      return;
    }
    if (!password) {
      setError('请输入密码');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await login({ username: p, password });
      saveAuth(res.access_token, res.user);
      onAuthSuccess(res.user.nickname || res.user.username || p);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSmsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const p = phone.trim();
    const code = smsCode.trim();
    if (!/^\d{11}$/.test(p)) {
      setError('请输入 11 位手机号');
      return;
    }
    if (!code) {
      setError('请输入验证码');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await loginBySms(p, code);
      saveAuth(res.access_token, res.user);
      if (res.need_set_password) {
        setPendingToken(res.access_token);
        setPendingUser(res.user);
        setStep('set_password');
        setSuccess('请设置登录密码，之后可使用手机号+密码登录');
      } else {
        onAuthSuccess(res.user.nickname || res.user.username || p);
        handleClose();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 6) {
      setError('密码至少 6 位');
      return;
    }
    if (newPassword !== newPasswordConfirm) {
      setError('两次输入的密码不一致');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await setPassword(newPassword);
      if (pendingToken && pendingUser) {
        saveAuth(pendingToken, pendingUser);
        onAuthSuccess(pendingUser.nickname || pendingUser.username || phone);
      }
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '设置失败');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const msg = error || success;

  return createPortal(
    <div className="fixed inset-0 overflow-y-auto" style={{ zIndex: 99999 }}>
      <div className="fixed inset-0 bg-black/80 backdrop-blur-md" onClick={handleClose} />
      <div className="min-h-screen px-4 text-center">
        <span className="inline-block h-screen align-middle" aria-hidden="true">&#8203;</span>
        <div className="inline-block w-full max-w-lg text-left align-middle bg-gradient-to-b from-gray-900 via-gray-900 to-black border border-white/10 rounded-3xl shadow-2xl overflow-hidden relative my-8 z-10">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-32 bg-gradient-to-r from-orange-500/30 via-yellow-500/20 to-orange-500/30 blur-3xl" />
          <button
            onClick={handleClose}
            className="absolute top-5 right-5 z-10 p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-all duration-200"
          >
            <X size={20} />
          </button>

          {/* 默认：手机号+密码登录 */}
          {step === 'password' && (
            <>
              <div className="relative pt-8 pb-2 text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-500 to-yellow-500 shadow-lg shadow-orange-500/30 mb-4">
                  <LogIn size={28} className="text-white" />
                </div>
                <h2 className="text-2xl font-bold text-white">手机号登录</h2>
                <p className="text-gray-400 mt-2 text-sm">使用手机号与密码登录，减少验证码发送</p>
              </div>
              <form onSubmit={handlePasswordLogin} className="px-8 py-4 pb-8 space-y-5">
                {msg && (
                  <div className={`p-4 rounded-xl text-sm flex items-center gap-3 ${error ? 'bg-red-500/10 border border-red-500/30 text-red-400' : 'bg-green-500/10 border border-green-500/30 text-green-400'}`}>
                    {error ? <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" /> : <Sparkles size={16} />}
                    {msg}
                  </div>
                )}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300 flex items-center gap-2">
                    <Smartphone size={14} className="text-orange-400" />
                    手机号
                  </label>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 11))}
                    placeholder="11 位手机号"
                    maxLength={11}
                    className="w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-orange-500/50"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300 flex items-center gap-2">
                    <Lock size={14} className="text-orange-400" />
                    密码
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPasswordValue(e.target.value)}
                      placeholder="请输入密码"
                      className="w-full px-4 py-3.5 pr-12 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-orange-500/50"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white"
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-4 mt-2 bg-gradient-to-r from-orange-500 to-yellow-500 hover:from-orange-600 hover:to-yellow-600 text-white font-semibold rounded-xl shadow-lg shadow-orange-500/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? <Loader2 size={20} className="animate-spin" /> : <><LogIn size={20} /> 登录</>}
                </button>
                <button
                  type="button"
                  onClick={() => { setStep('sms'); setError(null); setSuccess(null); }}
                  className="w-full py-3 border border-white/10 hover:border-orange-500/50 text-gray-400 hover:text-orange-400 text-sm rounded-xl transition-all"
                >
                  没有密码？使用验证码登录/注册
                </button>
              </form>
            </>
          )}

          {/* 验证码登录/注册 */}
          {step === 'sms' && (
            <>
              <div className="relative pt-8 pb-2 text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-500 to-yellow-500 shadow-lg shadow-orange-500/30 mb-4">
                  <Smartphone size={28} className="text-white" />
                </div>
                <h2 className="text-2xl font-bold text-white">验证码登录 / 注册</h2>
                <p className="text-gray-400 mt-2 text-sm">未注册手机号将自动创建账号，首次需设置密码</p>
              </div>
              <form onSubmit={handleSmsSubmit} className="px-8 py-4 pb-8 space-y-5">
                {msg && (
                  <div className={`p-4 rounded-xl text-sm flex items-center gap-3 ${error ? 'bg-red-500/10 border border-red-500/30 text-red-400' : 'bg-green-500/10 border border-green-500/30 text-green-400'}`}>
                    {error ? <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" /> : <Sparkles size={16} />}
                    {msg}
                  </div>
                )}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300 flex items-center gap-2">手机号</label>
                  <div className="flex gap-2">
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value.replace(/\D/g, '').slice(0, 11))}
                      placeholder="11 位手机号"
                      maxLength={11}
                      className="flex-1 px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-orange-500/50"
                    />
                    <button
                      type="button"
                      onClick={handleSendCode}
                      disabled={loading || countdown > 0}
                      className="px-5 py-3.5 bg-white/10 hover:bg-white/20 border border-white/10 rounded-xl text-white text-sm font-medium whitespace-nowrap disabled:opacity-50"
                    >
                      {countdown > 0 ? `${countdown}s 后重发` : '获取验证码'}
                    </button>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300 flex items-center gap-2">验证码</label>
                  <input
                    type="text"
                    value={smsCode}
                    onChange={(e) => setSmsCode(e.target.value.replace(/\D/g, '').slice(0, 8))}
                    placeholder="请输入短信验证码"
                    maxLength={8}
                    className="w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-orange-500/50"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-4 mt-2 bg-gradient-to-r from-orange-500 to-yellow-500 hover:from-orange-600 hover:to-yellow-600 text-white font-semibold rounded-xl shadow-lg shadow-orange-500/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? <Loader2 size={20} className="animate-spin" /> : <><LogIn size={20} /> 登录 / 注册</>}
                </button>
                <button
                  type="button"
                  onClick={() => { setStep('password'); setError(null); setSuccess(null); }}
                  className="w-full py-3 border border-white/10 hover:border-orange-500/50 text-gray-400 hover:text-orange-400 text-sm rounded-xl transition-all"
                >
                  已有密码？使用手机号+密码登录
                </button>
              </form>
            </>
          )}

          {/* 首次设置密码 */}
          {step === 'set_password' && (
            <>
              <div className="relative pt-8 pb-2 text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-500 to-yellow-500 shadow-lg shadow-orange-500/30 mb-4">
                  <Lock size={28} className="text-white" />
                </div>
                <h2 className="text-2xl font-bold text-white">设置登录密码</h2>
                <p className="text-gray-400 mt-2 text-sm">设置后可使用手机号+密码登录，减少验证码发送</p>
              </div>
              <form onSubmit={handleSetPassword} className="px-8 py-4 pb-8 space-y-5">
                {msg && (
                  <div className={`p-4 rounded-xl text-sm flex items-center gap-3 ${error ? 'bg-red-500/10 border border-red-500/30 text-red-400' : 'bg-green-500/10 border border-green-500/30 text-green-400'}`}>
                    {error ? <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" /> : <Sparkles size={16} />}
                    {msg}
                  </div>
                )}
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300 flex items-center gap-2">新密码</label>
                  <div className="relative">
                    <input
                      type={showNewPassword ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="至少 6 位"
                      minLength={6}
                      className="w-full px-4 py-3.5 pr-12 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-orange-500/50"
                    />
                    <button type="button" onClick={() => setShowNewPassword(!showNewPassword)} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white">
                      {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300 flex items-center gap-2">确认密码</label>
                  <input
                    type="password"
                    value={newPasswordConfirm}
                    onChange={(e) => setNewPasswordConfirm(e.target.value)}
                    placeholder="再次输入密码"
                    className="w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-orange-500/50"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-4 mt-2 bg-gradient-to-r from-orange-500 to-yellow-500 hover:from-orange-600 hover:to-yellow-600 text-white font-semibold rounded-xl shadow-lg shadow-orange-500/30 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? <Loader2 size={20} className="animate-spin" /> : <><Sparkles size={20} /> 完成</>}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
      <style>{` .animate-fadeIn { animation: fadeIn 0.3s ease-out; } @keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } } `}</style>
    </div>,
    document.body
  );
};

export default AuthModal;
