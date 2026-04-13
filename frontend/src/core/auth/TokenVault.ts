/**
 * 🛰️ [Architecture-Gate]: TokenVault — 统一身份凭证保险箱
 * 策略:
 *   - sessionStorage: 用于标签页 (Tab) 级的身份物理隔离，解决多用户覆盖。
 *   - localStorage: 仅用于辅助 "记住我" 策略和跨 Session 的 UID 索引。
 *   - 单一入口: 严禁在非 TokenVault 模块直接操作凭证读写。
 */
class TokenVault {
    private static readonly ACCESS_KEY  = 'hm_access_token';
    private static readonly REFRESH_KEY = 'hm_refresh_token';
    private static readonly USER_KEY    = 'hm_active_user_id';
    private static readonly LAST_USER   = 'hm_last_user_id';

    /** 
     * 获取访问令牌
     * 优先从当前标签页会话获取，确保 Tab 间隔离。
     */
    getAccessToken(): string | null {
        return sessionStorage.getItem(TokenVault.ACCESS_KEY) || localStorage.getItem(TokenVault.ACCESS_KEY);
    }

    /** 
     * 设置令牌并关联活跃用户
     * 同时通过状态更新同步到后端请求头。
     */
    setTokens(access: string, refresh?: string, userId?: string): void {
        sessionStorage.setItem(TokenVault.ACCESS_KEY, access);
        if (refresh) sessionStorage.setItem(TokenVault.REFRESH_KEY, refresh);
        if (userId) {
            sessionStorage.setItem(TokenVault.USER_KEY, userId);
            localStorage.setItem(TokenVault.LAST_USER, userId); // 用于离线索引恢复
        }
    }

    /** 
     * 获取当前活跃用户 ID
     * 用于驱动 IndexedDB 命名空间隔离。
     */
    getActiveUserId(): string | null {
        return sessionStorage.getItem(TokenVault.USER_KEY) || localStorage.getItem(TokenVault.LAST_USER);
    }

    /** 
     * 彻底清除凭证 (退出登录或 401 时调用)
     */
    clear(): void {
        sessionStorage.removeItem(TokenVault.ACCESS_KEY);
        sessionStorage.removeItem(TokenVault.REFRESH_KEY);
        sessionStorage.removeItem(TokenVault.USER_KEY);
        localStorage.removeItem(TokenVault.ACCESS_KEY); // Also clear persistent recovery token
        // 不清除 LAST_USER, 允许离线预读取历史配置
    }

    /** 
     * 记住我: 持久化 RefreshToken 到磁盘 (加密或混淆后存入)
     */
    persistForAuthRecovery(refresh: string, userId: string): void {
        localStorage.setItem(`hm_recovery_${userId}`, refresh);
        localStorage.setItem(TokenVault.LAST_USER, userId);
    }

    /** 
     * 恢复持久化令牌
     */
    getRecoveryToken(): string | null {
        const lastUid = localStorage.getItem(TokenVault.LAST_USER);
        if (!lastUid) return null;
        return localStorage.getItem(`hm_recovery_${lastUid}`);
    }
}

export const tokenVault = new TokenVault();
