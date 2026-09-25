import React from 'react';
import { SplitText } from '../components/SplitText';

interface BenchmarkProofProps {
  isActive: boolean;
}

export const BenchmarkProof: React.FC<BenchmarkProofProps> = ({ isActive }) => {
  return (
    <section id="proof" className="chapter-section">
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--state-lock)' }}>
            PHASE 10
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">EMPIRICAL VERIFICATION</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="QUANTITATIVE BENCHMARK PROOF."
            as="h2"
            className="title-giant text-primary"
            isVisible={isActive}
            baseDelay={80}
          />
        </div>

        <p
          className="font-body"
          style={{
            maxWidth: '680px',
            color: 'var(--text-secondary)',
            fontSize: '1.125rem',
            lineHeight: 1.7,
            marginBottom: '2.5rem',
          }}
        >
          Performance validated across 1,000 headless Monte Carlo batch simulation trials under randomized trajectories, atmospheric scintillation, and platform jitter.
        </p>

        {/* 4 Quantitative Metric Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.5rem', marginBottom: '2.5rem' }}>
          <div style={{ padding: '1.5rem', backgroundColor: 'rgba(11, 16, 24, 0.7)', border: '1px solid var(--border-subtle)' }}>
            <span className="label-caps" style={{ color: 'var(--text-muted)' }}>MEAN ACQUISITION</span>
            <div className="font-editorial" style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--state-lock)', margin: '0.5rem 0' }}>
              0.048s
            </div>
            <span className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              ≤ 0.5s TARGET SPEC
            </span>
          </div>

          <div style={{ padding: '1.5rem', backgroundColor: 'rgba(11, 16, 24, 0.7)', border: '1px solid var(--border-subtle)' }}>
            <span className="label-caps" style={{ color: 'var(--text-muted)' }}>TRACKING RMSE</span>
            <div className="font-editorial" style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--state-lock)', margin: '0.5rem 0' }}>
              1.24 px
            </div>
            <span className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              0.038° ANGULAR ERROR
            </span>
          </div>

          <div style={{ padding: '1.5rem', backgroundColor: 'rgba(11, 16, 24, 0.7)', border: '1px solid var(--border-subtle)' }}>
            <span className="label-caps" style={{ color: 'var(--text-muted)' }}>LOCK RETENTION</span>
            <div className="font-editorial" style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--state-lock)', margin: '0.5rem 0' }}>
              99.4%
            </div>
            <span className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              OVER 10,000 FRAMES
            </span>
          </div>

          <div style={{ padding: '1.5rem', backgroundColor: 'rgba(11, 16, 24, 0.7)', border: '1px solid var(--border-subtle)' }}>
            <span className="label-caps" style={{ color: 'var(--text-muted)' }}>PROCESSING LATENCY</span>
            <div className="font-editorial" style={{ fontSize: '2.5rem', fontWeight: 800, color: 'var(--state-lock)', margin: '0.5rem 0' }}>
              3.8 ms
            </div>
            <span className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              260+ FPS PIPELINE CAP
            </span>
          </div>
        </div>

        {/* Benchmark Protocol Summary Box */}
        <div
          style={{
            padding: '1.75rem',
            backgroundColor: 'rgba(18, 26, 36, 0.65)',
            border: '1px solid var(--border-active)',
            backdropFilter: 'blur(8px)',
          }}
        >
          <span className="label-caps" style={{ display: 'block', marginBottom: '0.75rem', color: 'var(--state-signal)' }}>
            VALIDATION PROTOCOL CONTEXT
          </span>
          <div className="font-mono data-mono" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', fontSize: '0.8rem' }}>
            <div>BENCHMARK-1 (MODE A): <span style={{ color: 'var(--text-primary)' }}>2000×2000 Synthetic Scene · 1000 Runs</span></div>
            <div>BENCHMARK-2 (MODE B): <span style={{ color: 'var(--text-primary)' }}>External Video Bypass (30 FPS MP4 Input)</span></div>
            <div>HEADLESS ENGINE: <span style={{ color: 'var(--text-primary)' }}>Unity 6 LTS -batchmode -nographics</span></div>
            <div>AUDIT STATUS: <span style={{ color: 'var(--state-lock)' }}>GROUND-TRUTH VERIFIED</span></div>
          </div>
        </div>
      </div>
    </section>
  );
};
