import React, { useState, useEffect, useRef } from 'react';
import type { SimulationEngineCore, SimulationState, DisturbancePreset } from '../core/SimulationEngineCore';

interface StressScreenProps {
  engine: SimulationEngineCore;
  state: SimulationState;
}

export const StressScreenView: React.FC<StressScreenProps> = ({ engine, state }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const disturbanceHistoryRef = useRef<number[]>([]);
  const config = engine.getConfig();

  useEffect(() => {
    // Current net disturbance magnitude
    const netDisturbance =
      (Math.sin(2 * Math.PI * 12.4 * state.time) * config.vibrationAmp +
       Math.sin(0.4 * state.time) * config.windGustAmp);

    disturbanceHistoryRef.current.push(netDisturbance);
    if (disturbanceHistoryRef.current.length > 150) {
      disturbanceHistoryRef.current.shift();
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

    // Background
    ctx.fillStyle = '#05070a';
    ctx.fillRect(0, 0, w, h);

    // Center zero line
    const midY = h / 2;
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, midY);
    ctx.lineTo(w, midY);
    ctx.stroke();

    // Upper/lower bounds
    ctx.strokeStyle = '#334155';
    ctx.setLineDash([2, 4]);
    ctx.beginPath();
    ctx.moveTo(0, midY - 50);
    ctx.lineTo(w, midY - 50);
    ctx.moveTo(0, midY + 50);
    ctx.lineTo(w, midY + 50);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw disturbance waveform
    const history = disturbanceHistoryRef.current;
    if (history.length > 1) {
      ctx.strokeStyle = state.patState === 'TRACK' ? '#38bdf8' : state.patState === 'LOSS' ? '#ef4444' : '#f59e0b';
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i < history.length; i++) {
        const xPos = (i / 150) * w;
        const yPos = midY - history[i] * 16;
        if (i === 0) ctx.moveTo(xPos, yPos);
        else ctx.lineTo(xPos, yPos);
      }
      ctx.stroke();
    }
  }, [state, config]);

  const handlePresetSelect = (p: DisturbancePreset) => {
    engine.applyPreset(p);
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', gap: '16px', height: '100%', minHeight: 0 }}>
      {/* Left Column: Disturbance Oscilloscope & Active Stress Telemetry */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', minHeight: 0 }}>
        {/* Real-time Oscilloscope */}
        <div style={{ background: '#0b111a', border: '1px solid #1e293b', borderRadius: '6px', padding: '16px', flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: state.patState === 'TRACK' ? '#22c55e' : state.patState === 'LOSS' ? '#ef4444' : '#f59e0b',
                  boxShadow: state.patState === 'TRACK' ? '0 0 10px #22c55e' : '0 0 10px #ef4444',
                }}
              />
              <span style={{ color: '#fff', fontSize: '12px', fontWeight: 600, letterSpacing: '0.04em' }}>
                DISTURBANCE OSCILLOSCOPE & COUPLING CHANNEL
              </span>
            </div>
            <span style={{ color: '#f59e0b', fontSize: '11px', fontFamily: 'monospace' }}>
              JITTER RMS: {state.metrics.jitterRmsUrad.toFixed(2)} µrad
            </span>
          </div>

          <div style={{ flex: 1, minHeight: 0, position: 'relative', borderRadius: '4px', overflow: 'hidden', border: '1px solid #142032' }}>
            <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block' }} />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px', color: '#64748b', fontSize: '10px', fontFamily: 'monospace' }}>
            <span>SCALE: ±3.0 mrad FULL-SCALE DEFLECTION</span>
            <span>SAMPLE RATE: 60 FPS SYNCHRONOUS</span>
            <span>BEACON FLUX: {state.metrics.fluxPercent.toFixed(1)}%</span>
          </div>
        </div>

        {/* Transient Shock Generator */}
        <div style={{ background: '#0b111a', border: '1px solid #1e293b', borderRadius: '6px', padding: '16px' }}>
          <div style={{ color: '#fff', fontSize: '12px', fontWeight: 600, letterSpacing: '0.04em', marginBottom: '6px' }}>
            TRANSIENT IMPULSE & STEP DISPLACEMENT SHOCK GENERATOR
          </div>
          <div style={{ color: '#64748b', fontSize: '11px', marginBottom: '12px' }}>
            Inject instantaneous angular impulse to test filter innovations, IMM mode transitions, and reacquisition latency.
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px' }}>
            {[
              { label: '±1.0 mrad SLEW', val: 1.0 },
              { label: '±3.0 mrad GUST', val: 3.0 },
              { label: '±6.0 mrad SHOCK', val: 6.0 },
              { label: '±12.0 mrad KICK', val: 12.0 },
            ].map((btn, i) => (
              <button
                key={i}
                onClick={() => engine.injectShock(btn.val)}
                style={{
                  background: '#1e293b',
                  color: '#f8fafc',
                  border: '1px solid #334155',
                  borderRadius: '4px',
                  padding: '8px 10px',
                  fontFamily: 'monospace',
                  fontSize: '11px',
                  fontWeight: 700,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={e => (e.currentTarget.style.borderColor = '#f59e0b')}
                onMouseLeave={e => (e.currentTarget.style.borderColor = '#334155')}
              >
                {btn.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Right Column: Disturbance Sliders & Preset Matrix */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', minHeight: 0, overflowY: 'auto' }}>
        {/* Preset Selector */}
        <div style={{ background: '#0b111a', border: '1px solid #1e293b', borderRadius: '6px', padding: '14px' }}>
          <div style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, marginBottom: '8px' }}>
            ENVIRONMENTAL STRESS PRESET
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px' }}>
            {(['NOMINAL', 'DIFFICULT', 'SEVERE', 'RECOVERY', 'ADVERSARIAL'] as DisturbancePreset[]).map(p => (
              <button
                key={p}
                onClick={() => handlePresetSelect(p)}
                style={{
                  background: config.preset === p ? 'rgba(0, 229, 255, 0.15)' : '#070d16',
                  color: config.preset === p ? '#00e5ff' : '#94a3b8',
                  border: config.preset === p ? '1px solid #00e5ff' : '1px solid #142032',
                  borderRadius: '3px',
                  padding: '6px 4px',
                  fontFamily: 'monospace',
                  fontSize: '9px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Angular Vibration */}
        <div style={{ background: '#0b111a', border: '1px solid #1e293b', borderRadius: '6px', padding: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '11px', fontFamily: 'monospace', marginBottom: '6px' }}>
            <span style={{ color: '#fff', fontWeight: 600 }}>ANGULAR PLATFORM VIBRATION</span>
            <span style={{ color: '#00e5ff' }}>{config.vibrationAmp.toFixed(2)}×</span>
          </div>
          <input
            type="range"
            min="0.0"
            max="5.0"
            step="0.1"
            value={config.vibrationAmp}
            onChange={e => engine.setConfig({ vibrationAmp: parseFloat(e.target.value) })}
            style={{ width: '100%', accentColor: '#00e5ff' }}
          />
        </div>

        {/* Aerodynamic Wind Gust */}
        <div style={{ background: '#0b111a', border: '1px solid #1e293b', borderRadius: '6px', padding: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '11px', fontFamily: 'monospace', marginBottom: '6px' }}>
            <span style={{ color: '#fff', fontWeight: 600 }}>AERODYNAMIC WIND BUFFETING</span>
            <span style={{ color: '#00e5ff' }}>{config.windGustAmp.toFixed(2)}×</span>
          </div>
          <input
            type="range"
            min="0.0"
            max="5.0"
            step="0.1"
            value={config.windGustAmp}
            onChange={e => engine.setConfig({ windGustAmp: parseFloat(e.target.value) })}
            style={{ width: '100%', accentColor: '#00e5ff' }}
          />
        </div>

        {/* Cloud Scintillation / Dropouts */}
        <div style={{ background: '#0b111a', border: '1px solid #1e293b', borderRadius: '6px', padding: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '11px', fontFamily: 'monospace', marginBottom: '6px' }}>
            <span style={{ color: '#fff', fontWeight: 600 }}>CLOUD & OPTICAL ATTENUATION</span>
            <span style={{ color: '#00e5ff' }}>{(config.cloudOpacity * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min="0.0"
            max="0.95"
            step="0.05"
            value={config.cloudOpacity}
            onChange={e => engine.setConfig({ cloudOpacity: parseFloat(e.target.value) })}
            style={{ width: '100%', accentColor: '#00e5ff' }}
          />
        </div>

        {/* Sensor Dropout Probability */}
        <div style={{ background: '#0b111a', border: '1px solid #1e293b', borderRadius: '6px', padding: '14px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', fontSize: '11px', fontFamily: 'monospace', marginBottom: '6px' }}>
            <span style={{ color: '#fff', fontWeight: 600 }}>SENSOR DROPOUT PROBABILITY</span>
            <span style={{ color: '#00e5ff' }}>{(config.sensorDropoutProb * 100).toFixed(0)}%</span>
          </div>
          <input
            type="range"
            min="0.0"
            max="0.50"
            step="0.02"
            value={config.sensorDropoutProb}
            onChange={e => engine.setConfig({ sensorDropoutProb: parseFloat(e.target.value) })}
            style={{ width: '100%', accentColor: '#00e5ff' }}
          />
        </div>
      </div>
    </div>
  );
};
