import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X, User, Mail, Lock, Eye, EyeOff, Loader2, Sparkles, UserPlus, LogIn } from 'lucide-react';
import { login, register, saveAuth, LoginData, RegisterData } from '../services/auth';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthSuccess: (username: string) => void;
}

type AuthMode = 'login' | 'register';

const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onAuthSuccess }) => {
  // 调试日志
  useEffect(() => {
    if (isOpen) {
      console.log('AuthModal opened');
    }
  }, [isOpen]);

  const [mode, setMode] = useState<AuthMode>('login');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const resetForm = () => {
    setUsername('');
    setEmail('');
    setPassword('');
    setError(null);
    setSuccess(null);
    setShowPassword(false);
  };

  const switchMode = (newMode: AuthMode) => {
    setMode(newMode);
    setError(null);
    setSuccess(null);
  };

  const handleClose = () => {
    resetForm();
    setMode('login');
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      if (mode === 'login') {
        const loginData: LoginData = { username, password };
        const response = await login(loginData);
        // 如果后端返回了 user 对象则保存，否则使用表单中的 username
        const userToSave = response.user || { username };
        saveAuth(response.access_token, userToSave);
        onAuthSuccess(username);
        handleClose();
      } else {
        const registerData: RegisterData = { username, email, password };
        await register(registerData);
        setSuccess('注册成功！正在自动登录...');
        
        // 注册成功后自动登录
        const loginResponse = await login({ username, password });
        const userToSave = loginResponse.user || { username, email };
        saveAuth(loginResponse.access_token, userToSave);
        
        onAuthSuccess(username);
        setTimeout(() => handleClose(), 1000);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  // 使用 createPortal 将弹窗挂载到 body，避免 z-index 和父级 overflow 限制
  // 显式设置极高的 z-index
  return createPortal(
    <div 
      className="fixed inset-0 overflow-y-auto"
      style={{ zIndex: 99999 }}
    >
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/80 backdrop-blur-md"
        onClick={handleClose}
      />
      
      {/* Modal Container */}
      <div className="min-h-screen px-4 text-center">
        {/* 垂直居中辅助元素 */}
        <span className="inline-block h-screen align-middle" aria-hidden="true">&#8203;</span>
        
        {/* Modal - 确保 relative 和 z-index 高于 backdrop */}
        <div className="inline-block w-full max-w-lg text-left align-middle bg-gradient-to-b from-gray-900 via-gray-900 to-black border border-white/10 rounded-3xl shadow-2xl overflow-hidden relative my-8 z-10">
          {/* 顶部装饰光晕 */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-32 bg-gradient-to-r from-orange-500/30 via-yellow-500/20 to-orange-500/30 blur-3xl" />
          
          {/* 关闭按钮 */}
          <button
            onClick={handleClose}
            className="absolute top-5 right-5 z-10 p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-full transition-all duration-200"
          >
            <X size={20} />
          </button>

          {/* Header */}
          <div className="relative pt-8 pb-2 text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-orange-500 to-yellow-500 shadow-lg shadow-orange-500/30 mb-4">
              {mode === 'login' ? (
                <LogIn size={28} className="text-white" />
              ) : (
                <UserPlus size={28} className="text-white" />
              )}
            </div>
            <h2 className="text-2xl font-bold text-white">
              {mode === 'login' ? '欢迎回来' : '加入我们'}
            </h2>
            <p className="text-gray-400 mt-2 text-sm">
              {mode === 'login' ? '登录您的账号，继续探索' : '创建账号，开启智能之旅'}
            </p>
          </div>

          {/* Tabs */}
          <div className="px-8 py-4">
            <div className="flex bg-white/5 p-1.5 rounded-2xl border border-white/5">
              <button
                onClick={() => switchMode('login')}
                className={`flex-1 flex items-center justify-center gap-2 py-3.5 px-6 rounded-xl text-base font-semibold transition-all duration-300 ${
                  mode === 'login'
                    ? 'bg-gradient-to-r from-orange-500 to-yellow-500 text-white shadow-lg shadow-orange-500/25'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <LogIn size={18} />
                登录
              </button>
              <button
                onClick={() => switchMode('register')}
                className={`flex-1 flex items-center justify-center gap-2 py-3.5 px-6 rounded-xl text-base font-semibold transition-all duration-300 ${
                  mode === 'register'
                    ? 'bg-gradient-to-r from-orange-500 to-yellow-500 text-white shadow-lg shadow-orange-500/25'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <UserPlus size={18} />
                注册
              </button>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="px-8 pb-8 space-y-5">
            {/* Messages */}
            {error && (
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm animate-fadeIn flex items-center gap-3">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                {error}
              </div>
            )}
            {success && (
              <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-xl text-green-400 text-sm animate-fadeIn flex items-center gap-3">
                <Sparkles size={16} className="text-green-400" />
                {success}
              </div>
            )}

            {/* Inputs */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300 flex items-center gap-2">
                <User size={14} className="text-orange-400" />
                用户名
              </label>
              <div className="relative group">
                <div className="absolute inset-0 bg-gradient-to-r from-orange-500/20 to-yellow-500/20 rounded-xl blur opacity-0 group-focus-within:opacity-100 transition-opacity" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="请输入用户名"
                  required
                  autoComplete="username"
                  className="relative w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-orange-500/50 focus:bg-white/10 transition-all duration-200"
                />
              </div>
            </div>

            {mode === 'register' && (
              <div className="space-y-2 animate-fadeIn">
                <label className="text-sm font-medium text-gray-300 flex items-center gap-2">
                  <Mail size={14} className="text-orange-400" />
                  邮箱地址
                </label>
                <div className="relative group">
                  <div className="absolute inset-0 bg-gradient-to-r from-orange-500/20 to-yellow-500/20 rounded-xl blur opacity-0 group-focus-within:opacity-100 transition-opacity" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="请输入邮箱地址"
                    required
                    autoComplete="email"
                    className="relative w-full px-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-orange-500/50 focus:bg-white/10 transition-all duration-200"
                  />
                </div>
              </div>
            )}

            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300 flex items-center gap-2">
                <Lock size={14} className="text-orange-400" />
                密码
              </label>
              <div className="relative group">
                <div className="absolute inset-0 bg-gradient-to-r from-orange-500/20 to-yellow-500/20 rounded-xl blur opacity-0 group-focus-within:opacity-100 transition-opacity" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={mode === 'register' ? '设置密码（至少6位）' : '请输入密码'}
                  required
                  minLength={6}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  className="relative w-full px-4 py-3.5 pr-12 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-orange-500/50 focus:bg-white/10 transition-all duration-200"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition-colors z-10"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {mode === 'register' && (
                <p className="text-xs text-gray-500 mt-1">密码长度至少为 6 个字符</p>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 mt-2 bg-gradient-to-r from-orange-500 to-yellow-500 hover:from-orange-600 hover:to-yellow-600 text-white font-semibold text-base rounded-xl shadow-lg shadow-orange-500/30 hover:shadow-orange-500/50 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 group"
            >
              {loading ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  {mode === 'login' ? '登录中...' : '注册中...'}
                </>
              ) : (
                <>
                  {mode === 'login' ? (
                    <>
                      <LogIn size={20} />
                      立即登录
                    </>
                  ) : (
                    <>
                      <Sparkles size={20} />
                      创建账号
                    </>
                  )}
                  <span className="group-hover:translate-x-1 transition-transform">→</span>
                </>
              )}
            </button>

            {/* Switch Mode */}
            <div className="pt-2">
              <button
                type="button"
                onClick={() => switchMode(mode === 'login' ? 'register' : 'login')}
                className="w-full py-3 border border-white/10 hover:border-orange-500/50 text-gray-400 hover:text-orange-400 font-medium rounded-xl transition-all duration-200 flex items-center justify-center gap-2"
              >
                {mode === 'login' ? (
                  <>
                    <UserPlus size={18} />
                    免费注册新账号
                  </>
                ) : (
                  <>
                    <LogIn size={18} />
                    使用已有账号登录
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
      
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
    </div>,
    document.body
  );
};

export default AuthModal;
