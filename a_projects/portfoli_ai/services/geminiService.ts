import { GoogleGenAI, Type } from "@google/genai";
import { Holding, Quote, AIAnalysisResponse, StrategyBucket } from '../types';

const apiKey = process.env.API_KEY || '';
const ai = new GoogleGenAI({ apiKey });

export const analyzePortfolio = async (
  buckets: StrategyBucket[],
  totalValue: number
): Promise<AIAnalysisResponse> => {
  if (!apiKey) {
    return {
      analysis: "未检测到 API Key。请配置环境变量以使用 AI 分析功能。",
      score: 0,
      riskLevel: "Low",
      suggestions: ["请添加 API Key 以解锁智能分析。"]
    };
  }

  const bucketSummary = buckets.map(b => {
    const currentPercent = (b.currentValue / totalValue) * 100;
    const targetValue = totalValue * (b.targetPercent / 100);
    const gapValue = b.currentValue - targetValue;

    return {
      category: b.name,
      target: `${b.targetPercent}%`,
      current: `${currentPercent.toFixed(1)}%`,
      gapValue: `$${gapValue.toFixed(0)}`, // Positive means overweight, negative means underweight
      holdings: b.holdings.map(h => `${h.symbol} ($${(h.shares * h.avgCost).toFixed(0)})`).join(', ')
    };
  });

  const prompt = `
      你是一位专业的投资组合经理。
      用户正在遵循特定的 "哑铃策略" (50/30/20 法则) 进行美股配置。
      
      当前组合数据:
      ${JSON.stringify(bucketSummary, null, 2)}
      
      总资产: $${totalValue.toFixed(0)}
  
      策略定义:
      1. **盾 (防守底仓)** [目标 50%]: 高股息、标普500 (SCHD, VOO, KO, JPM)。作用: 安全垫。
      2. **矛 (稳健增长)** [目标 30%]: 科技巨头、行业龙头 (QQQM, GOOGL, MSFT, PLTR)。作用: 稳定增长。
      3. **剑 (进攻博弈)** [目标 20%]: 周期资源、商业航天、高弹性 (ASTS, URA, COPX)。作用: 爆发收益。
  
      任务:
      1. **分析偏差**: 简述当前配置与目标的差距。
      2. **执行评分**: 给出 0-100 的评分。
      3. **风险判定**: Low/Moderate/High。
      4. **具体调仓建议 (重要)**: 
         - 请根据 "gapValue" (偏差金额) 提供 3 条具体的操作建议。
         - **必须** 提到具体的股票代码。
         - 例如: "盾不足 (-$2000)，建议买入约 25 股 SCHD。" 或 "剑超配 (+$5000)，建议止盈部分 ASTS。"
         - 如果某个部分为空，强烈建议买入该类别下的代表性标的。
  
      **请务必使用简体中文回复。**
    `;

  try {
    const response = await ai.models.generateContent({
      model: 'gemini-3-flash-preview',
      contents: prompt,
      config: {
        responseMimeType: "application/json",
        responseSchema: {
          type: Type.OBJECT,
          properties: {
            analysis: { type: Type.STRING },
            score: { type: Type.NUMBER },
            riskLevel: { type: Type.STRING, enum: ["Low", "Moderate", "High"] },
            suggestions: {
              type: Type.ARRAY,
              items: { type: Type.STRING }
            }
          }
        }
      }
    });

    const text = response.text;
    if (!text) throw new Error("AI 未返回数据");

    return JSON.parse(text) as AIAnalysisResponse;

  } catch (error) {
    console.error("Gemini Analysis Failed:", error);
    return {
      analysis: "暂时无法分析您的投资组合，请稍后再试。",
      score: 0,
      riskLevel: "Moderate",
      suggestions: ["检查网络连接", "稍后重试"]
    };
  }
};