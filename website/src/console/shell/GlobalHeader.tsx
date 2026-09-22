import React from 'react';
import { SimulationState } from '../core/SimulationEngineCore';

interface GlobalHeaderProps {
  state: SimulationState;
  onClose?: () => void;
  onExit?: () => void;
}

export const GlobalHeader: React.FC<GlobalHeaderProps> = ({ state, onClose, onExit }) => {
  const handleExit = onClose || onExit || (() => {});
  const getPatBadgeColor = () => {
    switch (state.patState) {
      case 'TRACK':
        return '#6fe8a8';
      case 'ACQUIRE':
      case 'SEARCH':
        return '#a9d8e8';
      case 'REACQUIRE':
        return '#e8a15c';
      case 'LOSS':
        return '#e86f7f';
      default:
        return '#a9d8e8';
    }
  };

  const badgeColor = getPatBadgeColor();

  return (
    <header
      style={{
        height: '72px',
        padding: '0 2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        backgroundColor: 'rgba(5, 11, 20, 0.95)',
        borderBottom: '1px solid rgba(213, 224, 255, 0.12)',
        backdropFilter: 'blur(16px)',
        zIndex: 50,
      }}
    >
      {/* Left: HORIZON Title & Experiment ID */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span style={{ fontSize: '1.3rem', fontWeight: 800, letterSpacing: '0.14em', color: '#F0F4FA', fontFamily: 'var(--font-display)' }}>
            HORIZON
          </span>
          <span style={{ fontSize: '0.70rem', color: '#a9d8e8', fontFamily: 'var(--font-mono)', border: '1px solid rgba(169, 216, 232, 0.35)', padding: '2px 6px' }}>
            COARSE-ALIGN-X
          </span>
        </div>

        <div style={{ height: '24px', width: '1px', backgroundColor: 'rgba(213, 224, 255, 0.15)' }} />

        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span className="font-mono" style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
            SIMULATION ENGINE // ACTIVE SESSION
          </span>
          <span className="font-mono" style={{ fontSize: '0.80rem', color: 'var(--text-primary)', fontWeight: 600 }}>
            T+ {state.time.toFixed(2)}s | FRAME #{state.frame}
          </span>
        </div>
      </div>

      {/* Center: Live Subsystem Telemetry Badges */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {/* PAT State Badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '4px 12px',
            backgroundColor: 'rgba(213, 224, 255, 0.04)',
            border: `1px solid ${badgeColor}`,
            boxShadow: `0 0 12px ${badgeColor}33`,
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: badgeColor,
              boxShadow: `0 0 8px ${badgeColor}`,
            }}
          />
          <span className="font-mono" style={{ fontSize: '0.75rem', fontWeight: 700, color: badgeColor, letterSpacing: '0.08em' }}>
            PAT: {state.patState} ({state.metrics.lockPercentage.toFixed(1)}%)
          </span>
        </div>

        {/* Optical Flux Meter */}
        <div className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', padding: '4px 10px', border: '1px solid rgba(213, 224, 255, 0.08)', backgroundColor: 'rgba(213, 224, 255, 0.02)' }}>
          FLUX: <strong style={{ color: '#6fe8a8' }}>{state.metrics.fluxPercent.toFixed(1)}%</strong>
        </div>

        {/* Jitter RMS */}
        <div className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', padding: '4px 10px', border: '1px solid rgba(213, 224, 255, 0.08)', backgroundColor: 'rgba(213, 224, 255, 0.02)' }}>
          JITTER: <strong style={{ color: '#a9d8e8' }}>{state.metrics.jitterRmsUrad.toFixed(2)} µrad</strong>
        </div>
      </div>

      {/* Right: Exit / Return to Narrative Button */}
      <button
        onClick={handleExit}
        style={{
          padding: '0.55rem 1.25rem',
          backgroundColor: 'rgba(232, 111, 127, 0.10)',
          border: '1px solid rgba(232, 111, 127, 0.40)',
          color: '#e86f7f',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.78rem',
          fontWeight: 700,
          letterSpacing: '0.08em',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(232, 111, 127, 0.25)';
          e.currentTarget.style.borderColor = '#e86f7f';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(232, 111, 127, 0.10)';
          e.currentTarget.style.borderColor = 'rgba(232, 111, 127, 0.40)';
        }}
      >
        <span>✕</span>
        <span>EXIT CONSOLE</span>
      </button>
    </header>
  );
};
