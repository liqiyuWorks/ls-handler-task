import { API_BASE_URL } from '@/config';
import { getAuthToken } from './auth';

export interface MeResponse {
  username: string;
  phone?: string | null;
  email?: string | null;
  nickname?: string | null;
  balance: number;
  total_spent: number;
}

export interface ProfileUpdateBody {
  email?: string | null;
  nickname?: string | null;
}

export interface RechargeResponse {
  balance: number;
  added: number;
}

export interface UsageRecord {
  id: string;
  record_type: string;
  type_label: string;
  amount: number;
  count: number;
  created_at: string;
}

function authHeaders(): HeadersInit {
  const token = getAuthToken();
  if (!token) throw new Error('请先登录');
  return {
    Accept: 'application/json',
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

/** 获取当前用户信息与余额（个人中心用） */
export async function getMe(): Promise<MeResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/me`, {
    method: 'GET',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '获取失败' }));
    throw new Error(err.detail || '获取用户信息失败');
  }
  return res.json();
}

/** 更新个人信息（邮箱、昵称） */
export async function updateProfile(body: ProfileUpdateBody): Promise<MeResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/me`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '保存失败' }));
    throw new Error(err.detail || '保存失败');
  }
  return res.json();
}

/** 充值 */
export async function recharge(amount: number): Promise<RechargeResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/recharge`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ amount }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '充值失败' }));
    throw new Error(err.detail || '充值失败');
  }
  return res.json();
}

/** 获取调用记录 */
export async function getUsageRecords(limit = 50, offset = 0): Promise<UsageRecord[]> {
  const res = await fetch(
    `${API_BASE_URL}/auth/records?limit=${limit}&offset=${offset}`,
    { method: 'GET', headers: authHeaders() }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '获取失败' }));
    throw new Error(err.detail || '获取调用记录失败');
  }
  return res.json();
}

export interface CozeConfigResponse {
  coze_api_token: string | null;
  coze_space_id: string | null;
}

export interface CozeConfigUpdateBody {
  coze_api_token?: string | null;
  coze_space_id?: string | null;
}

/** 获取当前用户扣子知识库配置（API Token、Space ID） */
export async function getCozeConfig(): Promise<CozeConfigResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/coze-config`, {
    method: 'GET',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '获取失败' }));
    throw new Error(err.detail || '获取扣子知识库配置失败');
  }
  return res.json();
}

/** 更新当前用户扣子知识库配置（首次保存或修改） */
export async function updateCozeConfig(body: CozeConfigUpdateBody): Promise<CozeConfigResponse> {
  const res = await fetch(`${API_BASE_URL}/auth/coze-config`, {
    method: 'PATCH',
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '保存失败' }));
    throw new Error(err.detail || '保存扣子知识库配置失败');
  }
  return res.json();
}
