import { getAuthToken } from './auth';
import { API_BASE_URL, STATIC_BASE_URL } from '@/config';

/** 若为相对路径则拼成完整 URL，便于图片预览（与视频一致） */
export function ensureAbsoluteImageUrl(url: string | undefined): string | undefined {
  if (!url) return undefined;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const base = STATIC_BASE_URL.replace(/\/$/, '');
  return url.startsWith('/') ? `${base}${url}` : `${base}/${url}`;
}

export interface ImageOptions {
  resolutions: {
    options: string[];
    default: string;
    pricing: string;
  };
  aspect_ratios: {
    options: string[];
    default: string;
  };
}

export interface ImageGenerationRequest {
  prompt: string;
  resolution: string;
  aspect_ratio: string;
  /** 参考图 base64，上传则使用图片编辑/PS 模式 */
  image_base64?: string;
  image_mime_type?: string;
}

export interface ImageGenerationResponse {
  image_url: string;
}

export interface ImageHistoryItem {
  id: string;
  prompt_summary?: string;
  created_at: string;
  image_url?: string;
  resolution: string;
  aspect_ratio: string;
}

export async function getImageOptions(): Promise<ImageOptions> {
  const response = await fetch(`${API_BASE_URL}/image/options`, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error('Failed to fetch image options');
  }

  return response.json();
}

export async function generateImage(data: ImageGenerationRequest): Promise<ImageGenerationResponse> {
  const token = getAuthToken();
  if (!token) {
    throw new Error('请先登录');
  }

  const response = await fetch(`${API_BASE_URL}/image/generate`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data),
  });

  if (response.status === 401) {
    throw new Error('登录已过期，请重新登录');
  }

  if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: '图片生成失败' }));
      throw new Error(error.detail || '图片生成失败');
  }

  return response.json();
}

/** 获取最近 N 条图片生成记录（默认 5 条） */
export async function getImageHistory(limit: number = 5): Promise<ImageHistoryItem[]> {
  const token = getAuthToken();
  if (!token) throw new Error('请先登录');
  const res = await fetch(`${API_BASE_URL}/image/history?limit=${limit}`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '获取失败' }));
    throw new Error(err.detail || '获取历史记录失败');
  }
  return res.json();
}
