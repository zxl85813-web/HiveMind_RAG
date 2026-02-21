/**
 * StatCard — 统计数据卡片。
 *
 * 统一所有数据概览卡片的样式和结构。
 * 支持图标、渐变背景、趋势指示。
 *
 * 用法:
 *   <StatCard
 *     title="活跃 Agent"
 *     value={5}
 *     icon={<ClusterOutlined />}
 *     color="primary"
 *   />
 *
 * @module components/common
 * @see REGISTRY.md > 前端 > 组件 > StatCard
 */

import React from 'react';
import { Card, Statistic, Flex } from 'antd';
import styles from './StatCard.module.css';

type ColorPreset = 'primary' | 'success' | 'warning' | 'error' | 'info';

const colorMap: Record<ColorPreset, string> = {
    primary: 'rgba(6, 214, 160, 0.12)',
    success: 'rgba(6, 214, 160, 0.12)',
    warning: 'rgba(255, 209, 102, 0.12)',
    error: 'rgba(239, 71, 111, 0.12)',
    info: 'rgba(17, 138, 178, 0.12)',
};

const iconColorMap: Record<ColorPreset, string> = {
    primary: '#06D6A0',
    success: '#06D6A0',
    warning: '#FFD166',
    error: '#EF476F',
    info: '#118AB2',
};

export interface StatCardProps {
    /** 指标标题 */
    title: string;
    /** 指标值 */
    value: number | string;
    /** 图标 */
    icon?: React.ReactNode;
    /** 颜色预设 */
    color?: ColorPreset;
    /** 后缀文字 */
    suffix?: string;
    /** 说明文字 */
    description?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
    title,
    value,
    icon,
    color = 'primary',
    suffix,
    description,
}) => {
    return (
        <Card className={styles.card} hoverable>
            <Flex align="center" gap={16}>
                {icon && (
                    <div
                        className={styles.iconWrap}
                        style={{ background: colorMap[color] }}
                    >
                        <span style={{ color: iconColorMap[color], fontSize: 22 }}>{icon}</span>
                    </div>
                )}
                <div>
                    <Statistic title={title} value={value} suffix={suffix} />
                    {description && (
                        <span className={styles.desc}>{description}</span>
                    )}
                </div>
            </Flex>
        </Card>
    );
};
