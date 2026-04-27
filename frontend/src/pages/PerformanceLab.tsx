import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Database, 
  Lock, 
  AlertTriangle, 
  RefreshCcw, 
  Zap,
  TrendingUp,
  Terminal,
  Search
} from 'lucide-react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts';

// 🏗️ [FE-GOV]: Performance Lab — Real-time DB Monitoring & Stress Testing
const PerformanceLab: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [drillStatus, setDrillStatus] = useState<'idle' | 'running' | 'done'>('idle');

  // Simulated live updates (In a real app, use WebSocket or SWR)
  useEffect(() => {
    const fetchData = async () => {
      try {
        // Mocking API call for demo (Replace with real fetch if backend is up)
        // const res = await fetch('/api/v1/performance/db/stats');
        // const data = await res.json();
        
        const mockData = {
          locks: { total: Math.floor(Math.random() * 5), waiting: Math.random() > 0.8 ? 1 : 0 },
          activity: { 
            active: 2 + Math.floor(Math.random() * 5), 
            avg_duration_ms: 15 + Math.random() * 30 
          },
          cache: { hit_ratio: 99.2 + Math.random() * 0.5 },
          timestamp: new Date().toLocaleTimeString()
        };

        setStats(mockData);
        setHistory(prev => [...prev.slice(-19), mockData]);
      } catch (err) {
        console.error("Failed to fetch DB stats", err);
      }
    };

    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  const triggerDrill = async () => {
    setLoading(true);
    setDrillStatus('running');
    // API Call: POST /api/v1/performance/db/drill/deadlock
    setTimeout(() => {
      setLoading(false);
      setDrillStatus('done');
    }, 5000);
  };

  return (
    <div className="p-8 bg-slate-950 min-h-screen text-slate-200 font-sans">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            Database Performance Lab
          </h1>
          <p className="text-slate-400 mt-1">Real-time DB contention analysis & deadlock verification</p>
        </div>
        <div className="flex gap-4">
          <button 
            onClick={triggerDrill}
            disabled={loading}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-semibold transition-all ${
              drillStatus === 'running' 
              ? 'bg-amber-500/20 text-amber-500 border border-amber-500/50' 
              : 'bg-emerald-500/20 text-emerald-500 border border-emerald-500/50 hover:bg-emerald-500/30'
            }`}
          >
            {drillStatus === 'running' ? <RefreshCcw className="animate-spin size-5" /> : <AlertTriangle className="size-5" />}
            {drillStatus === 'running' ? 'Simulating Deadlock...' : 'Trigger Deadlock Drill'}
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <StatCard 
          icon={<Zap className="text-cyan-400" />} 
          label="Avg. Query Latency" 
          value={`${stats?.activity?.avg_duration_ms?.toFixed(1) || 0}ms`} 
          trend="+2.1%"
          trendUp={false}
        />
        <StatCard 
          icon={<Lock className="text-amber-400" />} 
          label="Active Locks" 
          value={stats?.locks?.total || 0} 
          trend={stats?.locks?.waiting > 0 ? "WAITING" : "STABLE"}
          trendUp={stats?.locks?.waiting > 0}
        />
        <StatCard 
          icon={<Activity className="text-emerald-400" />} 
          label="Active Connections" 
          value={stats?.activity?.active || 0} 
          trend="Optimal"
        />
        <StatCard 
          icon={<Database className="text-purple-400" />} 
          label="Cache Hit Ratio" 
          value={`${stats?.cache?.hit_ratio?.toFixed(2) || 0}%`} 
          trend="High"
        />
        <StatCard 
          icon={<Search className="text-blue-400" />} 
          label="ES Status / Top-K" 
          value={`${stats?.es?.status === 'green' ? 'Healthy' : 'Warning'} (K=30)`} 
          trend={stats?.es?.indices_count + " Indices"}
          trendUp={stats?.es?.status !== 'green'}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Latency Chart */}
        <div className="lg:col-span-2 bg-slate-900/50 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl">
          <div className="flex items-center justify-between mb-6">
            <h3 className="flex items-center gap-2 text-lg font-semibold">
              <TrendingUp className="text-cyan-400 size-5" />
              Latency & Recall Efficiency
            </h3>
            <span className="text-xs text-slate-500 italic">Rerank configured: Top-K=30, Top-N=10</span>
          </div>
          <div className="h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={history}>
                <defs>
                  <linearGradient id="colorLatency" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--hm-color-info)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--hm-color-info)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--hm-color-border)" vertical={false} />
                <XAxis dataKey="timestamp" stroke="var(--hm-color-text-secondary)" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--hm-color-text-secondary)" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--hm-color-bg-layout)', border: '1px solid var(--hm-color-border)', borderRadius: '12px' }}
                  itemStyle={{ color: 'var(--hm-color-info)' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="activity.avg_duration_ms" 
                  stroke="var(--hm-color-info)" 
                  strokeWidth={3}
                  fillOpacity={1} 
                  fill="url(#colorLatency)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Live Trace / Audit Logs */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl flex flex-col">
          <h3 className="flex items-center gap-2 text-lg font-semibold mb-6">
            <Terminal className="text-emerald-400 size-5" />
            Live SQL Trace
          </h3>
          <div className="flex-1 overflow-hidden">
            <div className="space-y-4 font-mono text-sm">
              <TraceLog id="tr-821x" sql="SELECT * FROM messages WHERE conv_id = ..." time="12:45:01" status="success" />
              <TraceLog id="tr-822x" sql="UPDATE conversations SET title = ..." time="12:45:02" status="success" />
              <TraceLog id="tr-823x" sql="BEGIN TRANSACTION (AB-BA Probe)" time="12:45:05" status="warning" />
              {drillStatus === 'running' && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded text-amber-500 animate-pulse">
                  [DEADLOCK_PROBE] Waiting for ShareLock on Row: conv_552
                </div>
              )}
              <TraceLog id="tr-824x" sql="COMMIT" time="12:45:10" status="success" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const StatCard = ({ icon, label, value, trend, trendUp }: any) => (
  <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-2xl backdrop-blur-xl">
    <div className="flex items-center gap-3 mb-4">
      <div className="p-2 bg-slate-800 rounded-lg">{icon}</div>
      <span className="text-slate-400 text-sm font-medium">{label}</span>
    </div>
    <div className="flex items-end justify-between">
      <span className="text-2xl font-bold">{value}</span>
      <span className={`text-xs font-bold px-2 py-1 rounded ${trendUp ? 'bg-red-500/10 text-red-500' : 'bg-emerald-500/10 text-emerald-500'}`}>
        {trend}
      </span>
    </div>
  </div>
);

const TraceLog = ({ id, sql, time, status }: any) => (
  <div className="p-3 border-l-2 border-slate-700 bg-slate-800/30 rounded-r">
    <div className="flex items-center justify-between mb-1">
      <span className="text-[10px] px-1 bg-slate-700 rounded text-slate-400 uppercase">{id}</span>
      <span className="text-[10px] text-slate-500">{time}</span>
    </div>
    <div className="truncate text-slate-300 italic">{sql}</div>
    <div className={`text-[10px] mt-1 uppercase font-bold ${status === 'success' ? 'text-emerald-500' : 'text-amber-500'}`}>
      ● {status}
    </div>
  </div>
);

export default PerformanceLab;
