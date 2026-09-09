import React from 'react';
import { SplitText } from '../components/SplitText';

interface ReacquisitionProps {
  isActive: boolean;
}

export const Reacquisition: React.FC<ReacquisitionProps> = ({ isActive }) => {
  return (
    <section id="reacquire" className="chapter-section">
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--state-lock)' }}>
            PHASE 08
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">ADAPTIVE RECOVERY</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="RAPID REACQUISITION. LOCK RE-ESTABLISHED."
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
            Instead of resetting to a blind global search, the mode manager executes a localized expanding spiral centered on the propagated covariance ellipsoid, re-locking the link within 180 milliseconds.
          </p>

          <div
            style={{
              padding: '1.5rem',
              border: '1px solid var(--border-active)',
              backgroundColor: 'rgba(11, 16, 24, 0.75)',
              backdropFilter: 'blur(8px)',
            }}
          >
            <span className="label-caps" style={{ display: 'block', marginBottom: '0.75rem', color: 'var(--state-lock)' }}>
              RECOVERY METRICS
            </span>
            <div className="font-mono data-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.8rem' }}>
              <div>REACQUISITION TIME: <span style={{ color: 'var(--state-lock)', fontWeight: 700 }}>0.184 SECONDS</span></div>
              <div>SEARCH RADIUS: <span style={{ color: 'var(--text-primary)' }}>1.8° EXPANDING CONE</span></div>
              <div>FINAL POINTING ERROR: <span style={{ color: 'var(--state-lock)' }}>0.038° (≤ 0.1° THRESHOLD)</span></div>
              <div>OPTICAL POWER RETENTION: <span style={{ color: 'var(--text-primary)' }}>99.2%</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
