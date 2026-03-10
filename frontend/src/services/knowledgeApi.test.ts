import { describe, it, expect, vi, beforeEach } from 'vitest';
import { knowledgeApi } from './knowledgeApi';
import api from './api';

// Mock the api instance
vi.mock('./api', () => ({
    default: {
        get: vi.fn(),
        post: vi.fn(),
        delete: vi.fn(),
    },
}));

describe('knowledgeApi', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('listKBs calls the correct endpoint', async () => {
        const mockData = { data: [{ id: 'kb_1', name: 'Test KB' }] };
        (api.get as any).mockResolvedValue(mockData);

        const response = await knowledgeApi.listKBs();

        expect(api.get).toHaveBeenCalledWith('/knowledge');
        expect(response).toEqual(mockData);
    });

    it('createKB calls the correct endpoint with data', async () => {
        const kbData = { name: 'New KB', description: 'desc' };
        const mockResponse = { data: { id: 'kb_new', ...kbData } };
        (api.post as any).mockResolvedValue(mockResponse);

        const response = await knowledgeApi.createKB(kbData);

        expect(api.post).toHaveBeenCalledWith('/knowledge', kbData);
        expect(response).toEqual(mockResponse);
    });

    it('getKB calls the correct endpoint', async () => {
        const kbId = 'kb_123';
        (api.get as any).mockResolvedValue({ data: { id: kbId } });

        await knowledgeApi.getKB(kbId);

        expect(api.get).toHaveBeenCalledWith(`/knowledge/${kbId}`);
    });

    it('uploadDoc uses FormData and correct headers', async () => {
        const file = new File(['content'], 'test.txt', { type: 'text/plain' });
        (api.post as any).mockResolvedValue({ data: { id: 'doc_1' } });

        await knowledgeApi.uploadDoc(file);

        expect(api.post).toHaveBeenCalledWith(
            '/knowledge/documents',
            expect.any(FormData),
            expect.objectContaining({
                headers: { 'Content-Type': 'multipart/form-data' },
            })
        );
    });

    it('searchKB calls the correct endpoint with params', async () => {
        const kbId = 'kb_1';
        const query = 'test query';
        (api.post as any).mockResolvedValue({ data: { results: [] } });

        await knowledgeApi.searchKB(kbId, query);

        expect(api.post).toHaveBeenCalledWith(
            `/knowledge/${kbId}/search`,
            { query, search_type: 'hybrid', top_k: 5 }
        );
    });
});
