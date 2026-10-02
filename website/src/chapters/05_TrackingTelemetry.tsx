import React from 'react';
import { SplitText } from '../components/SplitText';
import { AnimatedCounter } from '../components/AnimatedCounter';

interface TrackingTelemetryProps {
  isActive: boolean;
}

export const TrackingTelemetry: React.FC<TrackingTelemetryProps> = ({ isActive }) => {
  return (
    <section id="track" className="chapter-section">
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--state-lock)' }}>
            CHAPTER 05
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">CLOSED-LOOP LOCK</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="KEEP IT IN VIEW. CANCEL THE DISTURBANCE."
            as="h2"
            className="title-hero"
            isVisible={isActive}
            baseDelay={80}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem', maxWidth: '980px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <p
              className="font-body"
              style={{
                color: 'var(--text-secondary)',
                fontSize: '1.1rem',
                lineHeight: 1.75,
                fontWeight: 300,
                margin: 0,
              }}
            >
              A 6-state IMM-EKF fuses three kinematic sub-models (CV, CA, High-G Manoeuvre) via Bayesian Markov mixing. When the target breaks into a 2G turn, the Manoeuvre model probability spikes and the innovation gate expands dynamically — no dropout.
            </p>
            <p
              className="font-body"
              style={{
                color: 'var(--text-secondary)',
                fontSize: '1.1rem',
                lineHeight: 1.75,
                fontWeight: 300,
                margin: 0,
              }}
            >
              An ADRC controller with Non-Linear ESO (Han's <span className="font-mono" style={{ fontSize: '0.9em' }}>fal()</span>) continuously estimates the total lumped disturbance — platform jitter, wind shear, friction — and cancels it before the motor command. A Smith Predictor eliminates 40–80 ms sensor transport lag without gain sacrifice.
            </p>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Live telemetry HUD */}
            <div className="beveled-glass-card" style={{ borderColor: 'var(--border-active)' }}>
              <span className="label-caps" style={{ display: 'block', marginBottom: '0.85rem', color: 'var(--state-lock)' }}>
                VERIFIED CLOSED-LOOP TELEMETRY
              </span>
              <div className="font-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.78rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>FSM STATE:</span>
                  <span style={{ color: 'var(--state-lock)', fontWeight: 700 }}>TRACK</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>MEAN TRACK ERROR:</span>
                  <span style={{ color: 'var(--state-lock)' }}>
                    <AnimatedCounter value={0.13} decimals={2} suffix=" px / 0.339°" isActive={isActive} />
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>PIPELINE LATENCY:</span>
                  <span style={{ color: 'var(--text-primary)' }}>
                    <AnimatedCounter value={440.3} decimals={1} suffix=" µs" isActive={isActive} />
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>FALSE-LOCK RATE:</span>
                  <span style={{ color: 'var(--state-lock)', fontWeight: 700 }}>0.0%</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>RE-ACQUIRE (2G TURN):</span>
                  <span style={{ color: 'var(--text-primary)' }}>&lt;180 ms</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>ISRO VIDEO RETENTION:</span>
                  <span style={{ color: 'var(--state-lock)' }}>
                    <AnimatedCounter value={99.8} decimals={1} suffix="%" isActive={isActive} />
                  </span>
                </div>
              </div>
            </div>

            {/* Control chain pill */}
            <div
              className="beveled-glass-card"
              style={{
                padding: '1rem 1.25rem',
                borderColor: 'var(--border-subtle)',
                backgroundColor: 'rgba(8, 16, 28, 0.55)',
              }}
            >
              <span className="label-caps" style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-muted)', fontSize: '0.62rem' }}>
                CONTROL CHAIN ARCHITECTURE
              </span>
              <div className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
                <div>IMM-EKF <span style={{ color: 'var(--border-strong)' }}>→</span> PAT FSM <span style={{ color: 'var(--border-strong)' }}>→</span> NLESO ADRC</div>
                <div>Smith Predictor <span style={{ color: 'var(--border-strong)' }}>→</span> S-Curve Limiter <span style={{ color: 'var(--border-strong)' }}>→</span> Gimbal</div>
                <div style={{ marginTop: '0.35rem', color: 'var(--text-muted)', fontSize: '0.68rem' }}>ωc = 2.8 rad/s · ωo = 12 rad/s · ±5.0°/s clamp</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
