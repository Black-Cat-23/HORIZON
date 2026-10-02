import React from 'react';
import { SplitText } from '../components/SplitText';

interface LockLossProps {
  isActive: boolean;
}

export const LockLoss: React.FC<LockLossProps> = ({ isActive }) => {
  return (
    <section id="loss" className="chapter-section">
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--state-loss)' }}>
            PHASE 07
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">SIGNAL OCCLUSION</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="LOCK LOST. RECOVERY IS ESSENTIAL."
            as="h2"
            className="title-giant text-primary"
            isVisible={isActive}
            baseDelay={80}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem', maxWidth: '960px' }}>
          <p
            className="font-body"
            style={{
              color: 'var(--text-secondary)',
              fontSize: '1.125rem',
              lineHeight: 1.75,
              fontWeight: 300,
              margin: 0,
            }}
          >
            When severe obstacles, clouds, or rapid angular acceleration cause complete optical dropouts, the system must not diverge. State estimation covariance grows while maintaining last-known velocity vector.
          </p>

          <div
            className="beveled-glass-card"
            style={{
              borderColor: 'rgba(232, 111, 127, 0.35)',
              backgroundColor: 'rgba(10, 19, 34, 0.65)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <span className="label-caps" style={{ color: 'var(--state-loss)' }}>
                DROPOUT DIAGNOSTICS
              </span>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.2rem 0.55rem',
                  borderRadius: '9999px',
                  backgroundColor: 'rgba(232, 111, 127, 0.12)',
                  border: '1px solid rgba(232, 111, 127, 0.35)',
                  fontSize: '0.65rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--state-loss)',
                }}
              >
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--state-loss)' }} />
                COAST MODE
              </span>
            </div>

            <div className="font-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>TRACK STATUS:</span>
                <span style={{ color: 'var(--state-loss)', fontWeight: 700 }}>LOCK LOST (COASTING)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>OCCLUSION DURATION:</span>
                <span style={{ color: 'var(--text-primary)' }}>1.20 SECONDS</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>COVARIANCE P:</span>
                <span style={{ color: 'var(--state-disturbance)' }}>EXPANDING BOUNDS</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>FALLBACK ACTION:</span>
                <span style={{ color: 'var(--state-signal)' }}>INITIATE REACQUISITION</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
