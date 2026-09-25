import React from 'react';
import { SplitText } from '../components/SplitText';

interface DisturbanceLabProps {
  isActive: boolean;
}

export const DisturbanceLab: React.FC<DisturbanceLabProps> = ({ isActive }) => {
  return (
    <section id="disturbance" className="chapter-section">
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--state-disturbance)' }}>
            PHASE 06
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">DISTURBANCE INJECTION</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="SURVIVE SEVERE DISTURBANCE."
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
            Real FSOC operating environments experience atmospheric scintillation, optical blur, and high-frequency vehicular platform vibration. HORIZON injects deterministic disturbance profiles to test filter robustness.
          </p>

          <div
            style={{
              padding: '1.5rem',
              border: '1px solid rgba(232, 161, 92, 0.4)',
              backgroundColor: 'rgba(11, 16, 24, 0.75)',
              backdropFilter: 'blur(8px)',
            }}
          >
            <span className="label-caps" style={{ display: 'block', marginBottom: '0.75rem', color: 'var(--state-disturbance)' }}>
              DISTURBANCE PROFILE
            </span>
            <div className="font-mono data-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.8rem' }}>
              <div>STATE: <span style={{ color: 'var(--state-disturbance)', fontWeight: 700 }}>TRACK (DEGRADED)</span></div>
              <div>GAUSSIAN JITTER: <span style={{ color: 'var(--text-primary)' }}>σ = 3.5 PIXELS (20 Hz)</span></div>
              <div>SCINTILLATION: <span style={{ color: 'var(--text-primary)' }}>0.40 CONTRAST ATTENUATION</span></div>
              <div>FILTER REJECTION: <span style={{ color: 'var(--state-lock)' }}>ACTIVE (IMM ADAPTATION)</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
