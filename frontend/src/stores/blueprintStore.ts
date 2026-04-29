/**
 * Blueprint wizard store — drafts a Blueprint locally, persists to localStorage.
 *
 * The wizard is intentionally state-light: this store owns the in-progress
 * draft + active job; everything else (assets list, job polling) is fetched
 * directly from the API by the page component.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { BlueprintDraft, ExportJob } from '../services/exportApi';

const DEFAULT_DRAFT: BlueprintDraft = {
    name: 'quote-bot',
    version: '1.0.0',
    customer: '',
    description: '',
    platform_mode: 'agent',
    ui_mode: 'single_agent',
    llm: {
        provider: 'openai',
        model: 'gpt-4o-mini',
    },
    agents: [
        {
            id: 'quote-bot',
            name: '报价助手',
            system_prompt: '',
            skills: [],
            mcp_servers: [],
        },
    ],
    default_agent_id: 'quote-bot',
    knowledge_bases: [],
    extra_paths: [],
    env_overrides: {
        DISABLE_TELEMETRY: true,
    },
};

interface BlueprintStoreState {
    draft: BlueprintDraft;
    activeJob: ExportJob | null;
    setDraft: (patch: Partial<BlueprintDraft>) => void;
    replaceDraft: (next: BlueprintDraft) => void;
    resetDraft: () => void;
    upsertAgent: (index: number, patch: Partial<BlueprintDraft['agents'][number]>) => void;
    addAgent: (agent?: Partial<BlueprintDraft['agents'][number]>) => void;
    removeAgent: (index: number) => void;
    setActiveJob: (job: ExportJob | null) => void;
    patchJob: (patch: Partial<ExportJob>) => void;
}

/** Generate an unused agent id like "agent-2", "agent-3", … */
function nextAgentId(existing: BlueprintDraft['agents']): string {
    const used = new Set(existing.map((a) => a.id));
    for (let i = existing.length + 1; i < 1000; i++) {
        const candidate = `agent-${i}`;
        if (!used.has(candidate)) return candidate;
    }
    return `agent-${Date.now()}`;
}

export const useBlueprintStore = create<BlueprintStoreState>()(
    persist(
        (set) => ({
            draft: DEFAULT_DRAFT,
            activeJob: null,
            setDraft: (patch) =>
                set((s) => ({ draft: { ...s.draft, ...patch } })),
            replaceDraft: (next) => set({ draft: next }),
            resetDraft: () => set({ draft: DEFAULT_DRAFT, activeJob: null }),
            upsertAgent: (index, patch) =>
                set((s) => {
                    const agents = s.draft.agents.slice();
                    if (index < 0 || index >= agents.length) return s;
                    const prev = agents[index];
                    const next = { ...prev, ...patch };
                    agents[index] = next;
                    // If the renamed id was the default, follow it.
                    const draft: BlueprintDraft = { ...s.draft, agents };
                    if (
                        patch.id !== undefined &&
                        prev.id === s.draft.default_agent_id &&
                        patch.id !== prev.id
                    ) {
                        draft.default_agent_id = patch.id;
                    }
                    return { draft };
                }),
            addAgent: (agent) =>
                set((s) => {
                    const id = agent?.id || nextAgentId(s.draft.agents);
                    const newAgent = {
                        id,
                        name: agent?.name || id,
                        system_prompt: agent?.system_prompt || '',
                        skills: agent?.skills || [],
                        mcp_servers: agent?.mcp_servers || [],
                    };
                    return {
                        draft: {
                            ...s.draft,
                            agents: [...s.draft.agents, newAgent],
                        },
                    };
                }),
            removeAgent: (index) =>
                set((s) => {
                    if (s.draft.agents.length <= 1) return s; // keep at least one
                    if (index < 0 || index >= s.draft.agents.length) return s;
                    const removed = s.draft.agents[index];
                    const agents = s.draft.agents.filter((_, i) => i !== index);
                    const draft: BlueprintDraft = { ...s.draft, agents };
                    if (s.draft.default_agent_id === removed.id) {
                        draft.default_agent_id = agents[0]?.id || null;
                    }
                    return { draft };
                }),
            setActiveJob: (job) => set({ activeJob: job }),
            patchJob: (patch) =>
                set((s) => (s.activeJob ? { activeJob: { ...s.activeJob, ...patch } } : s)),
        }),
        {
            name: 'hivemind.blueprint-draft.v1',
            partialize: (s) => ({ draft: s.draft }),
        }
    )
);

export const DEFAULT_BLUEPRINT_DRAFT = DEFAULT_DRAFT;
