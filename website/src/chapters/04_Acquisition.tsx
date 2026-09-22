import React from 'react';
import { SplitText } from '../components/SplitText';

interface AcquisitionProps {
  isActive: boolean;
}

export const Acquisition: React.FC<AcquisitionProps> = ({ isActive }) => {
  return (
    <section id="acquire" className="chapter-section">
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--state-lock)' }}>
            PHASE 04
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">SIGNAL DETECTED</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="SIGNAL FOUND. ACQUIRE."
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
            The moment the optical beacon enters the focal plane, our sub-pixel center-of-gravity pipeline locks onto the centroid, transitioning state from SEARCH to ACQUIRE in under 45 milliseconds.
          </p>

          <div
            style={{
              padding: '1.5rem',
              border: '1px solid var(--border-subtle)',
              backgroundColor: 'rgba(11, 16, 24, 0.65)',
              backdropFilter: 'blur(8px)',
            }}
          >
            <span className="label-caps" style={{ display: 'block', marginBottom: '0.75rem', color: 'var(--state-lock)' }}>
              CENTROID ESTIMATE
            </span>
            <div className="font-mono data-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.8rem' }}>
              <div>PIXEL CENTROID: <span style={{ color: 'var(--text-primary)' }}>[324.8, 238.2] px</span></div>
              <div>CONFIDENCE SCORE: <span style={{ color: 'var(--state-lock)' }}>98.7%</span></div>
              <div>TRANSIT TIME: <span style={{ color: 'var(--text-primary)' }}>0.042 SECONDS</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
