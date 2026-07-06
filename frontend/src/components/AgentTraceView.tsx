import React, { useEffect, useRef } from 'react';
import { Terminal, Shield, Search, HeartPulse, FileText } from 'lucide-react';
import { AgentEvent } from '../hooks/useAgentStream';

interface AgentTraceViewProps {
  events: AgentEvent[];
  activeAgent: string | null;
}

export const AgentTraceView: React.FC<AgentTraceViewProps> = ({ events, activeAgent }) => {
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll terminal to bottom
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  const agents = [
    { name: 'sentry', label: 'Sentry (Monitor)', icon: <Shield size={18} /> },
    { name: 'sleuth', label: 'Sleuth (Diagnose)', icon: <Search size={18} /> },
    { name: 'medic', label: 'Medic (Remediate)', icon: <HeartPulse size={18} /> },
    { name: 'scribe', label: 'Scribe (Report)', icon: <FileText size={18} /> },
  ];

  return (
    <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          Live Agent Execution Trace
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Cooperating agent reasoning chain and decision logs</p>
      </div>

      {/* Agent Progress Chain */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        background: 'rgba(15, 23, 42, 0.3)', 
        padding: '1rem', 
        borderRadius: '8px',
        border: '1px solid var(--border-color)',
        overflowX: 'auto',
        gap: '1rem'
      }}>
        {agents.map((agent, idx) => {
          const isActive = activeAgent === agent.name;
          const isCompleted = events.some(e => e.event_type === agent.name);
          
          let color = 'var(--text-muted)';
          let border = 'rgba(255, 255, 255, 0.05)';
          let bg = 'rgba(15, 23, 42, 0.4)';
          let glow = 'none';

          if (isActive) {
            color = 'var(--primary)';
            border = 'var(--primary)';
            bg = 'rgba(6, 182, 212, 0.1)';
            glow = '0 0 15px rgba(6, 182, 212, 0.2)';
          } else if (isCompleted) {
            color = 'var(--success)';
            border = 'var(--success)';
            bg = 'rgba(16, 185, 129, 0.05)';
          }

          return (
            <React.Fragment key={agent.name}>
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '0.5rem',
                minWidth: '100px',
              }}>
                <div style={{
                  width: '42px',
                  height: '42px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: bg,
                  border: `1px solid ${border}`,
                  color: color,
                  boxShadow: glow,
                  transition: 'all 0.3s ease',
                  position: 'relative'
                }} className={isActive ? 'active-pulse' : ''}>
                  {agent.icon}
                  {isActive && (
                    <span style={{
                      position: 'absolute',
                      bottom: '-2px',
                      right: '-2px',
                      width: '10px',
                      height: '10px',
                      borderRadius: '50%',
                      background: 'var(--primary)',
                      border: '2px solid var(--bg-color)',
                    }}></span>
                  )}
                </div>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: color }}>{agent.label}</span>
              </div>
              {idx < agents.length - 1 && (
                <div style={{
                  flexGrow: 1,
                  height: '2px',
                  background: isCompleted ? 'var(--success)' : 'var(--border-color)',
                  opacity: 0.5,
                  minWidth: '20px'
                }}></div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Terminal logs */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          <Terminal size={14} />
          <span>Agent Streams Console</span>
        </div>
        <div className="console-view" style={{ height: '220px' }}>
          {events.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', textAlign: 'center', padding: '2rem 0' }}>
              System idle. Inject a failure scenario to start execution loop...
            </div>
          ) : (
            events.map((evt, idx) => {
              let headerColor = '#38bdf8';
              if (evt.event_type === 'sentry') headerColor = '#06b6d4';
              if (evt.event_type === 'sleuth') headerColor = '#818cf8';
              if (evt.event_type === 'medic') headerColor = '#a78bfa';
              if (evt.event_type === 'scribe') headerColor = '#f472b6';
              if (evt.event_type === 'complete') headerColor = '#34d399';

              return (
                <div key={idx} style={{ marginBottom: '1rem', borderBottom: '1px solid rgba(255, 255, 255, 0.03)', paddingBottom: '0.75rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-muted)', fontSize: '0.7rem', marginBottom: '0.25rem' }}>
                    <span style={{ color: headerColor, fontWeight: 'bold', textTransform: 'uppercase' }}>
                      [{evt.event_type.toUpperCase()}]
                    </span>
                    <span>{evt.timestamp}</span>
                  </div>
                  <pre style={{ 
                    whiteSpace: 'pre-wrap', 
                    wordBreak: 'break-all', 
                    fontFamily: 'var(--font-mono)',
                    color: evt.event_type === 'scribe' ? '#e2e8f0' : '#38bdf8'
                  }}>
                    {evt.payload}
                  </pre>
                </div>
              );
            })
          )}
          <div ref={terminalEndRef} />
        </div>
      </div>
    </div>
  );
};
