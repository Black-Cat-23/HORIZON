import React, { useState } from 'react';
import { audioManager } from '../core/AudioManager';

interface EnterEnvironmentButtonProps {
  onEnter?: () => void;
}

export const EnterEnvironmentButton: React.FC<EnterEnvironmentButtonProps> = ({ onEnter }) => {
  const [isHovered, setIsHovered] = useState(false);
  const [isLaunching, setIsLaunching] = useState(false);

  const handleTrigger = () => {
    if (isLaunching) return;
    setIsLaunching(true);

    try {
      audioManager.playBeaconLock();
    } catch {
      // Audio fallback
    }

    if (onEnter) {
      onEnter();
    } else {
      // Smoothly fly back to the 3D Hero simulation environment
      setTimeout(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setIsLaunching(false);
      }, 750);
    }
  };

  return (
    <div
      style={{
        marginTop: '3.5rem',
        marginBottom: '2rem',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        gap: '1rem',
      }}
    >
      <div
        className="beveled-glass-card"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={handleTrigger}
        style={{
          cursor: 'pointer',
          padding: '1.75rem 2.5rem',
          minWidth: '340px',
          maxWidth: '520px',
          width: '100%',
          background: isHovered
            ? 'linear-gradient(135deg, rgba(14, 30, 58, 0.85) 0%, rgba(6, 18, 36, 0.95) 100%)'
            : 'rgba(8, 16, 30, 0.70)',
          border: isHovered
            ? '1px solid var(--state-signal)'
            : '1px solid var(--border-strong)',
          boxShadow: isHovered
            ? '0 12px 40px rgba(111, 232, 168, 0.18), 0 0 24px rgba(169, 216, 232, 0.20)'
            : '0 8px 30px rgba(0, 0, 0, 0.45)',
          transition: 'all 0.4s var(--ease-out-expo)',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Animated Scanning Laser Line on Hover */}
        {isHovered && (
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '2px',
              background: 'linear-gradient(90deg, transparent, #6fe8a8, #a9d8e8, transparent)',
              animation: 'scanLine 2s linear infinite',
            }}
          />
        )}

        {/* Top Status Badges */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                backgroundColor: isLaunching ? '#6fe8a8' : isHovered ? '#6fe8a8' : 'var(--state-signal)',
                boxShadow: `0 0 10px ${isHovered ? '#6fe8a8' : 'var(--state-signal)'}`,
                animation: 'pulse 1.8s infinite',
              }}
            />
            <span
              className="font-mono"
              style={{
                fontSize: '0.72rem',
                letterSpacing: '0.12em',
                color: isHovered ? 'var(--state-lock)' : 'var(--text-secondary)',
                fontWeight: 600,
              }}
            >
              {isLaunching ? 'ENGAGING OPTICAL LINK...' : 'SIMULATION ENGINE // ONLINE'}
            </span>
          </div>

          <span
            className="font-mono"
            style={{
              fontSize: '0.70rem',
              color: 'var(--text-muted)',
              letterSpacing: '0.08em',
            }}
          >
            SYS.PAT // V6.2
          </span>
        </div>

        {/* Main CTA & Reticle */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '1.5rem',
          }}
        >
          <div>
            <div
              className="font-display"
              style={{
                fontSize: '1.55rem',
                fontWeight: 700,
                color: 'var(--text-primary)',
                letterSpacing: '0.02em',
                display: 'flex',
                alignItems: 'center',
                gap: '0.6rem',
              }}
            >
              ENTER ENVIRONMENT
              <span
                style={{
                  display: 'inline-block',
                  transform: isHovered ? 'translateX(6px)' : 'translateX(0)',
                  transition: 'transform 0.3s var(--ease-out-expo)',
                  color: 'var(--state-signal)',
                }}
              >
                →
              </span>
            </div>
            <p
              className="font-mono"
              style={{
                fontSize: '0.78rem',
                color: 'var(--text-secondary)',
                marginTop: '0.35rem',
              }}
            >
              Launch real-time 6-DOF Keplerian tracking simulation
            </p>
          </div>

          {/* Interactive Targeting Reticle Icon */}
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '50%',
              border: `1px solid ${isHovered ? 'var(--state-lock)' : 'var(--border-strong)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              position: 'relative',
              background: 'rgba(213, 224, 255, 0.04)',
              transform: isHovered ? 'rotate(90deg)' : 'rotate(0deg)',
              transition: 'all 0.5s var(--ease-out-expo)',
              flexShrink: 0,
            }}
          >
            <div
              style={{
                width: '18px',
                height: '18px',
                borderRadius: '50%',
                border: '1px dashed var(--state-signal)',
              }}
            />
            <div
              style={{
                position: 'absolute',
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: isHovered ? '#6fe8a8' : 'var(--state-signal)',
              }}
            />
          </div>
        </div>

        {/* Real-time Subsystem Telemetry Ticker */}
        <div
          style={{
            marginTop: '1.25rem',
            paddingTop: '0.85rem',
            borderTop: '1px solid rgba(213, 224, 255, 0.08)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: '0.70rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-muted)',
          }}
        >
          <span>BEACON: LOCKED (99.8%)</span>
          <span>AZ: 142.84°</span>
          <span>EL: +41.12°</span>
        </div>
      </div>
    </div>
  );
};
