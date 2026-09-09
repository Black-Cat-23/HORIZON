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

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '2rem', maxWidth: '960px' }}>
          <p
            className="font-body"
            style={{
              color: 'var(--text-secondary)',
              fontSize: '1.125rem',
              lineHeight: 1.7,
            }}
          >
            When severe obstacles, clouds, or rapid angular acceleration cause complete optical dropouts, the system must not diverge. State estimation covariance grows while maintaining last-known velocity vector.
          </p>

          <div
            style={{
              padding: '1.5rem',
              border: '1px solid rgba(232, 111, 127, 0.4)',
              backgroundColor: 'rgba(11, 16, 24, 0.75)',
              backdropFilter: 'blur(8px)',
            }}
          >
            <span className="label-caps" style={{ display: 'block', marginBottom: '0.75rem', color: 'var(--state-loss)' }}>
              DROPOUT DIAGNOSTICS
            </span>
            <div className="font-mono data-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.8rem' }}>
              <div>TRACK STATUS: <span style={{ color: 'var(--state-loss)', fontWeight: 700 }}>LOCK LOST (COASTING)</span></div>
              <div>OCCLUSION DURATION: <span style={{ color: 'var(--text-primary)' }}>1.20 SECONDS</span></div>
              <div>KALMAN COVARIANCE P: <span style={{ color: 'var(--state-disturbance)' }}>EXPANDING (UNCERTAINTY GROWING)</span></div>
              <div>FALLBACK ACTION: <span style={{ color: 'var(--state-loss)' }}>INITIATE REACQUISITION</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
