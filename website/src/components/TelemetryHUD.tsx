import React from 'react';
import { TrackingMode } from '../core/StateManager';

interface TelemetryHUDProps {
  progress: number;
}

export const TelemetryHUD: React.FC<TelemetryHUDProps> = ({ progress }) => {
  let mode: TrackingMode = 'SEARCH';
  let azError = 1.84;
  let elError = -1.22;
  let rmse = 4.82;
  let lockStatus = 'SEARCHING';
  let modeColor = 'var(--state-signal)';

  if (progress < 0.22) {
    mode = 'SEARCH';
    azError = 18.2;
    elError = -12.4;
    rmse = 14.8;
    lockStatus = 'NO SIGNAL';
    modeColor = 'var(--text-muted)';
  } else if (progress >= 0.22 && progress < 0.33) {
    mode = 'SEARCH';
    azError = 4.2;
    elError = 2.8;
    rmse = 6.4;
    lockStatus = 'SPIRAL SCAN';
    modeColor = 'var(--state-signal)';
  } else if (progress >= 0.33 && progress < 0.42) {
    mode = 'ACQUIRE';
    azError = 0.85;
    elError = 0.42;
    rmse = 2.1;
    lockStatus = 'CENTROID LOCK';
    modeColor = 'var(--state-lock)';
  } else if (progress >= 0.42 && progress < 0.53) {
    mode = 'TRACK';
    azError = 0.04;
    elError = -0.02;
    rmse = 1.24;
    lockStatus = 'CLOSED-LOOP LOCK';
    modeColor = 'var(--state-lock)';
  } else if (progress >= 0.53 && progress < 0.63) {
    mode = 'DEGRADED';
    azError = 0.28;
    elError = -0.34;
    rmse = 3.65;
    lockStatus = 'JITTER / TURBULENCE';
    modeColor = 'var(--state-disturbance)';
  } else if (progress >= 0.63 && progress < 0.72) {
    mode = 'LOST';
    azError = 2.45;
    elError = 1.80;
    rmse = 8.12;
    lockStatus = 'LOCK LOST (COAST)';
    modeColor = 'var(--state-loss)';
  } else if (progress >= 0.72 && progress < 0.81) {
    mode = 'REACQUIRE';
    azError = 0.12;
    elError = -0.08;
    rmse = 1.85;
    lockStatus = 'RE-ESTABLISHED';
    modeColor = 'var(--state-lock)';
  } else {
    mode = 'TRACK';
    azError = 0.03;
    elError = 0.01;
    rmse = 1.18;
    lockStatus = 'STEADY-STATE LOCK';
    modeColor = 'var(--state-lock)';
  }

  // Telemetry HUD only activates during search/tracking phases (Phase 2+)
  if (progress < 0.22) return null;

  return (
    <aside
      aria-label="Realtime Optical Telemetry HUD"
      className="beveled-glass-card"
      style={{
        position: 'fixed',
        bottom: '3.5vh',
        right: '4vw',
        zIndex: 90,
        padding: '1.1rem 1.4rem',
        pointerEvents: 'none',
        minWidth: '260px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.65rem' }}>
        <span className="label-caps" style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>
          OPTICAL TELEMETRY
        </span>
        <span
          className="font-mono"
          style={{
            fontSize: '0.65rem',
            color: modeColor,
            fontWeight: 700,
            letterSpacing: '0.14em',
          }}
        >
          {mode}
        </span>
      </div>

      <div className="font-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', fontSize: '0.74rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>STATUS:</span>
          <span style={{ color: modeColor, fontWeight: 600 }}>{lockStatus}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>AZ / EL ERR:</span>
          <span style={{ color: 'var(--text-primary)' }}>{azError > 0 ? `+${azError.toFixed(2)}` : azError.toFixed(2)}° / {elError > 0 ? `+${elError.toFixed(2)}` : elError.toFixed(2)}°</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>RMSE:</span>
          <span style={{ color: 'var(--text-ice)' }}>{rmse.toFixed(2)} px</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <span style={{ color: 'var(--text-muted)' }}>FPA RATE:</span>
          <span style={{ color: 'var(--text-primary)' }}>30 Hz (33.3 ms)</span>
        </div>
      </div>
    </aside>
  );
};
