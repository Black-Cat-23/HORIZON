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
            An Archimedean spiral trajectory sweeps the uncertainty domain at bounded angular acceleration, guaranteeing complete overlap coverage while keeping motor slew rates within physical gimbal limits.
          </p>

          <div
            className="beveled-glass-card"
            style={{
              borderColor: 'var(--border-subtle)',
              backgroundColor: 'rgba(10, 19, 34, 0.65)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <span className="label-caps" style={{ color: 'var(--state-signal)' }}>
                SCAN DYNAMICS
              </span>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.2rem 0.55rem',
                  borderRadius: '9999px',
                  backgroundColor: 'rgba(169, 216, 232, 0.08)',
                  border: '1px solid rgba(169, 216, 232, 0.25)',
                  fontSize: '0.65rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--state-signal)',
                }}
              >
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--state-signal)' }} />
                SPIRAL PATTERN
              </span>
            </div>

            <div className="font-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>SCAN PATTERN:</span>
                <span style={{ color: 'var(--text-primary)' }}>ARCHIMEDEAN SPIRAL</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>ANGULAR RATE:</span>
                <span style={{ color: 'var(--text-primary)' }}>2.4° / SEC</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>OVERLAP RATIO:</span>
                <span style={{ color: 'var(--text-primary)' }}>40% FOV MARGIN</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
