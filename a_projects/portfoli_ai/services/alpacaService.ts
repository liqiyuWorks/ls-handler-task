// Alpaca WebSocket 实时股票价格服务
// 使用 Alpaca Market Data API v2 WebSocket 获取实时报价

import { config } from '../config/alpacaConfig';

interface AlpacaQuote {
  t: string;  // timestamp
  x: string;  // exchange
  p: number;  // price
  s: number;  // size
}

interface AlpacaTrade {
  t: string;  // timestamp
  x: string;  // exchange
  p: number;  // price
  s: number;  // size
  c?: string[]; // conditions
  i?: number;   // trade_id
  z?: string;   // tape
}

interface AlpacaMessage {
  T?: string;  // message type: 'q' (quote), 't' (trade), 'subscription', 'error', 'success'
  S?: string;  // symbol
  q?: AlpacaQuote;  // quote data
  t?: AlpacaTrade;  // trade data
  msg?: string;     // error/success message
}

export class AlpacaService {
  private ws: WebSocket | null = null;
  private apiKey: string;
  private secretKey: string;
  private subscribers: ((quotes: Record<string, { price: number; timestamp: number }>) => void)[] = [];
  private currentPrices: Record<string, { price: number; timestamp: number }> = {};
  private subscribedSymbols: Set<string> = new Set();
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number;
  private reconnectDelay: number;
  private isConnecting: boolean = false;
  private heartbeatInterval: number | null = null;

  // Alpaca WebSocket 端点
  private readonly WS_URL: string;
  // Alpaca REST API 端点
  private readonly DATA_API_URL: string;

  constructor(apiKey: string, secretKey: string) {
    this.apiKey = apiKey;
    this.secretKey = secretKey;
    this.WS_URL = config.WS_URL;
    this.DATA_API_URL = config.DATA_API_URL || 'https://data.alpaca.markets/v2';
    this.maxReconnectAttempts = config.MAX_RECONNECT_ATTEMPTS;
    this.reconnectDelay = config.RECONNECT_DELAY;
  }

  /**
   * 连接到 Alpaca WebSocket
   */
  public connect(): Promise<void> {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      this.isConnecting = true;

      try {
        this.ws = new WebSocket(this.WS_URL);

        this.ws.onopen = () => {
          console.log('[Alpaca] WebSocket 连接已建立');
          this.isConnecting = false;
          this.reconnectAttempts = 0;

          // 发送认证消息
          this.sendAuth();

          // 启动心跳
          this.startHeartbeat();

          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        this.ws.onerror = (error) => {
          console.error('[Alpaca] WebSocket 错误:', error);
          this.isConnecting = false;
          reject(error);
        };

        this.ws.onclose = () => {
          console.log('[Alpaca] WebSocket 连接已关闭');
          this.stopHeartbeat();
          this.isConnecting = false;

          // 尝试重连
          if (this.reconnectAttempts < this.maxReconnectAttempts && this.subscribedSymbols.size > 0) {
            this.reconnectAttempts++;
            console.log(`[Alpaca] 尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            setTimeout(() => {
              this.connect().catch(err => console.error('[Alpaca] 重连失败:', err));
            }, this.reconnectDelay);
          }
        };
      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  /**
   * 通过 REST API 获取最新报价快照
   */
  public async getLatestQuotes(symbols: string[]): Promise<Map<string, number>> {
    if (!symbols || symbols.length === 0) {
      return new Map();
    }

    try {
      const symbolsParam = symbols.join(',');
      const url = `${this.DATA_API_URL}/stocks/snapshots?symbols=${symbolsParam}`;

      console.log(`[Alpaca] Fetching snapshots for: ${symbolsParam}`);

      const response = await fetch(url, {
        headers: {
          'APCA-API-KEY-ID': this.apiKey,
          'APCA-API-SECRET-KEY': this.secretKey,
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Alpaca API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      const priceMap = new Map<string, number>();

      Object.keys(data).forEach(symbol => {
        const item = data[symbol];
        // 优先使用 latestTrade (最新成交价)，其次 dailyBar.c (收盘价)，最后 latestQuote (最新报价)
        let price = 0;

        if (item.latestTrade && item.latestTrade.p) {
          price = item.latestTrade.p;
        } else if (item.dailyBar && item.dailyBar.c) {
          price = item.dailyBar.c;
        } else if (item.latestQuote && item.latestQuote.ap && item.latestQuote.bp) {
          price = (item.latestQuote.ap + item.latestQuote.bp) / 2;
        }

        if (price > 0) {
          priceMap.set(symbol, price);
          // 同时也更新内部缓存
          this.currentPrices[symbol] = {
            price: price,
            timestamp: Date.now()
          };
        }
      });

      // 通知由于这里更新了 currentPrices
      if (priceMap.size > 0) {
        this.notifySubscribers();
      }

      console.log(`[Alpaca] Fetched ${priceMap.size} quotes via REST`);
      return priceMap;
    } catch (error) {
      console.error('[Alpaca] Failed to fetch latest quotes:', error);
      return new Map();
    }
  }

  /**
   * 发送认证消息
   */
  private sendAuth(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    const authMessage = {
      action: 'auth',
      key: this.apiKey,
      secret: this.secretKey
    };

    this.ws.send(JSON.stringify(authMessage));
    console.log('[Alpaca] 已发送认证请求');
  }

  /**
   * 订阅股票符号
   */
  public subscribe(symbols: string[]): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      // 如果未连接，先连接再订阅
      this.connect().then(() => {
        // 等待认证完成后再订阅
        setTimeout(() => this.doSubscribe(symbols), 1000);
      });
      return;
    }

    this.doSubscribe(symbols);
  }

  private doSubscribe(symbols: string[]): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    // 过滤掉已订阅的符号
    const newSymbols = symbols.filter(s => !this.subscribedSymbols.has(s));
    if (newSymbols.length === 0) {
      return;
    }

    // 添加新符号到订阅列表
    newSymbols.forEach(s => this.subscribedSymbols.add(s));

    // 发送订阅消息 - 订阅实时报价 (quotes)
    const subscribeMessage = {
      action: 'subscribe',
      quotes: newSymbols
    };

    this.ws.send(JSON.stringify(subscribeMessage));
    console.log(`[Alpaca] 已订阅 ${newSymbols.length} 个股票:`, newSymbols);
  }

  /**
   * 取消订阅股票符号
   */
  public unsubscribe(symbols: string[]): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    symbols.forEach(s => this.subscribedSymbols.delete(s));

    const unsubscribeMessage = {
      action: 'unsubscribe',
      quotes: symbols
    };

    this.ws.send(JSON.stringify(unsubscribeMessage));
    console.log(`[Alpaca] 已取消订阅:`, symbols);
  }

  /**
   * 处理 WebSocket 消息
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const messages: AlpacaMessage[] = Array.isArray(JSON.parse(event.data))
        ? JSON.parse(event.data)
        : [JSON.parse(event.data)];

      messages.forEach((msg: AlpacaMessage) => {
        if (msg.T === 'q' && msg.S && msg.q) {
          // 收到报价数据
          this.handleQuote(msg.S, msg.q);
        } else if (msg.T === 't' && msg.S && msg.t) {
          // 收到交易数据（也可以用作价格更新）
          this.handleTrade(msg.S, msg.t);
        } else if (msg.T === 'subscription') {
          console.log('[Alpaca] 订阅确认:', msg);
        } else if (msg.T === 'error' || msg.msg) {
          console.error('[Alpaca] 错误消息:', msg.msg || msg);
        } else if (msg.T === 'success') {
          console.log('[Alpaca] 成功消息:', msg.msg || msg);
        }
      });
    } catch (error) {
      console.error('[Alpaca] 解析消息失败:', error, event.data);
    }
  }

  /**
   * 处理报价数据
   */
  private handleQuote(symbol: string, quote: AlpacaQuote): void {
    if (quote.p && quote.p > 0) {
      const timestamp = Date.now();
      this.currentPrices[symbol] = {
        price: quote.p,
        timestamp
      };
      this.notifySubscribers();
    }
  }

  /**
   * 处理交易数据
   */
  private handleTrade(symbol: string, trade: AlpacaTrade): void {
    if (trade.p && trade.p > 0) {
      const timestamp = Date.now();
      this.currentPrices[symbol] = {
        price: trade.p,
        timestamp
      };
      this.notifySubscribers();
    }
  }

  /**
   * 通知订阅者
   */
  private notifySubscribers(): void {
    const quotes: Record<string, { price: number; timestamp: number }> = {};
    Object.keys(this.currentPrices).forEach(symbol => {
      quotes[symbol] = { ...this.currentPrices[symbol] };
    });

    this.subscribers.forEach(callback => {
      try {
        callback(quotes);
      } catch (error) {
        console.error('[Alpaca] 订阅者回调错误:', error);
      }
    });
  }

  /**
   * 订阅价格更新
   */
  public onPriceUpdate(callback: (quotes: Record<string, { price: number; timestamp: number }>) => void): () => void {
    this.subscribers.push(callback);

    // 立即发送当前价格
    if (Object.keys(this.currentPrices).length > 0) {
      callback({ ...this.currentPrices });
    }

    // 返回取消订阅函数
    return () => {
      this.subscribers = this.subscribers.filter(cb => cb !== callback);
    };
  }

  /**
   * 获取当前价格
   */
  public getCurrentPrice(symbol: string): number | null {
    return this.currentPrices[symbol]?.price || null;
  }

  /**
   * 启动心跳
   */
  private startHeartbeat(): void {
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        // Alpaca 不需要显式心跳，但我们可以发送 ping
        // 实际上 Alpaca 会自动处理连接保持
      }
    }, config.HEARTBEAT_INTERVAL);
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * 断开连接
   */
  public disconnect(): void {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.subscribedSymbols.clear();
    this.currentPrices = {};
    this.reconnectAttempts = 0;
  }
}
