import React, { useState, useEffect } from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';
import { Activity, Cpu, AlertTriangle, Zap, Server } from 'lucide-react';
import { api } from '../lib/api';

interface MetricSummary {
  latency_p95_ms: number;
  error_rate: number;
  gpu_memory_used_pct: number;
  throughput_rps: number;
  data_drift_score: number;
  service: string;
}

interface MetricHistoryPoint {
  timestamp: string;
  latency_p95_ms: number;
  error_rate: number;
  gpu_memory_used_pct: number;
  throughput_rps: number;
  data_drift_score: number;
}

export const MetricsPanel: React.FC = () => {
  const [current, setCurrent] = useState<MetricSummary | null>(null);
  const [history, setHistory] = useState<MetricHistoryPoint[]>([]);
  const [activeTab, setActiveTab] = useState<'latency' | 'errors' | 'gpu' | 'throughput' | 'drift'>('latency');
  const [error, setError] = useState<string | null>(null);

  // Poll simulator metrics and fetch history
  useEffect(() => {
    const fetchData = async () => {
      try {
        const live = await api.getMetricsSummary();
        setCurrent(live);
        
        // Take a snapshot and add to database records
        await api.takeSnapshot();
        
        const hist = await api.getMetricsHistory(30);
        // Format dates for display
        const formatted = hist.map((pt: any) => ({
          ...pt,
          time: new Date(pt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        })).reverse();
        setHistory(formatted);
        setError(null);
      } catch (err: any) {
        console.error('Metrics fetch error:', err);
        setError('Cannot connect to simulator. Make sure docker compose or mock_inference service is running.');
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 4000);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="glass-panel" style={{ padding: '1.5rem', borderLeft: '4px solid var(--danger)' }}>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
          <AlertTriangle color="var(--danger)" />
          <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Simulator Unreachable</h3>
        </div>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.5rem' }}>{error}</p>
      </div>
    );
  }

  const metricConfigs = {
    latency: {
      label: 'p95 Latency',
      val: `${current?.latency_p95_ms ?? 0} ms`,
      dataKey: 'latency_p95_ms',
      color: '#06b6d4',
      icon: <Zap size={20} color="#06b6d4" />,
      desc: 'Observed vs 45ms Baseline',
      status: (current?.latency_p95_ms ?? 0) > 100 ? 'danger' : 'success'
    },
    errors: {
      label: 'Error Rate',
      val: `${((current?.error_rate ?? 0) * 100).toFixed(2)}%`,
      dataKey: 'error_rate',
      color: '#ef4444',
      icon: <AlertTriangle size={20} color="#ef4444" />,
      desc: 'Observed vs 0.5% Baseline',
      status: (current?.error_rate ?? 0) > 0.02 ? 'danger' : 'success'
    },
    gpu: {
      label: 'GPU Memory',
      val: `${((current?.gpu_memory_used_pct ?? 0) * 100).toFixed(0)}%`,
      dataKey: 'gpu_memory_used_pct',
      color: '#a855f7',
      icon: <Cpu size={20} color="#a855f7" />,
      desc: 'Memory usage and fragmentation',
      status: (current?.gpu_memory_used_pct ?? 0) > 0.85 ? 'warning' : 'success'
    },
    throughput: {
      label: 'Throughput',
      val: `${current?.throughput_rps ?? 0} rps`,
      dataKey: 'throughput_rps',
      color: '#10b981',
      icon: <Activity size={20} color="#10b981" />,
      desc: 'Requests processed per second',
      status: (current?.throughput_rps ?? 1200) < 600 ? 'warning' : 'success'
    },
    drift: {
      label: 'Data Drift',
      val: `${current?.data_drift_score ?? 0} PSI`,
      dataKey: 'data_drift_score',
      color: '#f59e0b',
      icon: <Server size={20} color="#f59e0b" />,
      desc: 'Population stability index',
      status: (current?.data_drift_score ?? 0) > 0.1 ? 'warning' : 'success'
    }
  };

  const activeConf = metricConfigs[activeTab];

  return (
    <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            Telemetry Streams <span style={{ fontSize: '0.75rem', fontWeight: 400, color: 'var(--text-muted)' }}>({current?.service})</span>
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Real-time production service metric telemetry</p>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
        {(Object.keys(metricConfigs) as Array<keyof typeof metricConfigs>).map((key) => {
          const cfg = metricConfigs[key];
          const isSelected = activeTab === key;
          const statusColor = cfg.status === 'danger' ? 'var(--danger)' : cfg.status === 'warning' ? 'var(--warning)' : 'var(--success)';
          
          return (
            <div 
              key={key}
              onClick={() => setActiveTab(key)}
              style={{
                padding: '1rem',
                borderRadius: '8px',
                background: isSelected ? 'rgba(30, 41, 59, 0.4)' : 'rgba(15, 23, 42, 0.2)',
                border: `1px solid ${isSelected ? cfg.color : 'transparent'}`,
                cursor: 'pointer',
                transition: 'all 0.2s',
                boxShadow: isSelected ? `0 0 15px ${cfg.color}15` : 'none',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 500 }}>{cfg.label}</span>
                {cfg.icon}
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0.25rem 0' }}>{cfg.val}</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.7rem' }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: statusColor }}></span>
                <span style={{ color: 'var(--text-muted)' }}>{cfg.desc}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Metric Chart */}
      <div style={{ height: '260px', marginTop: '0.5rem', position: 'relative' }}>
        <h4 style={{ position: 'absolute', top: 0, left: 10, fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Historical {activeConf.label} Trend
        </h4>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={history} margin={{ top: 35, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id={`gradient-${activeTab}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={activeConf.color} stopOpacity={0.4}/>
                <stop offset="95%" stopColor={activeConf.color} stopOpacity={0}/>
              </linearGradient>
            </defs>
            <XAxis 
              dataKey="time" 
              stroke="var(--text-muted)" 
              fontSize={10}
              tickLine={false}
              axisLine={false}
            />
            <YAxis 
              stroke="var(--text-muted)" 
              fontSize={10} 
              tickLine={false}
              axisLine={false}
              domain={['auto', 'auto']}
            />
            <Tooltip
              contentStyle={{
                background: 'rgba(15, 23, 42, 0.95)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                color: 'var(--text-main)',
                fontSize: '0.8rem',
              }}
            />
            <Area 
              type="monotone" 
              dataKey={activeConf.dataKey} 
              stroke={activeConf.color} 
              strokeWidth={2}
              fillOpacity={1} 
              fill={`url(#gradient-${activeTab})`} 
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
