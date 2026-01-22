// Alpaca API 配置
// 注意：在生产环境中，应该使用环境变量或安全的配置管理方式
// 不要将 API keys 提交到公共代码仓库

export const ALPACA_CONFIG = {
  // Alpaca API 密钥
  API_KEY: 'PKRWSF2TIWC7Q5N5A5YA25ZI5X',
  SECRET_KEY: '9hWKiNHwb3Ls7wk1bNwybUB4yHArddYsDvRLT8PKuLu4',

  // WebSocket 端点
  WS_URL: 'wss://stream.data.alpaca.markets/v2/iex',

  // REST API 端点
  DATA_API_URL: 'https://data.alpaca.markets/v2',

  // 重连配置
  MAX_RECONNECT_ATTEMPTS: 5,
  RECONNECT_DELAY: 3000, // 毫秒

  // 心跳间隔
  HEARTBEAT_INTERVAL: 30000, // 毫秒
};

// 从环境变量读取配置（如果存在）
// 在构建时，可以通过环境变量覆盖配置
const getEnvConfig = () => {
  if (typeof window !== 'undefined') {
    // 浏览器环境：可以从 window 对象读取
    const env = (window as any).__ALPACA_CONFIG__;
    if (env) {
      return {
        ...ALPACA_CONFIG,
        ...env
      };
    }
  }
  return ALPACA_CONFIG;
};

export const config = getEnvConfig();
