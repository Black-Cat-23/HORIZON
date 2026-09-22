import React from 'react';

interface PreloadGateProps {
  onEnter: () => void;
  isEntered: boolean;
  loadProgress: number;
}

export const PreloadGate: React.FC<PreloadGateProps> = () => {
  return (
    <section
      id="preload"
      className="chapter-section"
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-end',
        padding: '0 6vw 5vh 6vw',
        position: 'relative',
        zIndex: 20,
        pointerEvents: 'none',
      }}
    >
      {/* 100% Open & Unobstructed 3D World (Zero centered blocking text) */}
    </section>
  );
};
