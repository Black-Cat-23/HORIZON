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
            The moment the optical beacon enters the focal plane, our sub-pixel center-of-gravity pipeline locks onto the centroid, transitioning state from SEARCH to ACQUIRE in under 45 milliseconds.
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
                CENTROID ESTIMATE
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
                SUB-PIXEL COG
              </span>
            </div>

            <div className="font-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>PIXEL CENTROID:</span>
                <span style={{ color: 'var(--text-primary)' }}>[324.8, 238.2] px</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>CONFIDENCE SCORE:</span>
                <span style={{ color: 'var(--state-lock)', fontWeight: 700 }}>98.7%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>TRANSIT TIME:</span>
                <span style={{ color: 'var(--text-primary)' }}>0.042 SECONDS</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
