import { openDB, type IDBPDatabase } from 'idb';
import { tokenVault } from './auth/TokenVault';

/**
 * 🛰️ [HMER Phase 2] Local Edge Engine
 * 本地持久化引擎：处理 IndexedDB 存储与同步。
 * 这是击碎网络延迟、实现离线可用性的基石。
 * 
 * @covers REQ-015
 */
class LocalEdgeEngine {
    private dbPromise: Promise<IDBPDatabase<any>> | null = null;
    private get DB_NAME() {
        const uid = tokenVault.getActiveUserId() || 'anonymous';
        return `HiveMind_Edge_Cache_${uid}`;
    }
    private VERSION = 1;

    constructor() {
        this.init();
    }

    private init() {
        this.dbPromise = openDB(this.DB_NAME, this.VERSION, {
            upgrade(db) {
                // 会话列表存储 (Conversation List)
                if (!db.objectStoreNames.contains('conversations')) {
                    db.createObjectStore('conversations', { keyPath: 'id' });
                }
                // 消息内容增量缓存 (Messages)
                if (!db.objectStoreNames.contains('messages')) {
                    const store = db.createObjectStore('messages', { keyPath: 'id' });
                    store.createIndex('conversationId', 'conversationId');
                }
                // 系统快照 (System Status/Meta)
                if (!db.objectStoreNames.contains('meta')) {
                    db.createObjectStore('meta');
                }
            },
        });
    }

    /** 存入持久化数据 */
    async put(storeName: string, data: any) {
        const db = await this.dbPromise;
        if (!db) return;
        return db.put(storeName, data);
    }

    /** 读取持久化数据 */
    async get(storeName: string, id: string) {
        const db = await this.dbPromise;
        if (!db) return;
        return db.get(storeName, id);
    }

    /** 获取 Store 下的所有数据 */
    async getAll(storeName: string) {
        const db = await this.dbPromise;
        if (!db) return [];
        return db.getAll(storeName);
    }

    /** 批量存入 (用于首次同步) */
    async batchPut(storeName: string, items: any[]) {
        const db = await this.dbPromise;
        if (!db) return;
        const tx = db.transaction(storeName, 'readwrite');
        await Promise.all([
            ...items.map(item => tx.store.put(item)),
            tx.done,
        ]);
    }
}

export const edgeEngine = new LocalEdgeEngine();
