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

  // Prepare data for AI
  const bucketSummary = buckets.map(b => ({
    category: b.name,
    target: `${b.targetPercent}%`,
    current: `${((b.currentValue / totalValue) * 100).toFixed(1)}%`,
    holdings: b.holdings.map(h => h.symbol).join(', ')
  }));

  const prompt = `
    你是一位专业的投资组合经理。
    用户正在遵循特定的 "哑铃策略" 或 "50/30/20 法则" 进行美股配置：
    1. **盾 (防守底仓)**: 目标占比 50%。关注：高股息、标普500 (如 SCHD, VOO)。逻辑：存钱罐，安全垫。
    2. **矛 (稳健增长)**: 目标占比 30%。关注：基建、科技巨头、AI 数据中心 (如 PAVE, QQQM, GOOGL)。逻辑：确定性增长。
    3. **剑 (进攻博弈)**: 目标占比 20%。关注：铜矿、铀矿、商业航天 (如 COPX, URA, ASTS)。逻辑：高风险高回报，博取爆发。

    当前组合状态:
    ${JSON.stringify(bucketSummary)}

    组合总价值: $${totalValue.toFixed(2)}

    任务:
    1. 分析当前配置与目标配置之间的偏差。
    2. 给出一个 "策略执行评分" (0-100)，基于用户对 50/30/20 模型的执行程度。
    3. 判定当前的风险等级 (Low/Moderate/High)。
    4. 提供 3 条具体的调仓建议 (例如："卖出部分 X，买入 Y，以将 '盾' 的比例提升至 50%")。

    **重要：请务必使用简体中文 (Simplified Chinese) 回复所有内容。**
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