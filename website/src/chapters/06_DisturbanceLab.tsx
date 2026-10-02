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

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem', maxWidth: '980px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
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
              Real FSOC platforms undergo severe platform vibration, atmospheric scintillation, and multi-stage sensor noise. HORIZON's disturbance engine injects four independent degradation stages — platform jitter (±20 px/frame SIH limit), atmospheric contrast/brightness shifts, and sensor noise (Salt &amp; Pepper, Gaussian, Poisson) — hardening perception and IMM-EKF estimation against adversarial real-world conditions.
            </p>
          </div>

          <div
            className="beveled-glass-card"
            style={{
              borderColor: 'rgba(232, 161, 92, 0.35)',
              backgroundColor: 'rgba(10, 19, 34, 0.65)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <span className="label-caps" style={{ color: 'var(--state-disturbance)' }}>
                ACTIVE DISTURBANCE PROFILE
              </span>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.4rem',
                  padding: '0.2rem 0.55rem',
                  borderRadius: '9999px',
                  backgroundColor: 'rgba(232, 161, 92, 0.12)',
                  border: '1px solid rgba(232, 161, 92, 0.35)',
                  fontSize: '0.65rem',
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--state-disturbance)',
                }}
              >
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--state-disturbance)' }} />
                STRESS PROFILE
              </span>
            </div>

            <div className="font-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem', fontSize: '0.78rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>FSM STATE:</span>
                <span style={{ color: 'var(--state-disturbance)', fontWeight: 700 }}>TRACK (DEGRADED)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>PLATFORM JITTER:</span>
                <span style={{ color: 'var(--text-primary)' }}>±20 px/frame MAX</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>ATMOSPHERIC:</span>
                <span style={{ color: 'var(--text-primary)' }}>HAZY (c=0.70, b=-0.05)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>SENSOR NOISE:</span>
                <span style={{ color: 'var(--text-primary)' }}>S&amp;P + GAUSSIAN + POISSON</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>ADRC REJECTION:</span>
                <span style={{ color: 'var(--state-lock)' }}>ACTIVE (ESO CANCEL)</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>IMM ADAPTATION:</span>
                <span style={{ color: 'var(--state-lock)' }}>MANOEUVRE MODEL ELEVATED</span>
              </div>
            </div>
          </div>
        </div>

        {/* Atmospheric preset table */}
        <div
          className="beveled-glass-card"
          style={{
            marginTop: '2rem',
            maxWidth: '820px',
            borderColor: 'var(--border-subtle)',
            backgroundColor: 'rgba(8, 16, 28, 0.55)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.85rem' }}>
            <span className="label-caps" style={{ color: 'var(--text-muted)' }}>
              5 ATMOSPHERIC CONDITIONS TESTED (GROUND-TRUTH BENCHMARK)
            </span>
            <span className="label-caps" style={{ color: 'var(--state-signal)', fontSize: '0.62rem' }}>
              ISRO PS26169 RIG
            </span>
          </div>

          <div className="font-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.76rem' }}>
            {[
              ['CLEAR', '1.00', '0.00', 'Full optical transparency'],
              ['HAZY', '0.70', '-0.05', 'Light particulate scattering'],
              ['FOGGY', '0.40', '-0.10', 'Dense water droplet attenuation'],
              ['NIGHT', '0.50', '-0.35', 'Low ambient luminance'],
              ['OVERCAST', '0.85', '-0.08', 'Diffuse high-altitude cloud cover'],
            ].map(([name, c, b, desc]) => (
              <div
                key={name}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '100px 65px 75px 1fr',
                  gap: '0.75rem',
                  padding: '0.35rem 0',
                  borderBottom: '1px solid rgba(213, 224, 255, 0.05)',
                  alignItems: 'center',
                }}
              >
                <span style={{ color: 'var(--state-signal)', fontWeight: 600 }}>{name}</span>
                <span style={{ color: 'var(--text-muted)' }}>c = {c}</span>
                <span style={{ color: 'var(--text-muted)' }}>b = {b}</span>
                <span style={{ color: 'var(--text-secondary)' }}>{desc}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
