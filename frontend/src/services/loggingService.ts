import axios from 'axios';

const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export interface LogEntry {
  level: 'info' | 'error' | 'warning' | 'debug';
  module: string;
  message: string;
  trace_id?: string;
  data?: any;
}

// 🛡️ [Harden]: Safe JSON stringification to prevent circular structure crashes (TASK-FE-GOV-001)
function safeStringify(obj: any): string {
  const cache = new Set();
  return JSON.stringify(obj, (key, value) => {
    if (typeof value === 'object' && value !== null) {
      if (cache.has(value)) {
        return '[Circular]';
      }
      cache.add(value);
    }
    return value;
  });
}

class LoggingService {
  private queue: LogEntry[] = [];
  private flushInterval: number = 5000; // 5 seconds
  private maxBatchSize: number = 20;

  constructor() {
    this.startAutoFlush();
    this.interceptConsole();
  }

  public log(entry: LogEntry) {
    this.queue.push(entry);
    if (this.queue.length >= this.maxBatchSize) {
      this.flush();
    }
  }

  private async flush() {
    if (this.queue.length === 0) return;

    const batch = [...this.queue];
    this.queue = [];

    try {
      await axios.post(`${API_BASE}/logs/ingest`, { batch });
    } catch (error) {
      // Don't log to console here to avoid recursion if console is intercepted
    }
  }

  private startAutoFlush() {
    setInterval(() => this.flush(), this.flushInterval);
  }

  private interceptConsole() {
    const originalLog = console.log;
    const originalError = console.error;
    const originalWarn = console.warn;

    console.log = (...args) => {
      originalLog(...args);
      this.log({
        level: 'info',
        module: 'console',
        message: args.map(a => {
            try {
                return typeof a === 'object' ? safeStringify(a) : String(a);
            } catch {
                return '[Serialization Error]';
            }
        }).join(' '),
      });
    };

    console.error = (...args) => {
      originalError(...args);
      this.log({
        level: 'error',
        module: 'console-error',
        message: args.map(a => {
            try {
                return typeof a === 'object' ? safeStringify(a) : String(a);
            } catch {
                return '[Serialization Error]';
            }
        }).join(' '),
      });
    };

    console.warn = (...args) => {
      originalWarn(...args);
      this.log({
        level: 'warning',
        module: 'console-warn',
        message: args.map(a => {
            try {
                return typeof a === 'object' ? safeStringify(a) : String(a);
            } catch {
                return '[Serialization Error]';
            }
        }).join(' '),
      });
    };
  }
}

export const loggingService = new LoggingService();
