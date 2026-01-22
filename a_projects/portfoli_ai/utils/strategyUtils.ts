
export type StrategyType = 'Shield' | 'Spear' | 'Sword';

export interface StrategyBucketInfo {
    type: StrategyType;
    name: string;
    icon: string; // 'Shield' | 'Zap' | 'Swords'
    color: string;
    description: string;
}

export const STRATEGY_DEFINITIONS: Record<StrategyType, StrategyBucketInfo> = {
    Shield: {
        type: 'Shield',
        name: '盾 (防守底仓)',
        icon: 'Shield',
        color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
        description: '高股息 / 标普500'
    },
    Spear: {
        type: 'Spear',
        name: '矛 (稳健增长)',
        icon: 'Zap',
        color: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
        description: '科技巨头 / 行业龙头'
    },
    Sword: {
        type: 'Sword',
        name: '剑 (进攻博弈)',
        icon: 'Swords',
        color: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
        description: '周期资源 / 商业航天 / 高弹性'
    }
};

export const getStrategyBucket = (symbol: string, sector: string): StrategyType => {
    const sym = symbol.toUpperCase();

    // 1. Shield: High Dividend, S&P 500, Defensive Sectors
    if (
        ['SCHD', 'VOO', 'VTI', 'KO', 'PEP', 'JPM', 'PG', 'JNJ', 'O'].includes(sym) ||
        secMatches(sector, ['Financial', 'Consumer Defensive', 'Real Estate', 'Healthcare', 'Utilities'])
    ) {
        return 'Shield';
    }

    // 2. Sword: High Growth/Volatile, Commodities, Space
    if (
        ['ASTS', 'RKLB', 'COPX', 'URA', 'FCX', 'CCJ', 'PLTR', 'TSLA', 'NVDA', 'SMCI'].includes(sym) ||
        secMatches(sector, ['Basic Materials', 'Energy'])
    ) {
        // Note: Some tech/energy can be Sword if high beta
        return 'Sword';
    }

    // 3. Spear: Stable Growth, Big Tech (Default for others)
    return 'Spear';
};

const secMatches = (sector: string, targets: string[]) => {
    if (!sector) return false;
    return targets.some(t => sector.toLowerCase().includes(t.toLowerCase()));
};
