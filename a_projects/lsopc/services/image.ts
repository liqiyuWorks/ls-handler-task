import { getAuthToken } from './auth';

const API_BASE_URL = 'http://api.lsopc.cn/api';

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
}

export interface ImageGenerationResponse {
  image_url: string;
  // 其他可能返回的字段
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
