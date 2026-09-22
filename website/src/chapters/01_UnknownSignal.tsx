import React from 'react';
import { SplitText } from '../components/SplitText';

interface UnknownSignalProps {
  isActive: boolean;
}

export const UnknownSignal: React.FC<UnknownSignalProps> = ({ isActive }) => {
  return (
    <section id="unknown" className="chapter-section">
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--text-ice)' }}>
            CHAPTER 01
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">SPATIAL UNCERTAINTY</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="THE SIGNAL IS THERE. WE DON'T KNOW WHERE."
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
            In mobile optical communications, platform orientation disturbances and broad initial GPS coordinate errors place the beacon well outside the narrow optical receiver cone.
          </p>

          <div className="beveled-glass-card">
            <span className="label-caps" style={{ display: 'block', marginBottom: '0.85rem', color: 'var(--state-disturbance)' }}>
              UNCERTAINTY DOMAIN
            </span>
            <div className="font-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>AZ / EL UNCERTAINTY:</span>
                <span style={{ color: 'var(--text-primary)' }}>±18.0° / ±12.0°</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>OPTICAL DISTANCE:</span>
                <span style={{ color: 'var(--text-primary)' }}>60.0 METERS</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>ACQUISITION STATUS:</span>
                <span style={{ color: 'var(--state-disturbance)' }}>UNRESOLVED</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
