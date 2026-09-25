import React from 'react';

export const IVRESSVerticalText: React.FC = () => {
  return (
    <div
      style={{
        position: 'fixed',
        right: '4.5vw',
        top: '16vh',
        zIndex: 90,
        pointerEvents: 'none',
        writingMode: 'vertical-rl',
        textOrientation: 'mixed',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.2rem',
        userSelect: 'none',
      }}
    >
      {/* Primary Japanese Poetic Line (from IVRESS) */}
      <span
        style={{
          fontFamily: "'Noto Serif JP', 'Cormorant Garamond', serif",
          fontSize: 'clamp(0.95rem, 1.4vw, 1.25rem)',
          fontWeight: 300,
          letterSpacing: '0.35em',
          color: 'rgba(255, 255, 255, 0.88)',
          textShadow: '0 0 20px rgba(0,0,0,0.8)',
          lineHeight: 1.8,
        }}
      >
        旅人は、世界の片隅で探索を続けていた
      </span>

      {/* English Editorial Subtitle */}
      <span
        className="font-mono"
        style={{
          fontSize: '0.62rem',
          letterSpacing: '0.22em',
          color: 'rgba(213, 224, 255, 0.45)',
          textTransform: 'uppercase',
        }}
      >
        A traveler continues the search in a corner of the world
      </span>
    </div>
  );
};
