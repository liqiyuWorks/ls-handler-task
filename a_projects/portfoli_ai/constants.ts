import { Holding } from './types';

export const INITIAL_HOLDINGS: Holding[] = [
  // FirstTrade Holdings (Extracted from user image)
  { symbol: 'ASTS', name: 'AST SpaceMobile', shares: 1.10132, avgCost: 90.80, sector: 'Communication', account: 'FirstTrade' },
  { symbol: 'CCJ', name: 'Cameco Corp', shares: 0.92259, avgCost: 108.39, sector: 'Energy', account: 'FirstTrade' },
  { symbol: 'COPX', name: 'Global X Copper Miners', shares: 1.22473, avgCost: 81.65, sector: 'Basic Materials', account: 'FirstTrade' },
  { symbol: 'FCX', name: 'Freeport-McMoRan', shares: 1.4072, avgCost: 56.14, sector: 'Basic Materials', account: 'FirstTrade' },
  { symbol: 'GOOGL', name: 'Alphabet Inc.', shares: 0.66263, avgCost: 332.01, sector: 'Communication', account: 'FirstTrade' },
  { symbol: 'QQQM', name: 'Invesco NASDAQ 100', shares: 0.78047, avgCost: 256.26, sector: 'Technology', account: 'FirstTrade' },
  { symbol: 'RKLB', name: 'Rocket Lab USA', shares: 2.306, avgCost: 86.73, sector: 'Industrials', account: 'FirstTrade' },
  { symbol: 'SCHD', name: 'Schwab US Dividend', shares: 1.7325, avgCost: 28.86, sector: 'Financial', account: 'FirstTrade' },
  { symbol: 'TER', name: 'Teradyne Inc', shares: 0.65011, avgCost: 230.73, sector: 'Technology', account: 'FirstTrade' },
  { symbol: 'URA', name: 'Global X Uranium', shares: 3.92857, avgCost: 50.91, sector: 'Energy', account: 'FirstTrade' },
  { symbol: 'VOO', name: 'Vanguard S&P 500', shares: 0.15697, avgCost: 637.00, sector: 'Financial', account: 'FirstTrade' },
];

export const MOCK_PRICES: Record<string, number> = {
  // synced with screenshot prices where available
  'ASTS': 106.88,
  'CCJ': 124.98,
  'COPX': 83.51,
  'FCX': 60.87,
  'GOOGL': 332.22,
  'QQQM': 255.61,
  'RKLB': 86.45,
  'SCHD': 29.22,
  'TER': 234.97,
  'URA': 56.70,
  'VOO': 633.50,
  // Others
  'NVDA': 850.00,
  'BABA': 73.50,
  'AAPL': 175.00,
  'MSFT': 415.00,
  'TSLA': 175.00,
};
