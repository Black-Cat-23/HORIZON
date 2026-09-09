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

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '2rem', maxWidth: '960px' }}>
          <p
            className="font-body"
            style={{
              color: 'var(--text-secondary)',
              fontSize: '1.125rem',
              lineHeight: 1.7,
            }}
          >
            The focal plane array captures a tight 4°×3° field at 640×480 resolution (≥30 Hz). High optical gain demands severe spatial pointing accuracy to capture the spot without losing aperture throughput.
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
              SENSOR SPECIFICATION
            </span>
            <div className="font-mono data-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.8rem' }}>
              <div>FIELD OF VIEW: <span style={{ color: 'var(--text-primary)' }}>4.0° (H) × 3.0° (V)</span></div>
              <div>RESOLUTION: <span style={{ color: 'var(--text-primary)' }}>640 × 480 MONOCHROME</span></div>
              <div>FRAME RATE: <span style={{ color: 'var(--text-primary)' }}>≥30 FPS (0.033s STEP)</span></div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
