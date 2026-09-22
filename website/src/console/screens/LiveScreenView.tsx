import React, { useRef, useEffect, useState } from 'react';
import { SimulationEngineCore, SimulationState } from '../core/SimulationEngineCore';

interface LiveScreenViewProps {
  engine: SimulationEngineCore;
}

export const LiveScreenView: React.FC<LiveScreenViewProps> = ({ engine }) => {
  const [state, setState] = useState<SimulationState>(() => (engine as any).state);
  const [isPlaying, setIsPlaying] = useState(true);
  const [speed, setSpeed] = useState(1.0);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const historyRef = useRef<{ x: number; y: number }[]>([]);

  useEffect(() => {
    engine.start();
    const unsubscribe = engine.subscribe((newState) => {
      setState(newState);

      // Keep recent 45 points for trajectory tail
      historyRef.current.push({ x: newState.targetTrue.x, y: newState.targetTrue.y });
      if (historyRef.current.length > 45) historyRef.current.shift();
    });

    return () => {
      unsubscribe();
      engine.pause();
    };
  }, [engine]);

  // Render Real-time Virtual Camera Optical Viewport onto 2D Canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;
    const centerX = width / 2;
    const centerY = height / 2;
    const scale = 14.0; // Projection zoom factor

    // 1. Clear background
    ctx.fillStyle = '#040914';
    ctx.fillRect(0, 0, width, height);

    // 2. Draw HUD Grid & Concentric Angular FOV Rings
    ctx.strokeStyle = 'rgba(213, 224, 255, 0.08)';
    ctx.lineWidth = 1;

    // Grid lines
    ctx.beginPath();
    ctx.moveTo(centerX, 0);
    ctx.lineTo(centerX, height);
    ctx.moveTo(0, centerY);
    ctx.lineTo(width, centerY);
    ctx.stroke();

    // Concentric Reticle Rings (1 mrad, 2 mrad, 3 mrad)
    [50, 110, 180, 260].forEach((r, idx) => {
      ctx.beginPath();
      ctx.arc(centerX, centerY, r, 0, Math.PI * 2);
      ctx.strokeStyle = idx === 0 ? 'rgba(111, 232, 168, 0.25)' : 'rgba(213, 224, 255, 0.06)';
      ctx.stroke();
    });

    // 3. Draw Trajectory History Tail
    if (historyRef.current.length > 1) {
      ctx.beginPath();
      historyRef.current.forEach((pt, i) => {
        const px = centerX + pt.x * scale;
        const py = centerY - pt.y * scale;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      });
      ctx.strokeStyle = 'rgba(169, 216, 232, 0.35)';
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // 4. Draw True Target Position (Cyan circle)
    const targetPx = centerX + state.targetTrue.x * scale;
    const targetPy = centerY - state.targetTrue.y * scale;

    ctx.beginPath();
    ctx.arc(targetPx, targetPy, 6, 0, Math.PI * 2);
    ctx.fillStyle = '#a9d8e8';
    ctx.fill();

    // 5. Draw Covariance Uncertainty Ellipse (Kalman P_k|k)
    const covRadiusX = Math.max(12, state.estimate.covX * scale * 1.8);
    const covRadiusY = Math.max(12, state.estimate.covY * scale * 1.8);
    const estPx = centerX + state.estimate.x * scale;
    const estPy = centerY - state.estimate.y * scale;

    ctx.save();
    ctx.beginPath();
    ctx.ellipse(estPx, estPy, covRadiusX, covRadiusY, 0, 0, Math.PI * 2);
    ctx.strokeStyle = state.patState === 'TRACK' ? 'rgba(111, 232, 168, 0.75)' : 'rgba(232, 161, 92, 0.65)';
    ctx.fillStyle = state.patState === 'TRACK' ? 'rgba(111, 232, 168, 0.08)' : 'rgba(232, 161, 92, 0.08)';
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.fill();
    ctx.restore();

    // 6. Draw Optical Targeting Crosshair & Lock Reticle
    const lockColor = state.patState === 'TRACK' ? '#6fe8a8' : state.patState === 'LOSS' ? '#e86f7f' : '#e8a15c';
    const boxSize = 28;

    ctx.strokeStyle = lockColor;
    ctx.lineWidth = 2;

    // Corner brackets
    const bLen = 8;
    // Top-Left
    ctx.beginPath();
    ctx.moveTo(estPx - boxSize / 2, estPy - boxSize / 2 + bLen);
    ctx.lineTo(estPx - boxSize / 2, estPy - boxSize / 2);
    ctx.lineTo(estPx - boxSize / 2 + bLen, estPy - boxSize / 2);
    ctx.stroke();
    // Top-Right
    ctx.beginPath();
    ctx.moveTo(estPx + boxSize / 2 - bLen, estPy - boxSize / 2);
    ctx.lineTo(estPx + boxSize / 2, estPy - boxSize / 2);
    ctx.lineTo(estPx + boxSize / 2, estPy - boxSize / 2 + bLen);
    ctx.stroke();
    // Bottom-Left
    ctx.beginPath();
    ctx.moveTo(estPx - boxSize / 2, estPy + boxSize / 2 - bLen);
    ctx.lineTo(estPx - boxSize / 2, estPy + boxSize / 2);
    ctx.lineTo(estPx - boxSize / 2 + bLen, estPy + boxSize / 2);
    ctx.stroke();
    // Bottom-Right
    ctx.beginPath();
    ctx.moveTo(estPx + boxSize / 2 - bLen, estPy + boxSize / 2);
    ctx.lineTo(estPx + boxSize / 2, estPy + boxSize / 2);
    ctx.lineTo(estPx + boxSize / 2, estPy + boxSize / 2 - bLen);
    ctx.stroke();

    // Center Cross
    ctx.beginPath();
    ctx.moveTo(estPx - 4, estPy);
    ctx.lineTo(estPx + 4, estPy);
    ctx.moveTo(estPx, estPy - 4);
    ctx.lineTo(estPx, estPy + 4);
    ctx.stroke();

    // 7. Corner Viewport HUD Annotations
    ctx.fillStyle = '#6fe8a8';
    ctx.font = '11px "Space Mono", monospace';
    ctx.fillText(`PAT: ${state.patState}`, 16, 26);
    ctx.fillText(`ERR: ${state.metrics.trackingErrorUrad.toFixed(3)} µrad`, 16, 44);
    ctx.fillText(`SNR: ${state.measurement.snrDb.toFixed(1)} dB`, 16, 62);

    ctx.fillStyle = 'rgba(213, 224, 255, 0.60)';
    ctx.fillText(`CAM FOV: 46.0°`, width - 110, 26);
    ctx.fillText(`RES: 1920x1080`, width - 110, 44);
    ctx.fillText(`FREQ: 60 Hz`, width - 110, 62);
  }, [state]);

  const handleTogglePlay = () => {
    engine.togglePlay();
    setIsPlaying(!isPlaying);
  };

  const handleSpeedChange = (newSpeed: number) => {
    setSpeed(newSpeed);
    engine.setPlaybackSpeed(newSpeed);
  };

  return (
    <div
      style={{
        padding: '1.5rem 2rem',
        maxWidth: '1500px',
        margin: '0 auto',
        display: 'grid',
        gridTemplateColumns: 'minmax(600px, 1fr) 380px',
        gap: '1.5rem',
        alignItems: 'start',
      }}
    >
      {/* Left Column: Virtual Camera Viewport & Controls */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div
          className="beveled-glass-card"
          style={{
            padding: '1rem',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            background: '#02060C',
            border: '1px solid var(--border-strong)',
          }}
        >
          {/* 2D Real-Time Camera Canvas */}
          <canvas
            ref={canvasRef}
            width={840}
            height={500}
            style={{
              width: '100%',
              height: 'auto',
              maxHeight: '520px',
              display: 'block',
              backgroundColor: '#040914',
            }}
          />

          {/* Timeline & Playback Controls Bar */}
          <div
            style={{
              width: '100%',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginTop: '1rem',
              padding: '0.5rem 1rem',
              borderTop: '1px solid rgba(213, 224, 255, 0.08)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
              <button
                onClick={handleTogglePlay}
                style={{
                  padding: '6px 14px',
                  backgroundColor: isPlaying ? 'rgba(232, 161, 92, 0.20)' : 'rgba(111, 232, 168, 0.20)',
                  border: isPlaying ? '1px solid #e8a15c' : '1px solid #6fe8a8',
                  color: '#F0F4FA',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {isPlaying ? '❚❚ PAUSE' : '▶ PLAY'}
              </button>

              <button
                onClick={() => engine.step()}
                style={{
                  padding: '6px 12px',
                  backgroundColor: 'rgba(213, 224, 255, 0.05)',
                  border: '1px solid var(--border-subtle)',
                  color: '#F0F4FA',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.78rem',
                  cursor: 'pointer',
                }}
              >
                STEP ⏭
              </button>

              <button
                onClick={() => engine.reset()}
                style={{
                  padding: '6px 12px',
                  backgroundColor: 'rgba(232, 111, 127, 0.10)',
                  border: '1px solid rgba(232, 111, 127, 0.35)',
                  color: '#e86f7f',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.78rem',
                  cursor: 'pointer',
                }}
              >
                RESET ↺
              </button>
            </div>

            {/* Speed Multiplier */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <span className="font-mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>SPEED:</span>
              {[0.5, 1.0, 2.0, 5.0].map((s) => (
                <button
                  key={s}
                  onClick={() => handleSpeedChange(s)}
                  style={{
                    padding: '4px 8px',
                    backgroundColor: speed === s ? 'rgba(169, 216, 232, 0.25)' : 'transparent',
                    border: speed === s ? '1px solid #a9d8e8' : '1px solid var(--border-subtle)',
                    color: speed === s ? '#F0F4FA' : 'var(--text-muted)',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '0.70rem',
                    cursor: 'pointer',
                  }}
                >
                  {s}x
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Right Column: Live Telemetry Meters & State Matrices */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* Metric Cards */}
        <div className="beveled-glass-card" style={{ padding: '1.25rem' }}>
          <span className="label-caps" style={{ color: '#6fe8a8', fontSize: '0.68rem' }}>OPTICAL TRACKING ACCURACY</span>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: '0.5rem' }}>
            <span className="font-display" style={{ fontSize: '1.8rem', fontWeight: 700, color: '#F0F4FA' }}>
              {state.metrics.trackingErrorUrad.toFixed(3)}
            </span>
            <span className="font-mono" style={{ fontSize: '0.85rem', color: '#6fe8a8' }}>µrad</span>
          </div>
          <div style={{ height: '4px', width: '100%', backgroundColor: 'rgba(213, 224, 255, 0.08)', marginTop: '0.5rem', borderRadius: '2px' }}>
            <div style={{ height: '100%', width: `${Math.min(100, (1.0 - state.metrics.trackingErrorUrad / 3.0) * 100)}%`, backgroundColor: '#6fe8a8', borderRadius: '2px' }} />
          </div>
        </div>

        <div className="beveled-glass-card" style={{ padding: '1.25rem' }}>
          <span className="label-caps" style={{ color: '#a9d8e8', fontSize: '0.68rem' }}>LINK STABILITY / LOCK SUCCESS</span>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: '0.5rem' }}>
            <span className="font-display" style={{ fontSize: '1.8rem', fontWeight: 700, color: '#F0F4FA' }}>
              {state.metrics.lockPercentage.toFixed(1)}%
            </span>
            <span className="font-mono" style={{ fontSize: '0.85rem', color: '#a9d8e8' }}>CONFIRMED</span>
          </div>
          <p className="font-mono" style={{ fontSize: '0.70rem', color: 'var(--text-muted)', marginTop: '0.4rem' }}>
            Total Frames Sampled: {state.frame} | Latency: {state.metrics.latencyMs.toFixed(2)}ms
          </p>
        </div>

        <div className="beveled-glass-card" style={{ padding: '1.25rem' }}>
          <span className="label-caps" style={{ color: '#e8a15c', fontSize: '0.68rem' }}>IMM PROBABILITIES</span>
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
            <div style={{ flex: 1, padding: '6px', backgroundColor: 'rgba(213, 224, 255, 0.03)', border: '1px solid var(--border-subtle)' }}>
              <div className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>CV MODEL</div>
              <div className="font-mono" style={{ fontSize: '0.90rem', fontWeight: 700, color: '#6fe8a8' }}>{(state.immProbabilities.cv * 100).toFixed(0)}%</div>
            </div>
            <div style={{ flex: 1, padding: '6px', backgroundColor: 'rgba(213, 224, 255, 0.03)', border: '1px solid var(--border-subtle)' }}>
              <div className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>CA MODEL</div>
              <div className="font-mono" style={{ fontSize: '0.90rem', fontWeight: 700, color: '#a9d8e8' }}>{(state.immProbabilities.ca * 100).toFixed(0)}%</div>
            </div>
            <div style={{ flex: 1, padding: '6px', backgroundColor: 'rgba(213, 224, 255, 0.03)', border: '1px solid var(--border-subtle)' }}>
              <div className="font-mono" style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>CT MODEL</div>
              <div className="font-mono" style={{ fontSize: '0.90rem', fontWeight: 700, color: '#e8a15c' }}>{(state.immProbabilities.ct * 100).toFixed(0)}%</div>
            </div>
          </div>
        </div>

        <div className="beveled-glass-card" style={{ padding: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--text-muted)', fontSize: '0.68rem' }}>6-DOF KINEMATIC STATE</span>
          <div className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.5rem', lineHeight: 1.6 }}>
            <div>X_EST: {state.estimate.x.toFixed(2)} px | VX: {state.estimate.vx.toFixed(2)} px/s</div>
            <div>Y_EST: {state.estimate.y.toFixed(2)} px | VY: {state.estimate.vy.toFixed(2)} px/s</div>
            <div>RESIDUALS: dx={state.estimate.residualX.toFixed(3)} | dy={state.estimate.residualY.toFixed(3)}</div>
          </div>
        </div>
      </div>
    </div>
  );
};
