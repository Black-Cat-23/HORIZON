import React from 'react';
import { SplitText } from '../components/SplitText';

interface SearchScanProps {
  isActive: boolean;
}

export const SearchScan: React.FC<SearchScanProps> = ({ isActive }) => {
  return (
    <section id="search" className="chapter-section">
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--state-signal)' }}>
            PHASE 03
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">UNCERTAINTY SWEEP</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="SYSTEMATIC SEARCH & SCAN."
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
            An Archimedean spiral trajectory sweeps the uncertainty domain at bounded angular acceleration, guaranteeing complete overlap coverage while keeping motor slew rates within physical gimbal limits.
          </p>

          <div
            style={{
              padding: '1.5rem',
              border: '1px solid var(--border-subtle)',
              backgroundColor: 'rgba(11, 16, 24, 0.65)',
              backdropFilter: 'blur(8px)',
            }}
          >
            <span className="label-caps" style={{ display: 'block', marginBottom: '0.75rem', color: 'var(--state-signal)' }}>
              SCAN DYNAMICS
            </span>
            <div className="font-mono data-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.8rem' }}>
              <div>SCAN PATTERN: <span style={{ color: 'var(--text-primary)' }}>ARCHIMEDEAN SPIRAL</span></div>
              <div>ANGULAR RATE: <span style={{ color: 'var(--text-primary)' }}>2.4° / SEC</span></div>
              <div>OVERLAP RATIO: <span style={{ color: 'var(--text-primary)' }}>40% FOV MARGIN</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
