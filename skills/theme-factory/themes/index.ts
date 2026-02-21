/**
 * HiveMind Theme Registry
 * 
 * 所有可用主题的元数据索引。
 * 前端 SettingsPage 可 import 此文件展示主题选择器。
 */

export interface ThemeDefinition {
    id: string;
    name: string;
    nameZh: string;
    description: string;
    preview: {
        bgDeepest: string;
        bgBase: string;
        brand: string;
        accent: string;
    };
    tags: string[];
}

export const THEMES: ThemeDefinition[] = [
    {
        id: 'cyber-refined',
        name: 'Cyber Refined',
        nameZh: '赛博精炼',
        description: '默认主题 — 深青蓝底 + 青绿主色',
        preview: { bgDeepest: '#0A0E1A', bgBase: '#111827', brand: '#06D6A0', accent: '#118AB2' },
        tags: ['default', 'dark', 'tech'],
    },
    {
        id: 'ocean-depths',
        name: 'Ocean Depths',
        nameZh: '海洋深处',
        description: '专业冷静的深海蓝绿，适合商务场景',
        preview: { bgDeepest: '#0B1929', bgBase: '#132F4C', brand: '#2D8B8B', accent: '#A8DADC' },
        tags: ['professional', 'dark', 'calm'],
    },
    {
        id: 'sunset-boulevard',
        name: 'Sunset Boulevard',
        nameZh: '日落大道',
        description: '温暖活力的橙色调，适合创意团队',
        preview: { bgDeepest: '#1A0F0A', bgBase: '#2D1810', brand: '#FF6B35', accent: '#FFD166' },
        tags: ['warm', 'dark', 'creative'],
    },
    {
        id: 'forest-canopy',
        name: 'Forest Canopy',
        nameZh: '森林华盖',
        description: '自然沉稳的森林绿调，适合环保科技',
        preview: { bgDeepest: '#0A1A0E', bgBase: '#142D18', brand: '#4CAF50', accent: '#81C784' },
        tags: ['nature', 'dark', 'calm'],
    },
    {
        id: 'modern-minimalist',
        name: 'Modern Minimalist',
        nameZh: '现代极简',
        description: '清晰现代的灰色调，适合通用商务',
        preview: { bgDeepest: '#0E0E12', bgBase: '#1A1A22', brand: '#8B8B9E', accent: '#B0B0C8' },
        tags: ['minimal', 'dark', 'neutral'],
    },
    {
        id: 'golden-hour',
        name: 'Golden Hour',
        nameZh: '黄金时刻',
        description: '温暖秋季金色调，适合内容平台',
        preview: { bgDeepest: '#141008', bgBase: '#231C0E', brand: '#D4A017', accent: '#E8C547' },
        tags: ['warm', 'dark', 'elegant'],
    },
    {
        id: 'arctic-frost',
        name: 'Arctic Frost',
        nameZh: '极地寒霜',
        description: '冰蓝通透色调，适合数据分析',
        preview: { bgDeepest: '#080E18', bgBase: '#101828', brand: '#56CCF2', accent: '#A0E4FF' },
        tags: ['cool', 'dark', 'data'],
    },
    {
        id: 'desert-rose',
        name: 'Desert Rose',
        nameZh: '沙漠玫瑰',
        description: '柔和优雅的玫瑰色调，适合设计产品',
        preview: { bgDeepest: '#16090E', bgBase: '#2A141B', brand: '#D4727E', accent: '#E8A0A8' },
        tags: ['soft', 'dark', 'elegant'],
    },
    {
        id: 'tech-innovation',
        name: 'Tech Innovation',
        nameZh: '科技创新',
        description: '高对比度电光蓝，适合 AI/ML 产品',
        preview: { bgDeepest: '#0A0A14', bgBase: '#12121E', brand: '#0066FF', accent: '#00DDFF' },
        tags: ['bold', 'dark', 'tech'],
    },
    {
        id: 'botanical-garden',
        name: 'Botanical Garden',
        nameZh: '植物园',
        description: '清新有机的植物绿，适合健康科技',
        preview: { bgDeepest: '#0A1510', bgBase: '#142A1A', brand: '#66BB6A', accent: '#AED581' },
        tags: ['fresh', 'dark', 'organic'],
    },
    {
        id: 'midnight-galaxy',
        name: 'Midnight Galaxy',
        nameZh: '午夜星河',
        description: '深紫宇宙色调，适合创意/游戏场景',
        preview: { bgDeepest: '#0D0A1A', bgBase: '#1A1432', brand: '#7C4DFF', accent: '#B388FF' },
        tags: ['cosmic', 'dark', 'creative'],
    },
];

export const DEFAULT_THEME = 'cyber-refined';

export function getTheme(id: string): ThemeDefinition | undefined {
    return THEMES.find(t => t.id === id);
}
