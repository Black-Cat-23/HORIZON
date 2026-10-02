import React from 'react';
import { SplitText } from '../components/SplitText';

interface CompetitiveDifferentiatorProps {
  isActive: boolean;
}

const rows = [
  {
    dimension: 'Operational Scope',
    generic: 'Single scripted trajectory, static params',
    ours: '6 fully parameterised 3D paths — seeded, reproducible, seed-matched',
    key: true,
  },
  {
    dimension: 'Benchmark-2 Readiness',
    generic: 'Crashes when stripped of internal 3D scene',
    ours: 'Native 30 FPS MP4 GPU bypass — covers 30% of ISRO evaluation marks',
    key: true,
  },
  {
    dimension: 'Distractor & Sun-Glint',
    generic: 'Classical threshold: 24–26% false-lock on glint',
    ours: '0.0% false-lock — Mahalanobis gate (d² ≤ 9.21) + 4-feature consistency',
    key: true,
  },
  {
    dimension: 'High-G Maneuver Gating',
    generic: 'Fixed-noise Kalman: gate drops on sudden turns',
    ours: 'Bar-Shalom IMM-EKF — dynamic spread-of-means expansion, <180 ms re-lock',
    key: true,
  },
  {
    dimension: 'Platform Jitter / Vibration',
    generic: 'Naive PID: integrator windup and hunting',
    ours: '2nd-order NLESO ADRC — Han\'s fal() cancels lumped disturbance in real time',
    key: false,
  },
  {
    dimension: 'Sensor Transport Latency',
    generic: 'Unmodelled — assumes zero delay',
    ours: 'Smith Predictor — cancels 40–80 ms lag, preserves phase margin',
    key: false,
  },
  {
    dimension: 'Atmospheric Degradation',
    generic: 'Clean synthetic frames only',
    ours: '5 presets: Clear, Hazy, Foggy, Rain, Low Light + 10% S&P noise',
    key: false,
  },
  {
    dimension: 'Statistical Validation',
    generic: 'Single cherry-picked run shown on video',
    ours: 'Paired Wilcoxon (P=0.0061, d=35.64) across 50 seeded Monte Carlo trials',
    key: true,
  },
  {
    dimension: 'Ground-Truth Isolation',
    generic: 'Unaudited — prone to coordinate leakage',
    ours: 'Certified zero GT leakage by automated AST inspection · 1015/1015 pytests',
    key: false,
  },
  {
    dimension: 'Embedded Viability',
    generic: 'Requires desktop GPU',
    ours: '440 µs pipeline · 2.40 ms algo core · >73% headroom on Jetson Orin Nano',
    key: false,
  },
];

export const CompetitiveDifferentiator: React.FC<CompetitiveDifferentiatorProps> = ({ isActive }) => {
  return (
    <section id="differentiator" className="chapter-section">
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--state-signal)' }}>
            PHASE 09.5
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">THE COMPETITIVE EDGE</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="NOT A TRACKER. A VALIDATION PLATFORM."
            as="h2"
            className="title-giant text-primary"
            isVisible={isActive}
            baseDelay={80}
          />
        </div>

        <p
          className="font-body"
          style={{
            maxWidth: '760px',
            color: 'var(--text-secondary)',
            fontSize: '1.1rem',
            lineHeight: 1.75,
            fontWeight: 300,
            marginBottom: '2.5rem',
          }}
        >
          Generic teams build a tracking script and show a video. HORIZON systematically stress-tests four parallel architectures under identical adversarial conditions, measures every failure mode against ground truth, and delivers mathematical proof — not visual impression.
        </p>

        {/* Comparison table */}
        <div
          className="beveled-glass-card"
          style={{
            padding: 0,
            borderColor: 'var(--border-active)',
            backgroundColor: 'rgba(10, 19, 34, 0.75)',
            overflow: 'hidden',
          }}
        >
          {/* Table header */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1.6fr 1.4fr 1.8fr',
              gap: '0',
              borderBottom: '1px solid var(--border-active)',
              minWidth: '620px',
            }}
          >
            <div
              style={{
                padding: '0.75rem 1.25rem',
                borderRight: '1px solid var(--border-subtle)',
              }}
            >
              <span className="label-caps" style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>
                EVALUATION DIMENSION
              </span>
            </div>
            <div
              style={{
                padding: '0.75rem 1.25rem',
                borderRight: '1px solid var(--border-subtle)',
                backgroundColor: 'rgba(11, 16, 24, 0.4)',
              }}
            >
              <span className="label-caps" style={{ fontSize: '0.6rem', color: 'var(--text-muted)' }}>
                GENERIC / COMPETITOR APPROACH
              </span>
            </div>
            <div
              style={{
                padding: '0.75rem 1.25rem',
                backgroundColor: 'rgba(111, 232, 168, 0.04)',
              }}
            >
              <span className="label-caps" style={{ fontSize: '0.6rem', color: 'var(--state-lock)' }}>
                HORIZON (VERIFIED)
              </span>
            </div>
          </div>

          {/* Rows */}
          <div style={{ overflowX: 'auto' }}>
            {rows.map((row, i) => (
              <div
                key={row.dimension}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1.6fr 1.4fr 1.8fr',
                  gap: '0',
                  borderBottom: i < rows.length - 1 ? '1px solid rgba(213,224,255,0.05)' : 'none',
                  backgroundColor: row.key ? 'rgba(111,232,168,0.03)' : 'transparent',
                  minWidth: '620px',
                }}
              >
                <div style={{ padding: '0.7rem 1.25rem', borderRight: '1px solid rgba(213,224,255,0.06)', display: 'flex', alignItems: 'center' }}>
                  <span
                    className="font-mono"
                    style={{
                      fontSize: '0.72rem',
                      color: row.key ? 'var(--text-primary)' : 'var(--text-secondary)',
                      fontWeight: row.key ? 700 : 400,
                    }}
                  >
                    {row.key && (
                      <span style={{ color: 'var(--state-lock)', marginRight: '0.4rem' }}>▸</span>
                    )}
                    {row.dimension}
                  </span>
                </div>
                <div style={{ padding: '0.7rem 1.25rem', borderRight: '1px solid rgba(213,224,255,0.06)', display: 'flex', alignItems: 'center' }}>
                  <span className="font-mono" style={{ fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                    {row.generic}
                  </span>
                </div>
                <div
                  style={{
                    padding: '0.7rem 1.25rem',
                    display: 'flex',
                    alignItems: 'center',
                    backgroundColor: row.key ? 'rgba(111,232,168,0.05)' : 'transparent',
                  }}
                >
                  <span
                    className="font-mono"
                    style={{
                      fontSize: '0.7rem',
                      color: row.key ? 'var(--state-lock)' : 'var(--text-secondary)',
                      fontWeight: row.key ? 700 : 400,
                      lineHeight: 1.5,
                    }}
                  >
                    {row.ours}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
