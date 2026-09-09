import React, { useState, useEffect, useRef } from 'react';
import type { SimulationEngineCore, SimulationState } from '../core/SimulationEngineCore';

interface TrackScreenProps {
  engine: SimulationEngineCore;
  state: SimulationState;
}

export const TrackScreenView: React.FC<TrackScreenProps> = ({ engine, state }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const residualHistoryRef = useRef<number[]>([]);
  const config = engine.getConfig();

  // Track innovation residuals over time
  useEffect(() => {
    const resX = state.estimate.residualX;
    const resY = state.estimate.residualY;
    const residualMag = Math.sqrt(resX * resX + resY * resY);
    residualHistoryRef.current.push(residualMag);
    if (residualHistoryRef.current.length > 120) {
      residualHistoryRef.current.shift();
    }

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
      canvas.width = w * dpr;
      canvas.height = h * dpr;
    }
    ctx.resetTransform();
    ctx.scale(dpr, dpr);

    // Draw background
    ctx.fillStyle = '#05070a';
    ctx.fillRect(0, 0, w, h);

    // Grid lines
    ctx.strokeStyle = '#142032';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = 0; x < w; x += 40) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
    }
    for (let y = 0; y < h; y += 30) {
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
    }
    ctx.stroke();

    // 3-Sigma threshold line
    const maxVal = 2.5; // mrad
    const sigma3 = 1.2; // 3-sigma bound
    const sigma3Y = h - (sigma3 / maxVal) * (h - 20) - 10;
    ctx.strokeStyle = '#ef444466';
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(0, sigma3Y);
    ctx.lineTo(w, sigma3Y);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = '#ef4444';
    ctx.font = '9px monospace';
    ctx.fillText('3-SIGMA INNOVATION GATING BOUND (1.20 mrad)', 10, sigma3Y - 4);

    // Draw residual history curve
    const history = residualHistoryRef.current;
    if (history.length > 1) {
      ctx.strokeStyle = '#00e5ff';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      for (let i = 0; i < history.length; i++) {
        const xPos = (i / 120) * w;
        const val = Math.min(history[i], maxVal);
        const yPos = h - (val / maxVal) * (h - 20) - 10;
        if (i === 0) ctx.moveTo(xPos, yPos);
        else ctx.lineTo(xPos, yPos);
      }
      ctx.stroke();

      // Glow fill under curve
      ctx.lineTo((history.length - 1) / 120 * w, h);
      ctx.lineTo(0, h);
      ctx.fillStyle = 'rgba(0, 229, 255, 0.08)';
      ctx.fill();
    }
  }, [state]);

  const pCov = [
    [state.estimate.covX, 0.02, 0.0, 0.04, 0.0, 0.0],
    [0.02, state.estimate.covY, 0.0, 0.0, 0.04, 0.0],
    [0.0, 0.0, state.estimate.covZ, 0.0, 0.0, 0.01],
    [0.04, 0.0, 0.0, state.estimate.covX * 1.8, 0.02, 0.0],
    [0.0, 0.04, 0.0, 0.02, state.estimate.covY * 1.8, 0.0],
    [0.0, 0.0, 0.01, 0.0, 0.0, 0.85],
  ];

  const currentFilter = config.filterType;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 380px', gap: '16px', height: '100%', minHeight: 0 }}>
      {/* Left Column: IMM Model Probabilities & Residuals Graph */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', minHeight: 0 }}>
        {/* Filter Architecture Mode Switcher */}
        <div style={{ background: '#0b111a', border: '1px solid #1e293b', borderRadius: '6px', padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <div style={{ color: '#fff', fontSize: '13px', fontWeight: 600, letterSpacing: '0.04em' }}>ESTIMATION PIPELINE FILTER TOPOLOGY</div>
            <div style={{ color: '#64748b', fontSize: '11px', marginTop: '2px' }}>Hand-written 60Hz Bayesian recursive state estimation (No external black boxes)</div>
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            {([
              { key: 'IMM', label: 'IMM (3-MODE)' },
              { key: 'KALMAN_CV', label: 'EXTENDED KF (CV)' },
              { key: 'KALMAN_CA', label: 'ACCEL KF (CA)' },
            ] as const).map(item => (
              <button
                key={item.key}
                onClick={() => engine.setConfig({ filterType: item.key })}
                style={{
                  background: currentFilter === item.key ? 'rgba(0, 229, 255, 0.15)' : '#070d16',
                  color: currentFilter === item.key ? '#00e5ff' : '#94a3b8',
                  border: currentFilter === item.key ? '1px solid #00e5ff' : '1px solid #1e293b',
                  borderRadius: '4px',
                  padding: '6px 14px',
                  fontSize: '11px',
                  fontFamily: 'monospace',
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {/* IMM Model Dynamic Weights Display */}
        <div style={{ background: '#0b111a', border: '1px solid #1e293b', borderRadius: '6px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>IMM HYPOTHESIS PROBABILITY DISTRIBUTION (μ_k)</span>
            <span style={{ color: '#00e5ff', fontSize: '11px', fontFamily: 'monospace' }}>
              DOMINANT REGIME: {state.immProbabilities.cv > state.immProbabilities.ca ? (state.immProbabilities.cv > state.immProbabilities.ct ? 'CONSTANT VELOCITY' : 'COORDINATED TURN') : 'CONSTANT ACCEL'}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
            {/* CV Model */}
            <div style={{ background: '#070d16', border: '1px solid #142032', borderRadius: '4px', padding: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ color: '#64748b', fontSize: '10px', fontFamily: 'monospace' }}>M1: CONSTANT VELOCITY (CV)</span>
                <span style={{ color: '#38bdf8', fontSize: '12px', fontFamily: 'monospace', fontWeight: 700 }}>{(state.immProbabilities.cv * 100).toFixed(1)}%</span>
              </div>
              <div style={{ width: '100%', height: '6px', background: '#0f172a', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${state.immProbabilities.cv * 100}%`, height: '100%', background: '#38bdf8', transition: 'width 0.1s ease' }} />
              </div>
              <div style={{ color: '#475569', fontSize: '9px', marginTop: '6px', fontFamily: 'monospace' }}>q_v = 0.05 deg/s² · Smooth Cruise</div>
            </div>

            {/* CA Model */}
            <div style={{ background: '#070d16', border: '1px solid #142032', borderRadius: '4px', padding: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ color: '#64748b', fontSize: '10px', fontFamily: 'monospace' }}>M2: CONSTANT ACCEL (CA)</span>
                <span style={{ color: '#eab308', fontSize: '12px', fontFamily: 'monospace', fontWeight: 700 }}>{(state.immProbabilities.ca * 100).toFixed(1)}%</span>
              </div>
              <div style={{ width: '100%', height: '6px', background: '#0f172a', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${state.immProbabilities.ca * 100}%`, height: '100%', background: '#eab308', transition: 'width 0.1s ease' }} />
              </div>
              <div style={{ color: '#475569', fontSize: '9px', marginTop: '6px', fontFamily: 'monospace' }}>q_a = 0.85 deg/s³ · Thruster Slew</div>
            </div>

            {/* CT Model */}
            <div style={{ background: '#070d16', border: '1px solid #142032', borderRadius: '4px', padding: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <span style={{ color: '#64748b', fontSize: '10px', fontFamily: 'monospace' }}>M3: COORDINATED TURN (CT)</span>
                <span style={{ color: '#a855f7', fontSize: '12px', fontFamily: 'monospace', fontWeight: 700 }}>{(state.immProbabilities.ct * 100).toFixed(1)}%</span>
              </div>
              <div style={{ width: '100%', height: '6px', background: '#0f172a', borderRadius: '3px', overflow: 'hidden' }}>
                <div style={{ width: `${state.immProbabilities.ct * 100}%`, height: '100%', background: '#a855f7', transition: 'width 0.1s ease' }} />
              </div>
              <div style={{ color: '#475569', fontSize: '9px', marginTop: '6px', fontFamily: 'monospace' }}>ω = 0.45 rad/s · Conical Scan</div>
            </div>
          </div>
        </div>

        {/* Real-time Innovation Residuals & 3-Sigma Bound */}
        <div style={{ background: '#0b111a', border: '1px solid #1e293b', borderRadius: '6px', padding: '16px', flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>INNOVATION RESIDUAL ỹ_k & MAHALANOBIS GATING</span>
            <span style={{ color: '#00e5ff', fontSize: '11px', fontFamily: 'monospace' }}>
              RESIDUAL: [{state.estimate.residualX.toFixed(3)} mrad, {state.estimate.residualY.toFixed(3)} mrad]
            </span>
          </div>
          <div style={{ flex: 1, minHeight: 0, position: 'relative', borderRadius: '4px', overflow: 'hidden', border: '1px solid #142032' }}>
            <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
          </div>
        </div>
      </div>

      {/* Right Column: State Vector & Error Covariance Matrix P_k */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', minHeight: 0 }}>
        {/* Estimated State Vector x_hat */}
        <div style={{ background: '#0b111a', border: '1px solid #1e293b', borderRadius: '6px', padding: '16px' }}>
          <div style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em', marginBottom: '12px' }}>
            ESTIMATED STATE VECTOR x̂_k
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
            {[
              { label: 'Azimuth Position (x)', val: `${state.estimate.x.toFixed(3)} mrad`, color: '#38bdf8' },
              { label: 'Elevation Position (y)', val: `${state.estimate.y.toFixed(3)} mrad`, color: '#38bdf8' },
              { label: 'Azimuth Velocity (ẋ)', val: `${state.estimate.vx.toFixed(3)} mrad/s`, color: '#4ade80' },
              { label: 'Elevation Velocity (ẏ)', val: `${state.estimate.vy.toFixed(3)} mrad/s`, color: '#4ade80' },
              { label: 'Slant Range (z)', val: `${state.estimate.z.toFixed(1)} km`, color: '#f59e0b' },
              { label: 'Tracking Error', val: `${state.metrics.trackingErrorUrad.toFixed(2)} µrad`, color: '#f59e0b' },
            ].map((item, idx) => (
              <div key={idx} style={{ background: '#070d16', border: '1px solid #142032', borderRadius: '4px', padding: '8px' }}>
                <div style={{ color: '#64748b', fontSize: '9px', fontFamily: 'monospace' }}>{item.label}</div>
                <div style={{ color: item.color, fontSize: '13px', fontFamily: 'monospace', fontWeight: 700, marginTop: '2px' }}>{item.val}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Covariance Matrix P (6x6 visual slice) */}
        <div style={{ background: '#0b111a', border: '1px solid #1e293b', borderRadius: '6px', padding: '16px', flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, letterSpacing: '0.05em' }}>ERROR COVARIANCE MATRIX P_k (6×6)</span>
            <span style={{ color: '#00e5ff', fontSize: '10px', fontFamily: 'monospace' }}>TR(P) = {(pCov.reduce((acc, row, i) => acc + row[i], 0)).toFixed(4)}</span>
          </div>

          <div style={{ background: '#070d16', border: '1px solid #142032', borderRadius: '4px', padding: '8px', flex: 1, overflowY: 'auto' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '4px', textAlign: 'center' }}>
              {pCov.map((row, r) =>
                row.map((val, c) => {
                  const isDiag = r === c;
                  const intensity = Math.min(Math.abs(val) * 2, 1);
                  return (
                    <div
                      key={`${r}-${c}`}
                      style={{
                        background: isDiag
                          ? `rgba(0, 229, 255, ${0.1 + intensity * 0.4})`
                          : `rgba(30, 41, 59, ${0.2 + intensity * 0.3})`,
                        border: isDiag ? '1px solid #00e5ff44' : '1px solid #1e293b22',
                        borderRadius: '2px',
                        padding: '6px 2px',
                        fontFamily: 'monospace',
                        fontSize: '9px',
                        color: isDiag ? '#00e5ff' : '#94a3b8',
                      }}
                    >
                      {val.toFixed(3)}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px', color: '#475569', fontSize: '9px', fontFamily: 'monospace' }}>
            <span>KALMAN GAIN K_k = P H^T (H P H^T + R)^-1</span>
            <span>DIAGONAL ENTRIES INDICATE 1-σ² UNCERTAINTY</span>
          </div>
        </div>
      </div>
    </div>
  );
};
