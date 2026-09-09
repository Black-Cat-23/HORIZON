import React from 'react';
import { SplitText } from '../components/SplitText';

interface ClosingEpilogueProps {
  isActive: boolean;
}

export const ClosingEpilogue: React.FC<ClosingEpilogueProps> = ({ isActive }) => {
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
            text="FROM SEARCH TO CONTINUOUS LOCK."
            as="h2"
            className="title-giant text-primary"
            isVisible={isActive}
            baseDelay={80}
          />
        </div>

        <p
          className="font-body"
          style={{
            maxWidth: '640px',
            color: 'var(--text-secondary)',
            fontSize: '1.25rem',
            lineHeight: 1.7,
            marginBottom: '3rem',
          }}
        >
          HORIZON bridges high-speed computer vision perception with sub-milliradian kinematic tracking, establishing reliable optical communication links for next-generation aerospace and mobile terminals.
        </p>

        {/* Footer Credit & Link Cards */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
            gap: '1.5rem',
            paddingTop: '2.5rem',
            borderTop: '1px solid var(--border-subtle)',
          }}
        >
          <div>
            <span className="label-caps" style={{ color: 'var(--text-muted)' }}>PROBLEM STATEMENT</span>
            <div className="font-display" style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '0.35rem' }}>
              SIH 2026 · PS26169
            </div>
            <p className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              AI-Based Virtual Camera Tracking for Mobile FSOC
            </p>
          </div>

          <div>
            <span className="label-caps" style={{ color: 'var(--text-muted)' }}>TEAM</span>
            <div className="font-display" style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '0.35rem' }}>
              Team Xcalibur
            </div>
            <p className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Autonomous Optical Systems & Simulation
            </p>
          </div>

          <div>
            <span className="label-caps" style={{ color: 'var(--text-muted)' }}>IMPLEMENTATION STACK</span>
            <div className="font-display" style={{ fontSize: '1.1rem', fontWeight: 600, marginTop: '0.35rem' }}>
              Unity 6 LTS + Three.js
            </div>
            <p className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              C# Kalman Hand-Written + TypeScript WebGL
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
