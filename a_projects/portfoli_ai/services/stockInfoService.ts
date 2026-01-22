// 股票信息查询服务
// 使用 Alpaca API 获取股票基本信息（公司名称、板块等）

import { config } from '../config/alpacaConfig';

export interface StockInfo {
  symbol: string;
  name: string;
  sector?: string;
  exchange?: string;
  // 价格信息
  currentPrice?: number;
  previousClose?: number;
  open?: number; // 开盘价
  change?: number;
  changePercent?: number;
  // 当日交易数据
  dayHigh?: number; // 当日最高价
  dayLow?: number; // 当日最低价
  // 市场数据
  marketCap?: number;
  volume?: number;
  averageVolume?: number; // 平均成交量
  // 交易信息
  high52Week?: number;
  low52Week?: number;
  // 其他信息
  currency?: string;
  quoteType?: string;
  dividendYield?: number; // 股息收益率
  sharesOutstanding?: number; // 流通股数
}

interface AlpacaAsset {
  id: string;
  class: string;
  exchange: string;
  symbol: string;
  name: string;
  status: string;
  tradable: boolean;
  marginable: boolean;
  shortable: boolean;
  easy_to_borrow: boolean;
  fractionable: boolean;
}

// 缓存股票信息，避免重复请求
const stockInfoCache: Map<string, StockInfo> = new Map();
const pendingRequests: Map<string, Promise<StockInfo | null>> = new Map();

// 板块映射（根据公司名称或行业推断）
const sectorMapping: Record<string, string> = {
  'Technology': 'Technology',
  'Tech': 'Technology',
  'Software': 'Technology',
  'Semiconductor': 'Technology',
  'Hardware': 'Technology',
  'Financial': 'Financial',
  'Bank': 'Financial',
  'Insurance': 'Financial',
  'Healthcare': 'Healthcare',
  'Pharmaceutical': 'Healthcare',
  'Biotech': 'Healthcare',
  'Medical': 'Healthcare',
  'Energy': 'Energy',
  'Oil': 'Energy',
  'Gas': 'Energy',
  'Renewable': 'Energy',
  'Consumer': 'Consumer Cyclical',
  'Retail': 'Consumer Cyclical',
  'Automotive': 'Consumer Cyclical',
  'Communication': 'Communication',
  'Telecom': 'Communication',
  'Media': 'Communication',
  'Industrial': 'Industrial',
  'Manufacturing': 'Industrial',
  'Aerospace': 'Industrial',
  'Materials': 'Basic Materials',
  'Mining': 'Basic Materials',
  'Metals': 'Basic Materials',
  'Real Estate': 'Real Estate',
  'REIT': 'Real Estate',
  'Utilities': 'Utilities',
  'Electric': 'Utilities',
};

/**
 * 根据股票代码获取公司信息
 */
export async function getStockInfo(symbol: string): Promise<StockInfo | null> {
  if (!symbol || symbol.trim().length === 0) {
    return null;
  }

  const upperSymbol = symbol.toUpperCase().trim();

  // 检查缓存
  if (stockInfoCache.has(upperSymbol)) {
    return stockInfoCache.get(upperSymbol)!;
  }

  // 如果已有正在进行的请求，返回该请求
  if (pendingRequests.has(upperSymbol)) {
    return pendingRequests.get(upperSymbol)!;
  }

  // 创建新请求 - 仅使用 Alpaca (通过代理)
  const request = fetchStockInfoFromAlpaca(upperSymbol);
  pendingRequests.set(upperSymbol, request);

  try {
    const info = await request;
    if (info) {
      stockInfoCache.set(upperSymbol, info);
    }
    return info;
  } finally {
    pendingRequests.delete(upperSymbol);
  }
}

/**
 * 从 Alpaca API 获取股票信息（主要方法）
 */
async function fetchStockInfoFromAlpaca(symbol: string): Promise<StockInfo | null> {
  try {
    // 使用 Alpaca Assets API 获取资产信息
    // 通过代理 /api/alpaca-paper 访问 https://paper-api.alpaca.markets
    const url = `/api/alpaca-paper/v2/assets/${symbol}`;

    console.log(`[StockInfo] 尝试从 Alpaca 获取 ${symbol} 的信息...`);

    let asset: AlpacaAsset | null = null;

    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'APCA-API-KEY-ID': config.API_KEY,
          'APCA-API-SECRET-KEY': config.SECRET_KEY,
        },
      });

      if (response.ok) {
        asset = await response.json();
        console.log(`[StockInfo] 成功从 Alpaca 获取 ${symbol}:`, asset);
      } else if (response.status === 404) {
        console.warn(`[StockInfo] 股票 ${symbol} 在 Alpaca 中未找到`);
        return null; // 直接返回 null，不抛出错误
      } else {
        const errorText = await response.text();
        console.warn(`[StockInfo] Alpaca API 错误 (${response.status}):`, errorText);
        throw new Error(`Alpaca API 错误: ${response.status} ${errorText}`);
      }
    } catch (error: any) {
      console.error(`[StockInfo] Alpaca 请求失败:`, error.message);
      throw error;
    }

    if (!asset) {
      return null;
    }

    // 提取基本信息
    const stockInfo: StockInfo = {
      symbol: asset.symbol,
      name: asset.name || symbol,
      exchange: asset.exchange,
    };

    // 尝试推断板块
    stockInfo.sector = inferSector(asset.name);

    // 尝试获取最新报价数据
    // 通过代理 /api/alpaca-data 访问 https://data.alpaca.markets
    try {
      const quoteUrl = `/api/alpaca-data/v2/stocks/${symbol}/quotes/latest`;
      const quoteResponse = await fetch(quoteUrl, {
        method: 'GET',
        headers: {
          'APCA-API-KEY-ID': config.API_KEY,
          'APCA-API-SECRET-KEY': config.SECRET_KEY,
        },
      });

      if (quoteResponse.ok) {
        const quoteData = await quoteResponse.json();
        if (quoteData.quote) {
          const q = quoteData.quote;
          stockInfo.currentPrice = q.ap; // ask price
          stockInfo.currency = 'USD';

          console.log(`[StockInfo] 获取到 Alpaca 报价:`, q);
        }
      } else {
        console.warn(`[StockInfo] 获取 Alpaca 报价失败 code=${quoteResponse.status}`);
      }
    } catch (error) {
      console.warn(`[StockInfo] 获取 Alpaca 报价失败，使用基本信息:`, error);
    }

    return stockInfo;
  } catch (error: any) {
    const errorMessage = error?.message || String(error);
    console.error(`[StockInfo] Alpaca API 请求失败 (${symbol}):`, errorMessage);
    return null;
  }
}
// Removed fetchStockInfoFromYahoo function and all Yahoo logic




/**
 * 根据公司名称推断板块
 */
function inferSector(name: string): string {
  if (!name) return 'Technology';

  const upperName = name.toUpperCase();

  // 检查关键词匹配
  for (const [keyword, sector] of Object.entries(sectorMapping)) {
    if (upperName.includes(keyword.toUpperCase())) {
      return sector;
    }
  }

  // 特殊规则
  if (upperName.includes('ETF') || upperName.includes('FUND') || upperName.includes('INDEX')) {
    return 'Financial';
  }

  if (upperName.includes('BANK')) {
    return 'Financial';
  }

  if (upperName.includes('OIL') || upperName.includes('ENERGY') || upperName.includes('PETROLEUM')) {
    return 'Energy';
  }

  if (upperName.includes('PHARMA') || upperName.includes('BIO') || upperName.includes('HEALTH')) {
    return 'Healthcare';
  }

  // 默认返回 Technology
  return 'Technology';
}

/**
 * 清除缓存
 */
export function clearStockInfoCache(): void {
  stockInfoCache.clear();
}

/**
 * 预加载多个股票信息
 */
export async function preloadStockInfo(symbols: string[]): Promise<void> {
  await Promise.all(symbols.map(symbol => getStockInfo(symbol)));
}
