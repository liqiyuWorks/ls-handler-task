import { Quote } from '../types';
import { MOCK_PRICES } from '../constants';
import { AlpacaService } from './alpacaService';
import { config } from '../config/alpacaConfig';

// 使用 Alpaca 实时数据服务
// 如果 Alpaca 连接失败，会回退到模拟数据

export class MarketDataService {
  private subscribers: ((quotes: Record<string, Quote>) => void)[] = [];
  private currentPrices: Record<string, number> = { ...MOCK_PRICES };
  private basePrices: Record<string, number> = { ...MOCK_PRICES }; // 用于计算涨跌幅
  private intervalId: number | null = null;
  private activeSymbols: Set<string> = new Set();
  private alpacaService: AlpacaService | null = null;
  private useAlpaca: boolean = true;
  private alpacaUnsubscribe: (() => void) | null = null;

  constructor() {
    // 初始化 Alpaca 服务
    try {
      this.alpacaService = new AlpacaService(config.API_KEY, config.SECRET_KEY);
      this.connectAlpaca();
    } catch (error) {
      console.error('[MarketData] Alpaca 初始化失败，使用模拟数据:', error);
      this.useAlpaca = false;
      this.startSimulation();
    }
  }

  /**
   * 连接到 Alpaca WebSocket
   */
  private async connectAlpaca(): Promise<void> {
    if (!this.alpacaService) {
      this.useAlpaca = false;
      this.startSimulation();
      return;
    }

    try {
      await this.alpacaService.connect();

      // 订阅价格更新
      this.alpacaUnsubscribe = this.alpacaService.onPriceUpdate((alpacaQuotes) => {
        // 更新价格并计算涨跌幅
        Object.keys(alpacaQuotes).forEach(symbol => {
          const alpacaPrice = alpacaQuotes[symbol].price;
          if (alpacaPrice > 0) {
            // 如果还没有基础价格，使用当前价格作为基础
            if (!this.basePrices[symbol]) {
              this.basePrices[symbol] = alpacaPrice;
            }
            this.currentPrices[symbol] = alpacaPrice;
          }
        });
        this.notifySubscribers();
      });

      // 如果有已激活的符号，立即订阅并获取初始价格
      if (this.activeSymbols.size > 0) {
        const symbols = Array.from(this.activeSymbols);
        this.alpacaService.subscribe(symbols);

        // 获取初始快照
        this.alpacaService.getLatestQuotes(symbols).then(prices => {
          prices.forEach((price, symbol) => {
            this.currentPrices[symbol] = price;
            if (!this.basePrices[symbol]) {
              this.basePrices[symbol] = price;
            }
          });
          this.notifySubscribers();
        });
      }

      console.log('[MarketData] 已连接到 Alpaca 实时数据流');
    } catch (error) {
      console.error('[MarketData] Alpaca 连接失败，使用模拟数据:', error);
      this.useAlpaca = false;
      this.startSimulation();
    }
  }

  /**
   * 启动模拟（当 Alpaca 不可用时）
   */
  private startSimulation() {
    if (this.intervalId) {
      return; // 已经在运行
    }

    this.intervalId = window.setInterval(() => {
      this.simulateMarketMove();
      this.notifySubscribers();
    }, 3000); // 每3秒更新一次
  }

  /**
   * 模拟市场波动
   */
  private simulateMarketMove() {
    // 随机波动 -0.5% 到 +0.5%
    Object.keys(this.currentPrices).forEach(symbol => {
      if (this.activeSymbols.has(symbol)) {
        const volatility = 0.005;
        const change = 1 + (Math.random() * volatility * 2 - volatility);
        this.currentPrices[symbol] = this.currentPrices[symbol] * change;
      }
    });
  }

  /**
   * 获取报价数据
   */
  private getQuotes(): Record<string, Quote> {
    const quotes: Record<string, Quote> = {};
    Object.keys(this.currentPrices).forEach(symbol => {
      if (!this.activeSymbols.has(symbol)) {
        return; // 只返回已激活的符号
      }

      const current = this.currentPrices[symbol];
      const base = this.basePrices[symbol] || current;
      const change = current - base;
      const changePercent = base > 0 ? (change / base) * 100 : 0;

      quotes[symbol] = {
        symbol,
        price: current,
        change,
        changePercent
      };
    });
    return quotes;
  }

  /**
   * 通知订阅者
   */
  private notifySubscribers() {
    const quotes = this.getQuotes();
    this.subscribers.forEach(cb => {
      try {
        cb(quotes);
      } catch (error) {
        console.error('[MarketData] 订阅者回调错误:', error);
      }
    });
  }

  /**
   * 订阅市场数据更新
   */
  public subscribe(callback: (quotes: Record<string, Quote>) => void) {
    this.subscribers.push(callback);
    // 立即发送当前数据
    callback(this.getQuotes());

    return () => {
      this.subscribers = this.subscribers.filter(cb => cb !== callback);
    };
  }

  /**
   * 添加股票符号并开始跟踪
   */
  public addSymbol(symbol: string) {
    if (this.activeSymbols.has(symbol)) {
      return; // 已经在跟踪
    }

    this.activeSymbols.add(symbol);

    // 如果没有当前价格，使用模拟价格或从 Alpaca 获取
    if (!this.currentPrices[symbol]) {
      this.currentPrices[symbol] = MOCK_PRICES[symbol] || 100 + Math.random() * 100;
    }

    // 设置基础价格（用于计算涨跌幅）
    if (!this.basePrices[symbol]) {
      this.basePrices[symbol] = this.currentPrices[symbol];
    }

    // 如果使用 Alpaca，订阅该符号并获取快照
    if (this.useAlpaca && this.alpacaService) {
      this.alpacaService.subscribe([symbol]);

      // 获取最新价格快照
      this.alpacaService.getLatestQuotes([symbol]).then(prices => {
        const price = prices.get(symbol);
        if (price) {
          this.currentPrices[symbol] = price;
          if (!this.basePrices[symbol]) {
            this.basePrices[symbol] = price;
          }
          this.notifySubscribers();
        }
      });
    }

    // 如果使用模拟数据且未启动，启动模拟
    if (!this.useAlpaca && !this.intervalId) {
      this.startSimulation();
    }

    // 立即通知订阅者
    this.notifySubscribers();
  }

  /**
   * 移除股票符号
   */
  public removeSymbol(symbol: string) {
    this.activeSymbols.delete(symbol);

    if (this.useAlpaca && this.alpacaService) {
      this.alpacaService.unsubscribe([symbol]);
    }
  }

  /**
   * 清理资源
   */
  public destroy() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    if (this.alpacaUnsubscribe) {
      this.alpacaUnsubscribe();
      this.alpacaUnsubscribe = null;
    }

    if (this.alpacaService) {
      this.alpacaService.disconnect();
    }
  }
}

export const marketDataService = new MarketDataService();
