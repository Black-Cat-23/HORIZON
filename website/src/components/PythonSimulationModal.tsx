import React, { useEffect, useState } from 'react';

interface PythonSimulationModalProps {
  isOpen: boolean;
  onClose: () => void;
  spaceUrl?: string;
}

export const PythonSimulationModal: React.FC<PythonSimulationModalProps> = ({
  isOpen,
  onClose,
  spaceUrl = 'https://black-cat-23-horizon-simulation.hf.space',
}) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Keyboard shortcut (ESC to close)
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const streamUrl = `${spaceUrl}/?autoconnect=true&resize=scale`;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 999999,
        backgroundColor: 'rgba(2, 6, 12, 0.96)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        display: 'flex',
        flexDirection: 'column',
        color: '#f8fafc',
        fontFamily: "'JetBrains Mono', monospace, sans-serif",
        overflow: 'hidden',
        animation: 'modalFadeIn 0.25s ease-out forwards',
      }}
    >
      <style>{`
        @keyframes modalFadeIn {
          from { opacity: 0; transform: scale(0.99); }
          to { opacity: 1; transform: scale(1); }
        }
      `}</style>

      {/* Top HUD Control Bar */}
      <div
        style={{
          height: '52px',
          backgroundColor: 'rgba(8, 16, 32, 0.90)',
          borderBottom: '1px solid rgba(127, 212, 232, 0.25)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 20px',
          flexShrink: 0,
        }}
      >
        {/* Left Status Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span
            style={{
              width: '9px',
              height: '9px',
              borderRadius: '50%',
              backgroundColor: '#6fe8a8',
              boxShadow: '0 0 10px #6fe8a8',
              animation: 'pulse 1.8s infinite',
            }}
          />
          <span
            style={{
              fontSize: '0.78rem',
              letterSpacing: '0.12em',
              fontWeight: 600,
              color: '#7fd4e8',
            }}
          >
            LIVE PYTHON PYSIDE6 ENVIRONMENT // HUGGING FACE CLOUD
          </span>
          <span
            style={{
              fontSize: '0.70rem',
              color: 'rgba(213, 224, 255, 0.5)',
              padding: '2px 8px',
              borderRadius: '4px',
              backgroundColor: 'rgba(213, 224, 255, 0.06)',
            }}
          >
            60 Hz PAT Loop
          </span>
        </div>

        {/* Right Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            style={{
              background: 'transparent',
              border: '1px solid rgba(127, 212, 232, 0.3)',
              borderRadius: '4px',
              color: '#dce5f5',
              padding: '6px 12px',
              fontSize: '0.72rem',
              fontFamily: 'inherit',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            title="Toggle Fullscreen"
          >
            {isFullscreen ? 'STANDARD VIEW' : 'EXPAND 1080P'}
          </button>

          <button
            onClick={onClose}
            style={{
              background: 'rgba(232, 111, 127, 0.15)',
              border: '1px solid rgba(232, 111, 127, 0.4)',
              borderRadius: '4px',
              color: '#e86f7f',
              padding: '6px 16px',
              fontSize: '0.72rem',
              fontWeight: 600,
              fontFamily: 'inherit',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            CLOSE [ESC]
          </button>
        </div>
      </div>

      {/* Main Interactive Simulation Iframe Stage */}
      <div
        style={{
          flex: 1,
          width: '100%',
          height: 'calc(100% - 52px)',
          position: 'relative',
          backgroundColor: '#000000',
        }}
      >
        {isLoading && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '16px',
              backgroundColor: '#040812',
              zIndex: 10,
            }}
          >
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                border: '3px solid rgba(127, 212, 232, 0.2)',
                borderTopColor: '#7fd4e8',
                animation: 'spin 1s linear infinite',
              }}
            />
            <p
              style={{
                fontSize: '0.82rem',
                letterSpacing: '0.1em',
                color: '#7fd4e8',
              }}
            >
              ESTABLISHING WEBSOCKET LINK TO CLOUD PYTHON CONTAINER...
            </p>
            <style>{`
              @keyframes spin {
                to { transform: rotate(360deg); }
              }
            `}</style>
          </div>
        )}

        <iframe
          src={streamUrl}
          title="HORIZON PySide6 Cloud Simulation"
          onLoad={() => setIsLoading(false)}
          allow="fullscreen; autoplay"
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            display: 'block',
          }}
        />
      </div>
    </div>
  );
};
