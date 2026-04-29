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
    setActiveJob: (job: ExportJob | null) => void;
    patchJob: (patch: Partial<ExportJob>) => void;
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
                    agents[index] = { ...agents[index], ...patch };
                    return { draft: { ...s.draft, agents } };
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
