import React from 'react';
import { SplitText } from '../components/SplitText';
import { EnterEnvironmentButton } from '../components/EnterEnvironmentButton';

interface ClosingEpilogueProps {
  isActive: boolean;
}

export const ClosingEpilogue: React.FC<ClosingEpilogueProps> = ({ isActive }) => {
  const pillars = [
    {
      id: '01',
      label: 'VALIDATE',
      title: 'Not just a tracker.',
      body: 'Dual-mode SIL platform: Mode A closed-loop PTZ + Mode B native MP4 bypass — covering 60% of ISRO evaluation marks directly.',
      color: 'var(--state-lock)',
    },
    {
      id: '02',
      label: 'STRESS',
      title: 'Not just clean frames.',
      body: '5 atmospheric profiles, 10% S&P noise, ±20 px jitter, and 3 combined disturbance presets injected simultaneously.',
      color: 'var(--state-disturbance)',
    },
    {
      id: '03',
      label: 'RECOVER',
      title: 'Not just forward lock.',
      body: '5-state FSM coasts on IMM-EKF covariance for 1.5 s under occlusion, re-acquiring in <180 ms during 2G break-turns.',
      color: 'var(--state-signal)',
    },
    {
      id: '04',
      label: 'MEASURE',
      title: 'Not visual demos.',
      body: 'Isolated ground-truth residual channel. 50-trial Wilcoxon hypothesis proof (P = 0.0061, A₁₂ = 1.00). 1015 / 1015 pytests.',
      color: 'var(--state-lock)',
    },
    {
      id: '05',
      label: 'REUSE',
      title: 'Not a one-off script.',
      body: 'Modular Python + swappable detectors / controllers. 100% ITAR-free sovereign IP. Extensible to UAV, satellite, and marine FSOC missions.',
      color: 'var(--state-signal)',
    },
  ];

  return (
    <section
      id="closing"
      className="chapter-section"
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        paddingBottom: '12vh',
      }}
    >
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--state-signal)' }}>
            PHASE 11
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">EPILOGUE</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="FROM FRAGILE DEMO TO AUDITED PLATFORM."
            as="h2"
            className="title-giant text-primary"
            isVisible={isActive}
            baseDelay={80}
          />
        </div>

        <p
          className="font-body"
          style={{
            maxWidth: '700px',
            color: 'var(--text-secondary)',
            fontSize: '1.15rem',
            lineHeight: 1.75,
            marginBottom: '3rem',
            fontWeight: 300,
          }}
        >
          HORIZON does not pitch an AI model. It pitches an empirical validation laboratory — a rigorous, reproducible, ground-truth-verified platform that systematically proves when, why, and how tracking algorithms hold or break under the exact adversarial conditions ISRO specified.
        </p>

        {/* 5 Architectural Pillars */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))',
            gap: '1px',
            backgroundColor: 'var(--border-subtle)',
            marginBottom: '3rem',
          }}
        >
          {pillars.map((p) => (
            <div
              key={p.id}
              style={{
                padding: '1.5rem 1.25rem',
                backgroundColor: 'rgba(11, 16, 24, 0.9)',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
                <span className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                  {p.id}
                </span>
                <span className="label-caps" style={{ color: p.color, fontSize: '0.65rem', fontWeight: 800 }}>
                  {p.label}
                </span>
              </div>
              <div
                className="font-editorial"
                style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.2 }}
              >
                {p.title}
              </div>
              <p
                className="font-body"
                style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6, margin: 0, fontWeight: 300 }}
              >
                {p.body}
              </p>
            </div>
          ))}
        </div>

        {/* Enter Environment Button */}
        <EnterEnvironmentButton />

        {/* Footer */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '1.5rem',
            paddingTop: '2.5rem',
            borderTop: '1px solid var(--border-subtle)',
          }}
        >
          <div>
            <span className="label-caps" style={{ color: 'var(--text-muted)' }}>PROBLEM STATEMENT</span>
            <div className="font-display" style={{ fontSize: '1.05rem', fontWeight: 600, marginTop: '0.35rem' }}>
              SIH 2026 · PS26169
            </div>
            <p className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              ISRO · AI-Based Virtual Camera Tracking for Mobile FSOC
            </p>
          </div>

          <div>
            <span className="label-caps" style={{ color: 'var(--text-muted)' }}>TEAM</span>
            <div className="font-display" style={{ fontSize: '1.05rem', fontWeight: 600, marginTop: '0.35rem' }}>
              Team Xcalibur
            </div>
            <p className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Autonomous Optical Systems & Simulation
            </p>
          </div>

          <div>
            <span className="label-caps" style={{ color: 'var(--text-muted)' }}>IMPLEMENTATION STACK</span>
            <div className="font-display" style={{ fontSize: '1.05rem', fontWeight: 600, marginTop: '0.35rem' }}>
              Python SIL + PySide6 GUI
            </div>
            <p className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Hand-written IMM-EKF & NLESO ADRC · Three.js WebGL
            </p>
          </div>

          <div>
            <span className="label-caps" style={{ color: 'var(--text-muted)' }}>VALIDATION STATUS</span>
            <div className="font-display" style={{ fontSize: '1.05rem', fontWeight: 600, marginTop: '0.35rem', color: 'var(--state-lock)' }}>
              1015 / 1015 TESTS PASSING
            </div>
            <p className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Zero ground-truth leakage · Certified by AST audit
            </p>
          </div>
        </div>

        {/* Footer Bottom Bar */}
        <div
          style={{
            marginTop: '2.5rem',
            paddingTop: '1.5rem',
            borderTop: '1px solid rgba(213, 224, 255, 0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '1rem',
          }}
        >
          <span
            className="font-mono"
            style={{
              fontSize: '0.74rem',
              letterSpacing: '0.18em',
              color: 'var(--text-secondary)',
              textTransform: 'uppercase',
            }}
          >
            All Rights Reserved - MITUL RISHI
          </span>
          <span
            className="font-mono"
            style={{
              fontSize: '0.72rem',
              letterSpacing: '0.15em',
              color: 'var(--text-muted)',
            }}
          >
            HORIZON · SIH 2026
          </span>
        </div>
      </div>
    </section>
  );
};
