import React, { useState } from 'react';
import { Shield, Zap, AlertCircle, Play, RotateCcw, Activity } from 'lucide-react';
import { MetricsPanel } from './components/MetricsPanel';
import { AgentTraceView } from './components/AgentTraceView';
import { IncidentTimeline } from './components/IncidentTimeline';
import { ApprovalModal } from './components/ApprovalModal';
import { useAgentStream } from './hooks/useAgentStream';
import { api } from './lib/api';

export const App: React.FC = () => {
  const { events, activeAgent, currentIncidentId, isConnected, clearTrace } = useAgentStream();
  const [pendingIncident, setPendingIncident] = useState<any>(null);
  const [injecting, setInjecting] = useState<string | null>(null);
  const [injectSuccess, setInjectSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleScenarioInject = async (scenario: string) => {
    setInjecting(scenario);
    setInjectSuccess(null);
    setError(null);
    try {
      if (scenario === 'reset') {
        clearTrace();
      }
      await api.triggerScenario(scenario);
      setInjectSuccess(`Scenario '${scenario.replace('_', ' ')}' successfully injected!`);
      setTimeout(() => setInjectSuccess(null), 4000);
    } catch (err: any) {
      console.error('Scenario injection error:', err);
      setError(`Failed to inject scenario: ${err.message || err.response?.data?.detail}`);
    } finally {
      setInjecting(null);
    }
  };

  const scenarios = [
    { name: 'latency_spike', label: 'Latency Spike', desc: 'Rollout model v2. p95 latency jumps to ~675ms' },
    { name: 'error_spike', label: 'Error Spike', desc: 'Simulate high thread starvation, generating 5xx errors' },
    { name: 'gpu_oom', label: 'GPU Memory OOM', desc: 'Exhaust and fragment GPU vRAM (97% capacity)' },
    { name: 'data_drift', label: 'Data Drift Shift', desc: 'Shift client request distributions (PSI triggers > 0.1)' },
    { name: 'cascading_failure', label: 'Cascading Collapse', desc: 'Worst case: CPU, GPU, Latency, and Error rates collapse' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', paddingBottom: '3rem' }}>
      {/* Glow Header */}
      <header style={{
        background: 'rgba(15, 23, 42, 0.6)',
        backdropFilter: 'blur(10px)',
        borderBottom: '1px solid var(--border-color)',
        padding: '1rem 2rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        position: 'sticky',
        top: 0,
        zIndex: 1000,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{
            background: 'linear-gradient(135deg, var(--primary), var(--secondary))',
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 15px var(--primary-glow)',
          }}>
            <Shield size={20} color="white" />
          </div>
          <div>
            <h1 style={{ fontFamily: "'Outfit', sans-serif", fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              AEGIS <span style={{ fontSize: '0.65rem', fontWeight: 600, color: 'var(--primary)', border: '1px solid var(--primary)', padding: '0.1rem 0.3rem', borderRadius: '4px', letterSpacing: '0.05em' }}>OPS COMMAND</span>
            </h1>
            <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Multi-Agent Remediation and Auto-Operations Platform</p>
          </div>
        </div>

        {/* Status indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', background: 'rgba(255,255,255,0.03)', padding: '0.35rem 0.75rem', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: isConnected ? 'var(--success)' : 'var(--danger)',
              boxShadow: isConnected ? '0 0 10px var(--success)' : 'none',
              display: 'inline-block'
            }}></span>
            <span style={{ color: 'var(--text-muted)' }}>SSE Pipeline Stream:</span>
            <strong style={{ color: isConnected ? 'var(--text-main)' : 'var(--danger)' }}>
              {isConnected ? 'ONLINE' : 'OFFLINE'}
            </strong>
          </div>
        </div>
      </header>

      {/* Main Grid Content */}
      <main className="dashboard-grid">
        {/* Left Column: Metrics & Injector */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Scenario Control Panel */}
          <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 600, letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Zap size={18} color="var(--primary)" /> Scenario Failure Injector
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Simulate real-time production failures to test autonomous agent resolution loop</p>
            </div>

            {/* Buttons Grid */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {scenarios.map((sc) => {
                const isCurrent = injecting === sc.name;
                return (
                  <div 
                    key={sc.name} 
                    style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      background: 'rgba(15,23,42,0.15)',
                      padding: '0.75rem 1rem', 
                      borderRadius: '8px', 
                      border: '1px solid var(--border-color)',
                      gap: '1rem'
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{sc.label}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{sc.desc}</span>
                    </div>
                    <button
                      disabled={injecting !== null}
                      onClick={() => handleScenarioInject(sc.name)}
                      className="btn btn-outline"
                      style={{ fontSize: '0.75rem', padding: '0.4rem 0.75rem', whiteSpace: 'nowrap' }}
                    >
                      <Play size={12} />
                      {isCurrent ? 'Injecting...' : 'Inject'}
                    </button>
                  </div>
                );
              })}

              {/* Reset Button */}
              <button
                disabled={injecting !== null}
                onClick={() => handleScenarioInject('reset')}
                className="btn btn-danger"
                style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', justifyContent: 'center' }}
              >
                <RotateCcw size={16} />
                Clear Injectors & Reset System Baseline
              </button>
            </div>

            {injectSuccess && (
              <div style={{ 
                fontSize: '0.8rem', 
                color: 'var(--success)', 
                background: 'rgba(16,185,129,0.1)', 
                padding: '0.75rem', 
                borderRadius: '6px', 
                border: '1px solid rgba(16,185,129,0.2)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}>
                <Activity size={14} />
                {injectSuccess}
              </div>
            )}

            {error && (
              <div style={{ 
                fontSize: '0.8rem', 
                color: 'var(--danger)', 
                background: 'rgba(239,68,68,0.1)', 
                padding: '0.75rem', 
                borderRadius: '6px', 
                border: '1px solid rgba(239,68,68,0.2)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}>
                <AlertCircle size={14} />
                {error}
              </div>
            )}
          </div>

          {/* Metrics Panel */}
          <MetricsPanel />
        </div>

        {/* Right Column: Trace & Timeline */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Agent Trace View */}
          <AgentTraceView events={events} activeAgent={activeAgent} />

          {/* Incident Timeline */}
          <IncidentTimeline 
            currentIncidentId={currentIncidentId} 
            onPendingApproval={(incident) => setPendingIncident(incident)} 
          />
        </div>
      </main>

      {/* Floating Approval Modal Gate */}
      {pendingIncident && (
        <ApprovalModal 
          incident={pendingIncident} 
          onClose={() => setPendingIncident(null)} 
          onRefresh={() => {
            // Trigger refetch of metric timelines
            window.dispatchEvent(new Event('refresh_incidents'));
          }}
        />
      )}
    </div>
  );
};

export default App;
