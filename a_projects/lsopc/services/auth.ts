import { API_BASE_URL } from '@/config';

export interface RegisterData {
  username: string;
  email: string;
  password: string;
}

export interface LoginData {
  username: string;
  password: string;
}

export interface User {
  username: string;
  email?: string;
  nickname?: string;
  phone?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user?: User;
}

/** 登录成功：带 user；need_set_password 时需引导用户设置密码 */
export interface TokenWithUser {
  access_token: string;
  token_type: string;
  user: User;
  need_set_password?: boolean;
}

export interface RegisterResponse {
  id: number;
  username: string;
  email: string;
}

// 注册
export async function register(data: RegisterData): Promise<RegisterResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '注册失败' }));
    throw new Error(error.detail || '注册失败');
  }

  return response.json();
}

/** 手机号+密码登录（默认方式，减少验证码发送） */
export async function login(data: { username: string; password: string }): Promise<TokenWithUser> {
  const formData = new URLSearchParams();
  formData.append('username', data.username.trim());
  formData.append('password', data.password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
  });

  const res = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(res.detail || '手机号或密码错误');
  }
  return res as TokenWithUser;
}

/** 发送短信验证码 */
export async function sendSmsCode(phone: string): Promise<{ ok: boolean; message?: string }> {
  const response = await fetch(`${API_BASE_URL}/auth/send-sms-code`, {
    method: 'POST',
    headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone: phone.trim() }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const msg = data.detail || (response.status === 429 ? '请 60 秒后再获取验证码' : '验证码发送失败');
    throw new Error(typeof msg === 'string' ? msg : msg[0]?.msg || '验证码发送失败');
  }
  return data;
}

/** 手机验证码登录/注册（未注册则自动注册） */
export async function loginBySms(phone: string, code: string): Promise<TokenWithUser> {
  const response = await fetch(`${API_BASE_URL}/auth/login-by-sms`, {
    method: 'POST',
    headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone: phone.trim(), code: code.trim() }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const msg = data.detail || '验证码错误或已过期';
    throw new Error(typeof msg === 'string' ? msg : '登录失败');
  }
  return data as TokenWithUser;
}

/** 首次设置密码（验证码注册后或未设密用户，需已登录） */
export async function setPassword(password: string): Promise<void> {
  const token = getAuthToken();
  if (!token) throw new Error('请先登录');
  const response = await fetch(`${API_BASE_URL}/auth/me/set-password`, {
    method: 'PATCH',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ password }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || '设置失败');
}

/** 个人中心修改密码 */
export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  const token = getAuthToken();
  if (!token) throw new Error('请先登录');
  const response = await fetch(`${API_BASE_URL}/auth/me/change-password`, {
    method: 'PATCH',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || '修改失败');
}

// === 认证状态管理 ===

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

export function saveAuth(token: string, user?: User): void {
  localStorage.setItem(TOKEN_KEY, token);
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }
  // 触发登录状态变化事件
  window.dispatchEvent(new CustomEvent('authStateChanged'));
}

export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getCurrentUser(): User | null {
  const userStr = localStorage.getItem(USER_KEY);
  try {
    return userStr ? JSON.parse(userStr) : null;
  } catch {
    return null;
  }
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  // 触发登录状态变化事件
  window.dispatchEvent(new CustomEvent('authStateChanged'));
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem(TOKEN_KEY);
}
