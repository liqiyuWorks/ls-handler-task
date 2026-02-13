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
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user?: User; // 假设后端返回用户信息，如果没有则从前端临时构造
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

// 登录
export async function login(data: LoginData): Promise<AuthResponse> {
  const formData = new URLSearchParams();
  // 根据提供的 curl 命令构建表单数据
  formData.append('grant_type', '');
  formData.append('username', data.username);
  formData.append('password', data.password);
  formData.append('scope', '');
  formData.append('client_id', 'string');
  // 注意：这里使用占位符，如果后端强制验证 client_secret，请替换为真实值
  formData.append('client_secret', 'string'); 

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: '登录失败' }));
    throw new Error(error.detail || '登录失败');
  }

  return response.json();
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
