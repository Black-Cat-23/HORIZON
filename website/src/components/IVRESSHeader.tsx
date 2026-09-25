import React from 'react';
import clsx from 'clsx';

interface IVRESSHeaderProps {
  isAudioActive: boolean;
  onToggleAudio: () => void;
}

export const IVRESSHeader: React.FC<IVRESSHeaderProps> = ({
  isAudioActive,
  onToggleAudio,
}) => {
  return (
    <header
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: '90px',
        zIndex: 100,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        padding: '3vh 4vw',
        pointerEvents: 'none',
      }}
    >
      {/* Top-Left: Tall Condensed Serif Chapter Title (Matching Image 1) */}
      <div style={{ pointerEvents: 'auto' }}>
        <span
          style={{
            fontFamily: "'Cormorant Garamond', 'Cinzel', serif",
            fontSize: 'clamp(2.2rem, 3.8vw, 3.4rem)',
            fontWeight: 400,
            letterSpacing: '0.08em',
            color: '#FFFFFF',
            lineHeight: 1,
            display: 'block',
            textTransform: 'uppercase',
            textShadow: '0 0 20px rgba(255,255,255,0.15)',
          }}
        >
          HORIZON
        </span>
      </div>



      {/* Top-Right: Sound Toggle & Language (Matching Image 1) */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '1.8rem',
          pointerEvents: 'auto',
          paddingTop: '0.5rem',
        }}
      >
        <button
          onClick={onToggleAudio}
          className={clsx('font-mono', isAudioActive && 'is-audio-active')}
          style={{
            background: 'transparent',
            border: 'none',
            color: isAudioActive ? '#FFFFFF' : 'rgba(213, 224, 255, 0.65)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.6rem',
            fontSize: '0.72rem',
            letterSpacing: '0.18em',
            cursor: 'pointer',
            outline: 'none',
            transition: 'color 0.3s ease',
          }}
        >
          <span>SOUND</span>
          <span style={{ letterSpacing: '0.25em', opacity: 0.6 }}>.....</span>
        </button>

        <span
          className="font-mono"
          style={{
            fontSize: '0.72rem',
            letterSpacing: '0.15em',
            color: '#FFFFFF',
            cursor: 'pointer',
          }}
        >
          EN
        </span>
      </div>
    </header>
  );
};
