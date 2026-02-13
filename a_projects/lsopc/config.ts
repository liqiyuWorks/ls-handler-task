/**
 * API 基础 URL 动态配置
 * - 开发/本地调试: 从 .env.development 或环境变量读取，默认 http://localhost:8000/api
 * - 生产(Docker): 从 .env.production 或构建时环境变量读取，默认 http://api.lsopc.cn/api
 */
function getApiBaseUrl(): string {
  const fromEnv = import.meta.env.VITE_API_BASE_URL;
  if (fromEnv && typeof fromEnv === 'string' && fromEnv.trim()) {
    return fromEnv.trim().replace(/\/$/, ''); // 去掉末尾斜杠
  }
  return import.meta.env.DEV
    ? 'http://localhost:8000/api'
    : 'http://api.lsopc.cn/api';
}

export const API_BASE_URL = getApiBaseUrl();
