/**
 * Quick Commands 单元测试 — 验证平台模式过滤逻辑。
 *
 * 测试覆盖:
 *   1. full 模式下所有指令可匹配
 *   2. rag 模式下 Agent 指令被过滤
 *   3. agent 模式下 RAG 指令被过滤
 *   4. core 指令在任何模式下都可用
 */

import { describe, it, expect } from 'vitest';
import { matchQuickCommand, QUICK_COMMANDS } from '../quickCommands';

describe('matchQuickCommand', () => {
    // ── Full 模式 ──────────────────────────────────────────

    it('should match RAG commands in full mode', () => {
        const cmd = matchQuickCommand('创建知识库', { ragEnabled: true, agentEnabled: true });
        expect(cmd).not.toBeNull();
        expect(cmd!.id).toBe('create_kb');
    });

    it('should match Agent commands in full mode', () => {
        const cmd = matchQuickCommand('查看 agent', { ragEnabled: true, agentEnabled: true });
        expect(cmd).not.toBeNull();
        expect(cmd!.id).toBe('nav_agents');
    });

    it('should match core commands in full mode', () => {
        const cmd = matchQuickCommand('去设置', { ragEnabled: true, agentEnabled: true });
        expect(cmd).not.toBeNull();
        expect(cmd!.id).toBe('nav_settings');
    });

    // ── RAG 模式 ──────────────────────────────────────────

    it('should match RAG commands in rag mode', () => {
        const cmd = matchQuickCommand('创建知识库', { ragEnabled: true, agentEnabled: false });
        expect(cmd).not.toBeNull();
        expect(cmd!.id).toBe('create_kb');
    });

    it('should NOT match Agent commands in rag mode', () => {
        const cmd = matchQuickCommand('查看 agent', { ragEnabled: true, agentEnabled: false });
        expect(cmd).toBeNull();
    });

    it('should match core commands in rag mode', () => {
        const cmd = matchQuickCommand('安全中心', { ragEnabled: true, agentEnabled: false });
        expect(cmd).not.toBeNull();
        expect(cmd!.id).toBe('nav_security');
    });

    // ── Agent 模式 ────────────────────────────────────────

    it('should match Agent commands in agent mode', () => {
        const cmd = matchQuickCommand('查看 agent', { ragEnabled: false, agentEnabled: true });
        expect(cmd).not.toBeNull();
        expect(cmd!.id).toBe('nav_agents');
    });

    it('should NOT match RAG commands in agent mode', () => {
        const cmd = matchQuickCommand('创建知识库', { ragEnabled: false, agentEnabled: true });
        expect(cmd).toBeNull();
    });

    it('should match core commands in agent mode', () => {
        const cmd = matchQuickCommand('首页', { ragEnabled: false, agentEnabled: true });
        expect(cmd).not.toBeNull();
        expect(cmd!.id).toBe('nav_dashboard');
    });

    // ── 边界情况 ──────────────────────────────────────────

    it('should default to full mode when no options provided', () => {
        const ragCmd = matchQuickCommand('创建知识库');
        const agentCmd = matchQuickCommand('查看 agent');
        expect(ragCmd).not.toBeNull();
        expect(agentCmd).not.toBeNull();
    });

    it('should return null for unrecognized input', () => {
        const cmd = matchQuickCommand('xyzzy nonsense');
        expect(cmd).toBeNull();
    });

    it('should be case insensitive', () => {
        const cmd = matchQuickCommand('CREATE KB', { ragEnabled: true, agentEnabled: true });
        expect(cmd).not.toBeNull();
        expect(cmd!.id).toBe('create_kb');
    });
});

describe('QUICK_COMMANDS module classification', () => {
    it('every command should have a valid module field', () => {
        for (const cmd of QUICK_COMMANDS) {
            expect(['core', 'rag', 'agent']).toContain(cmd.module);
        }
    });

    it('should have at least one command per module type', () => {
        const modules = new Set(QUICK_COMMANDS.map(c => c.module));
        expect(modules.has('core')).toBe(true);
        expect(modules.has('rag')).toBe(true);
        expect(modules.has('agent')).toBe(true);
    });
});
