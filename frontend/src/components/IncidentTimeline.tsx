import React, { useState, useEffect } from 'react';
import { ShieldAlert, CheckCircle, Clock, XCircle, FileText } from 'lucide-react';
import { api } from '../lib/api';

interface Incident {
  id: string;
  status: string;
  service: string;
  metric: string;
  severity: number;
  risk_tier: string;
  auto_executed: boolean;
  created_at: string;
}

interface IncidentDetail {
  id: string;
  status: string;
  created_at: string;
  anomaly: {
    service: string;
    metric: string;
    observed_value: number;
    baseline_value: number;
    severity: number;
    detected_at: string;
  };
  diagnosis: {
    root_cause: string;
    confidence: number;
    correlated_signals: string[];
  } | null;
  action: {
    description: string;
    command: string;
    risk_tier: string;
    reversible: boolean;
    auto_executed: boolean;
  } | null;
  report: string | null;
}

interface IncidentTimelineProps {
  currentIncidentId: string | null;
  onPendingApproval: (incident: IncidentDetail) => void;
}

// Simple custom Markdown parser
const renderMarkdown = (md: string) => {
  if (!md) return null;
  
  const lines = md.split('\n');
  return lines.map((line, idx) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('# ')) {
      return <h1 key={idx} style={{ fontSize: '1.5rem', fontWeight: 700, margin: '1.5rem 0 0.5rem 0', color: 'var(--primary)' }}>{trimmed.slice(2)}</h1>;
    }
    if (trimmed.startsWith('## ')) {
      return <h2 key={idx} style={{ fontSize: '1.2rem', fontWeight: 600, margin: '1.25rem 0 0.5rem 0', color: 'var(--text-main)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.25rem' }}>{trimmed.slice(3)}</h2>;
    }
    if (trimmed.startsWith('### ')) {
      return <h3 key={idx} style={{ fontSize: '1rem', fontWeight: 600, margin: '1rem 0 0.5rem 0', color: 'var(--text-main)' }}>{trimmed.slice(4)}</h3>;
    }
    if (trimmed.startsWith('- ')) {
      // Replace bold syntax **text** with <strong> elements
      const content = trimmed.slice(2);
      return <li key={idx} style={{ marginLeft: '1.5rem', marginBottom: '0.25rem', color: 'var(--text-main)', fontSize: '0.85rem' }} dangerouslySetInnerHTML={{ __html: parseBold(content) }} />;
    }
    if (trimmed === '') {
      return <div key={idx} style={{ height: '0.5rem' }} />;
    }
    return <p key={idx} style={{ marginBottom: '0.5rem', fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: '1.5' }} dangerouslySetInnerHTML={{ __html: parseBold(trimmed) }} />;
  });
};

const parseBold = (text: string) => {
  return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
};

export const IncidentTimeline: React.FC<IncidentTimelineProps> = ({ currentIncidentId, onPendingApproval }) => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<IncidentDetail | null>(null);

  // Poll list of incidents
  const fetchIncidents = async () => {
    try {
      const data = await api.listIncidents();
      setIncidents(data);
      
      // Auto-select first incident if none selected
      if (data.length > 0 && !selectedId) {
        setSelectedId(data[0].id);
      }
    } catch (err) {
      console.error('Error fetching incidents:', err);
    }
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 4000);
    return () => clearInterval(interval);
  }, []);

  // Sync selectedId with active SSE incident triggers
  useEffect(() => {
    if (currentIncidentId) {
      setSelectedId(currentIncidentId);
    }
  }, [currentIncidentId]);

  // Fetch incident details when selectedId changes
  useEffect(() => {
    const fetchDetail = async () => {
      if (!selectedId) return;
      try {
        const data = await api.getIncidentDetail(selectedId);
        setDetail(data);

        // Check if this incident requires manual approval
        if (data.status === 'awaiting_approval' && data.action) {
          onPendingApproval(data);
        }
      } catch (err) {
        console.error('Error fetching incident detail:', err);
      }
    };

    fetchDetail();
  }, [selectedId, onPendingApproval]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'resolved':
        return <CheckCircle size={16} color="var(--success)" />;
      case 'awaiting_approval':
        return <Clock size={16} color="var(--warning)" />;
      case 'rejected':
        return <XCircle size={16} color="var(--danger)" />;
      default:
        return <ShieldAlert size={16} color="var(--primary)" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    if (s === 'resolved') return <span className="badge badge-success">Resolved</span>;
    if (s === 'awaiting_approval') return <span className="badge badge-warning">Awaiting Approval</span>;
    if (s === 'rejected') return <span className="badge badge-danger">Rejected</span>;
    return <span className="badge badge-info">{status}</span>;
  };

  return (
    <div className="glass-panel" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          Incidents Inbox & Postmortems
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Review pipeline alerts, diagnoses, and reports</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: '1.5rem', minHeight: '400px' }}>
        {/* Incidents List (Left) */}
        <div style={{ borderRight: '1px solid var(--border-color)', paddingRight: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '480px', overflowY: 'auto' }}>
          {incidents.length === 0 ? (
            <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.8rem', padding: '1rem 0' }}>
              No incidents recorded.
            </div>
          ) : (
            incidents.map((inc) => {
              const isSelected = selectedId === inc.id;
              const dateStr = new Date(inc.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
              
              return (
                <div
                  key={inc.id}
                  onClick={() => setSelectedId(inc.id)}
                  style={{
                    padding: '0.75rem',
                    borderRadius: '8px',
                    background: isSelected ? 'rgba(30, 41, 59, 0.4)' : 'rgba(15, 23, 42, 0.15)',
                    border: `1px solid ${isSelected ? 'var(--primary)' : 'rgba(255,255,255,0.03)'}`,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.35rem'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      #{inc.id.slice(0, 8)}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{dateStr}</span>
                  </div>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, display: 'flex', justifyItems: 'center', gap: '0.35rem' }}>
                    {getStatusIcon(inc.status)}
                    <span>{inc.service}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.25rem' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--danger)', fontWeight: 600 }}>{inc.metric}</span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Sev: {inc.severity.toFixed(2)}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Detailed Postmortem View (Right) */}
        <div style={{ maxHeight: '480px', overflowY: 'auto', paddingRight: '0.5rem' }}>
          {detail ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {/* Header Details */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', flexWrap: 'wrap', gap: '1rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '1rem' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Incident Details</h3>
                    {getStatusBadge(detail.status)}
                  </div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>ID: {detail.id}</p>
                </div>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Detected: {new Date(detail.anomaly.detected_at).toLocaleString()}
                </span>
              </div>

              {/* Diagnosis Panel */}
              {detail.diagnosis ? (
                <div style={{ background: 'rgba(30, 41, 59, 0.2)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1rem' }}>
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--primary)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Sleuth Root Cause Hypothesis
                  </h4>
                  <p style={{ fontSize: '0.9rem', lineHeight: '1.4', marginBottom: '0.75rem' }}>{detail.diagnosis.root_cause}</p>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span>Confidence Score: <strong style={{ color: 'var(--primary)' }}>{(detail.diagnosis.confidence * 100).toFixed(0)}%</strong></span>
                    <span>Signals Correlated: {detail.diagnosis.correlated_signals.length}</span>
                  </div>
                </div>
              ) : (
                <div style={{ fontStyle: 'italic', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Diagnosis in progress...</div>
              )}

              {/* Remediation Action Panel */}
              {detail.action && (
                <div style={{ 
                  background: 'rgba(15, 23, 42, 0.2)', 
                  border: '1px solid var(--border-color)', 
                  borderRadius: '8px', 
                  padding: '1rem',
                  borderLeft: `4px solid ${
                    detail.action.risk_tier === 'high' ? 'var(--danger)' : 
                    detail.action.risk_tier === 'medium' ? 'var(--warning)' : 'var(--success)'
                  }`
                }}>
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)', marginBottom: '0.5rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    Medic Remediation Action
                  </h4>
                  <p style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>{detail.action.description}</p>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', background: 'rgba(0,0,0,0.4)', padding: '0.15rem 0.4rem', borderRadius: '4px', color: '#67e8f9' }}>
                      {detail.action.command}
                    </span>
                    <span>• Risk: <strong style={{ textTransform: 'capitalize' }}>{detail.action.risk_tier}</strong></span>
                    <span>• Auto-Executed: <strong>{detail.action.auto_executed ? 'YES' : 'NO'}</strong></span>
                  </div>
                </div>
              )}

              {/* Markdown Postmortem Report */}
              {detail.report ? (
                <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    <FileText size={14} />
                    <span>Scribe Incident Postmortem</span>
                  </div>
                  <div style={{
                    background: 'rgba(5, 7, 12, 0.4)',
                    padding: '1.25rem',
                    borderRadius: '8px',
                    border: '1px solid rgba(255, 255, 255, 0.02)',
                  }}>
                    {renderMarkdown(detail.report)}
                  </div>
                </div>
              ) : (
                <div style={{ fontStyle: 'italic', color: 'var(--text-muted)', fontSize: '0.85rem', paddingTop: '1rem' }}>Generating postmortem report...</div>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              Select an incident to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
