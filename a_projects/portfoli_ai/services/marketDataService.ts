import { Quote } from '../types';
import { MOCK_PRICES } from '../constants';

// This service simulates a WebSocket connection to a market data provider
// Since we don't have a paid financial API, we simulate price movements.

export class MarketDataService {
  private subscribers: ((quotes: Record<string, Quote>) => void)[] = [];
  private currentPrices: Record<string, number> = { ...MOCK_PRICES };
  private intervalId: number | null = null;
  private activeSymbols: string[] = [];

  constructor() {
    this.startSimulation();
  }

  private startSimulation() {
    this.intervalId = window.setInterval(() => {
      this.simulateMarketMove();
      this.notifySubscribers();
    }, 3000); // Update every 3 seconds
  }

  private simulateMarketMove() {
    // Randomly fluctuate prices by -0.5% to +0.5%
    Object.keys(this.currentPrices).forEach(symbol => {
      const volatility = 0.005; 
      const change = 1 + (Math.random() * volatility * 2 - volatility);
      this.currentPrices[symbol] = this.currentPrices[symbol] * change;
    });
  }

  private getQuotes(): Record<string, Quote> {
    const quotes: Record<string, Quote> = {};
    Object.keys(this.currentPrices).forEach(symbol => {
      const current = this.currentPrices[symbol];
      const base = MOCK_PRICES[symbol] || current; // Use initial mock price as previous close reference
      const change = current - base;
      const changePercent = (change / base) * 100;

      quotes[symbol] = {
        symbol,
        price: current,
        change,
        changePercent
      };
    });
    return quotes;
  }

  private notifySubscribers() {
    const quotes = this.getQuotes();
    this.subscribers.forEach(cb => cb(quotes));
  }

  public subscribe(callback: (quotes: Record<string, Quote>) => void) {
    this.subscribers.push(callback);
    // Send immediate data
    callback(this.getQuotes());
    return () => {
      this.subscribers = this.subscribers.filter(cb => cb !== callback);
    };
  }

  public addSymbol(symbol: string) {
    if (!this.currentPrices[symbol]) {
      // Simulate an initial price if unknown
      this.currentPrices[symbol] = 100 + Math.random() * 100;
    }
  }
}

export const marketDataService = new MarketDataService();
