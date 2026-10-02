import React from 'react';
import { SplitText } from '../components/SplitText';

interface UnknownSignalProps {
  isActive: boolean;
}

export const UnknownSignal: React.FC<UnknownSignalProps> = ({ isActive }) => {
  const failureModes = [
    {
      id: 'FM-01',
      title: 'Clutter & Sun Glint',
      body: 'Cloud borders and solar reflections cause 24–26% false-lock rates in classical intensity-threshold detectors.',
      color: 'var(--state-disturbance)',
    },
    {
      id: 'FM-02',
      title: 'High-G Maneuver Dropout',
      body: 'Single-model Kalman filters diverge when the target executes sudden angular break-turns exceeding 2G.',
      color: 'var(--state-disturbance)',
    },
    {
      id: 'FM-03',
      title: 'Transport Latency',
      body: 'Camera exposure and frame-transfer lag of 40–80 ms introduces phase loss into the control loop, causing hunting oscillations.',
      color: 'var(--state-disturbance)',
    },
    {
      id: 'FM-04',
      title: 'Validation Bottleneck',
      body: 'Physical gimbal hardware testing is expensive and non-reproducible. Algorithm comparison is guesswork without a controlled testbench.',
      color: 'var(--text-muted)',
    },
  ];

  return (
    <section id="unknown" className="chapter-section">
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--text-ice)' }}>
            CHAPTER 01
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">THE ENGINEERING BOTTLENECK</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="THE SIGNAL IS THERE. FOUR THINGS CAN KILL IT."
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
              fontSize: '1.1rem',
              lineHeight: 1.75,
              fontWeight: 300,
            }}
          >
            Mobile Free Space Optical Communications use narrow laser beams (≤1.0 mrad divergence). A pointing deviation of just 0.05° causes complete link failure. The beacon is there — but four distinct failure modes prevent reliable lock under real operating conditions.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {failureModes.map((fm) => (
              <div
                key={fm.id}
                className="beveled-glass-card"
                style={{
                  display: 'flex',
                  gap: '1rem',
                  padding: '0.9rem 1.15rem',
                  backgroundColor: 'rgba(8, 16, 28, 0.55)',
                  borderColor: fm.color === 'var(--state-disturbance)' ? 'rgba(232,161,92,0.25)' : 'var(--border-subtle)',
                }}
              >
                <span
                  className="font-mono"
                  style={{
                    fontSize: '0.6rem',
                    color: fm.color,
                    fontWeight: 800,
                    letterSpacing: '0.05em',
                    flexShrink: 0,
                    paddingTop: '0.15rem',
                  }}
                >
                  {fm.id}
                </span>
                <div>
                  <div
                    className="font-editorial"
                    style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.25rem' }}
                  >
                    {fm.title}
                  </div>
                  <p
                    className="font-body"
                    style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0, fontWeight: 300 }}
                  >
                    {fm.body}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
