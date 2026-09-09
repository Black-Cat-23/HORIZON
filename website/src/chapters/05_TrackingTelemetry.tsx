import React from 'react';
import { SplitText } from '../components/SplitText';

interface TrackingTelemetryProps {
  isActive: boolean;
}

export const TrackingTelemetry: React.FC<TrackingTelemetryProps> = ({ isActive }) => {
  return (
    <section id="track" className="chapter-section">
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--state-lock)' }}>
            CHAPTER 05
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">CLOSED-LOOP LOCK</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="KEEP IT IN VIEW. FEEDFORWARD LOCK."
            as="h2"
            className="title-hero"
            isVisible={isActive}
            baseDelay={80}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem', maxWidth: '980px' }}>
          <p
            className="font-body"
            style={{
              color: 'var(--text-secondary)',
              fontSize: '1.15rem',
              lineHeight: 1.75,
              fontWeight: 300,
            }}
          >
            An Interactive Multiple Model Extended Kalman Filter (IMM-EKF) dynamically predicts non-linear beacon trajectory states, generating proactive feedforward velocity commands to hold optical alignment.
          </p>

          <div className="beveled-glass-card" style={{ borderColor: 'var(--border-active)' }}>
            <span className="label-caps" style={{ display: 'block', marginBottom: '0.85rem', color: 'var(--state-lock)' }}>
              LIVE TRACKING HUD
            </span>
            <div className="font-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>MODE:</span>
                <span style={{ color: 'var(--state-lock)', fontWeight: 700 }}>CLOSED-LOOP TRACK</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>AZ / EL ERROR:</span>
                <span style={{ color: 'var(--text-primary)' }}>+0.04° / -0.02°</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>RMSE CENTROID:</span>
                <span style={{ color: 'var(--state-lock)' }}>1.24 PIXELS</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>PIPELINE LATENCY:</span>
                <span style={{ color: 'var(--text-primary)' }}>2.8 ms (350+ FPS)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
