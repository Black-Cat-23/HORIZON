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
            Instead of resetting to a blind global search, the mode manager executes a localized expanding spiral centered on the propagated covariance ellipsoid, re-locking the link within 180 milliseconds.
          </p>

          <div
            className="beveled-glass-card"
            style={{
              borderColor: 'var(--border-active)',
              backgroundColor: 'rgba(10, 19, 34, 0.65)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <span className="label-caps" style={{ color: 'var(--state-lock)' }}>
                RECOVERY METRICS
              </span>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.2rem 0.55rem',
                  borderRadius: '9999px',
                  backgroundColor: 'rgba(169, 216, 232, 0.12)',
                  border: '1px solid rgba(169, 216, 232, 0.35)',
                  fontSize: '0.65rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--state-lock)',
                }}
              >
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--state-lock)' }} />
                LOCK ACQUIRED
              </span>
            </div>

            <div className="font-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>REACQUISITION TIME:</span>
                <span style={{ color: 'var(--state-lock)', fontWeight: 700 }}>0.184 SECONDS</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>SEARCH RADIUS:</span>
                <span style={{ color: 'var(--text-primary)' }}>1.8° EXPANDING CONE</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>POINTING ERROR:</span>
                <span style={{ color: 'var(--state-lock)' }}>0.038° (≤ 0.1° SPEC)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>POWER RETENTION:</span>
                <span style={{ color: 'var(--text-primary)' }}>99.2%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
