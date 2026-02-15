import { API_BASE_URL, STATIC_BASE_URL } from '@/config';
import { getAuthToken } from './auth';

/** 若为相对路径则拼成完整 URL，便于视频预览（本地 / 部署与 API 同源） */
export function ensureAbsoluteVideoUrl(url: string | undefined): string | undefined {
  if (!url) return undefined;
  if (url.startsWith('http://') || url.startsWith('https://')) return url;
  const base = STATIC_BASE_URL.replace(/\/$/, '');
  return url.startsWith('/') ? `${base}${url}` : `${base}/${url}`;
}

export interface ModelWithPrice {
  model: string;
  price_usd: number;
  price_cny: number;
}

export interface VideoOptions {
  text_models: string[];
  text_models_with_price: ModelWithPrice[];
  text_model_default: string;
  image_models: string[];
  image_models_with_price: ModelWithPrice[];
  image_model_default: string;
  supported_image_types: string[];
  max_image_size_mb: number;
}

export interface CreateVideoResponse {
  video_id: string;
}

export interface VideoStatusResponse {
  video_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | string;
  detail?: string;
}

export interface VideoContentResponse {
  video_id: string;
  url?: string;
  resolution?: string;
}

export interface VideoHistoryItem {
  video_id: string;
  model: string;
  created_at: string;
  video_url?: string;
  /** 提示词概要，便于识别当次生成内容 */
  prompt_summary?: string;
}

function authHeaders(): HeadersInit {
  const token = getAuthToken();
  if (!token) throw new Error('请先登录');
  return {
    Accept: 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

/** 获取视频生成选项 */
export async function getVideoOptions(): Promise<VideoOptions> {
  const res = await fetch(`${API_BASE_URL}/video/options`, { method: 'GET', headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error('获取视频选项失败');
  return res.json();
}

/** 文生视频：创建任务 */
export async function createVideoText(prompt: string, model?: string): Promise<CreateVideoResponse> {
  const res = await fetch(`${API_BASE_URL}/video/create/text`, {
    method: 'POST',
    headers: {
      ...authHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ prompt, model: model || 'veo-3.1' }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '创建失败' }));
    throw new Error(err.detail || '文生视频创建失败');
  }
  return res.json();
}

/** 单帧图生视频：创建任务 */
export async function createVideoSingleImage(prompt: string, file: File, model?: string): Promise<CreateVideoResponse> {
  const form = new FormData();
  form.append('prompt', prompt);
  form.append('model', model || 'veo-3.1-landscape-fl');
  form.append('input_reference', file);
  const res = await fetch(`${API_BASE_URL}/video/create/image`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '创建失败' }));
    throw new Error(err.detail || '单帧图生视频创建失败');
  }
  return res.json();
}

/** 多帧图生视频：创建任务 */
export async function createVideoDualImages(
  prompt: string,
  fileFirst: File,
  fileLast: File,
  model?: string
): Promise<CreateVideoResponse> {
  const form = new FormData();
  form.append('prompt', prompt);
  form.append('model', model || 'veo-3.1-landscape-fl');
  form.append('image_first', fileFirst);
  form.append('image_last', fileLast);
  const res = await fetch(`${API_BASE_URL}/video/create/images`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '创建失败' }));
    throw new Error(err.detail || '多帧图生视频创建失败');
  }
  return res.json();
}

/** 查询视频任务状态 */
export async function getVideoStatus(videoId: string): Promise<VideoStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/video/status/${videoId}`, {
    method: 'GET',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '查询失败' }));
    throw new Error(err.detail || '查询状态失败');
  }
  return res.json();
}

/** 获取视频内容（含 URL） */
export async function getVideoContent(videoId: string): Promise<VideoContentResponse> {
  const res = await fetch(`${API_BASE_URL}/video/content/${videoId}`, {
    method: 'GET',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '获取失败' }));
    throw new Error(err.detail || '获取视频内容失败');
  }
  return res.json();
}

/** 获取最近 N 条视频生成记录（默认 5 条） */
export async function getVideoHistory(limit: number = 5): Promise<VideoHistoryItem[]> {
  const res = await fetch(`${API_BASE_URL}/video/history?limit=${limit}`, {
    method: 'GET',
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '获取失败' }));
    throw new Error(err.detail || '获取历史记录失败');
  }
  return res.json();
}
