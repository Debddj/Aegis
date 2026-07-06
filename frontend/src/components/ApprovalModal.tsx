import React, { useState } from 'react';
import { AlertOctagon, Check, X } from 'lucide-react';
import { api } from '../lib/api';

interface IncidentDetail {
  id: string;
  status: string;
  anomaly: {
    service: string;
    metric: string;
    observed_value: number;
    baseline_value: number;
  };
  action: {
    description: string;
    command: string;
    risk_tier: string;
    reversible: boolean;
  } | null;
}

interface ApprovalModalProps {
  incident: IncidentDetail | null;
  onClose: () => void;
  onRefresh: () => void;
}

export const ApprovalModal: React.FC<ApprovalModalProps> = ({ incident, onClose, onRefresh }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!incident || !incident.action) return null;

  const handleDecision = async (approved: boolean) => {
    setLoading(true);
    setError(null);
    try {
      await api.approveAction(incident.id, approved);
      onRefresh();
      onClose();
    } catch (err: any) {
      console.error('Error submitting approval decision:', err);
      setError(err.response?.data?.detail || 'Failed to submit decision.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100vw',
      height: '100vh',
      background: 'rgba(5, 7, 12, 0.85)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '1rem',
    }}>
      <div 
        className="glass-panel" 
        style={{
          width: '100%',
          maxWidth: '500px',
          padding: '2rem',
          border: '1px solid rgba(245, 158, 11, 0.4)',
          boxShadow: '0 0 40px rgba(245, 158, 11, 0.15)',
          display: 'flex',
          flexDirection: 'column',
          gap: '1.5rem',
          transform: 'scale(1)',
          animation: 'fade-in 0.2s cubic-bezier(0.16, 1, 0.3, 1)'
        }}
      >
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'start' }}>
          <div style={{
            background: 'rgba(245, 158, 11, 0.1)',
            padding: '0.75rem',
            borderRadius: '50%',
            color: 'var(--warning)',
            border: '1px solid rgba(245, 158, 11, 0.2)',
          }}>
            <AlertOctagon size={28} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 600, letterSpacing: '-0.02em', marginBottom: '0.25rem' }}>
              Human Approval Gate
            </h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              An agent-proposed action is classified as <strong style={{ color: 'var(--warning)', textTransform: 'capitalize' }}>{incident.action.risk_tier} Risk</strong> and requires authorization.
            </p>
          </div>
        </div>

        <div style={{ background: 'rgba(15, 23, 42, 0.3)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Target Incident</span>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, marginTop: '0.15rem' }}>
              {incident.anomaly.service} • {incident.anomaly.metric} ({incident.anomaly.observed_value} vs {incident.anomaly.baseline_value} Baseline)
            </div>
          </div>
          <div style={{ height: '1px', background: 'var(--border-color)' }}></div>
          <div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Proposed Intervention</span>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, marginTop: '0.15rem', color: 'var(--warning)' }}>
              {incident.action.description}
            </div>
            <pre style={{ 
              fontFamily: 'var(--font-mono)', 
              background: 'rgba(0,0,0,0.4)', 
              padding: '0.4rem 0.6rem', 
              borderRadius: '4px', 
              fontSize: '0.75rem', 
              marginTop: '0.5rem',
              color: '#67e8f9',
              border: '1px solid rgba(255,255,255,0.03)'
            }}>
              {incident.action.command}
            </pre>
          </div>
        </div>

        {error && (
          <div style={{ color: 'var(--danger)', fontSize: '0.8rem', background: 'rgba(239, 68, 68, 0.1)', padding: '0.5rem', borderRadius: '4px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          <button 
            disabled={loading} 
            onClick={() => handleDecision(false)}
            className="btn btn-outline"
            style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}
          >
            <X size={16} />
            {loading ? 'Processing...' : 'Reject Action'}
          </button>
          <button 
            disabled={loading} 
            onClick={() => handleDecision(true)}
            className="btn btn-primary"
            style={{ background: 'linear-gradient(135deg, var(--warning), #d97706)' }}
          >
            <Check size={16} />
            {loading ? 'Processing...' : 'Approve & Execute'}
          </button>
        </div>
      </div>
    </div>
  );
};
