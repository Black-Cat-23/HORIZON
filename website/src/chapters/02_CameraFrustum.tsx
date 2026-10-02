import React from 'react';
import { SplitText } from '../components/SplitText';

interface CameraFrustumProps {
  isActive: boolean;
}

export const CameraFrustum: React.FC<CameraFrustumProps> = ({ isActive }) => {
  return (
    <section id="camera" className="chapter-section">
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--state-signal)' }}>
            PHASE 02
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">OPTICAL RECEIVER</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="A NARROW WINDOW ON THE WORLD."
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
            The focal plane array captures a tight 4°×3° field at 640×480 resolution (≥30 Hz). High optical gain demands severe spatial pointing accuracy to capture the spot without losing aperture throughput.
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
                SENSOR SPECIFICATION
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
                FPA SENSOR
              </span>
            </div>

            <div className="font-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', fontSize: '0.8rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>FIELD OF VIEW:</span>
                <span style={{ color: 'var(--text-primary)' }}>4.0° (H) × 3.0° (V)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>RESOLUTION:</span>
                <span style={{ color: 'var(--text-primary)' }}>640 × 480 MONOCHROME</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>FRAME RATE:</span>
                <span style={{ color: 'var(--text-primary)' }}>≥30 FPS (0.033s STEP)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
