export interface Holding {
  symbol: string;
  name: string;
  shares: number;
  avgCost: number;
  sector: string;
  account: 'FirstTrade' | 'IBKR' | 'uSmart' | 'Other';
}

export interface Quote {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
}

export interface PortfolioSummary {
  totalValue: number;
  totalCost: number;
  totalPnL: number;
  totalPnLPercent: number;
  dailyPnL: number;
}

export interface StrategyBucket {
  name: string; // e.g. "Shield (Defensive)"
  targetPercent: number; // e.g. 50
  currentValue: number;
  holdings: Holding[];
  color: string;
}

export interface AIAnalysisResponse {
  analysis: string;
  score: number;
  riskLevel: 'Low' | 'Moderate' | 'High';
  suggestions: string[];
}