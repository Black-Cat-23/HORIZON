import React from 'react';
import { ChapterMeta } from '../core/StateManager';

interface IVRESSChapterDisplayProps {
  activeChapter: ChapterMeta;
  totalChapters?: string;
}

export const IVRESSChapterDisplay: React.FC<IVRESSChapterDisplayProps> = ({
  activeChapter,
  totalChapters = '09',
}) => {
  // Use '01' on start/preload to match Image 1
  const displayNum = activeChapter.num === '00' ? '01' : activeChapter.num;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: '4vh',
        left: '4.5vw',
        zIndex: 90,
        pointerEvents: 'none',
        display: 'flex',
        alignItems: 'baseline',
        userSelect: 'none',
      }}
    >
      {/* Giant Tall Condensed Serif Roman Numerals (1:1 with Image 1) */}
      <span
        style={{
          fontFamily: "'Cormorant Garamond', 'Cinzel', serif",
          fontSize: 'clamp(5.5rem, 12vw, 11rem)',
          fontWeight: 300,
          lineHeight: 0.8,
          letterSpacing: '-0.06em',
          color: '#FFFFFF',
          textShadow: '0 0 40px rgba(255,255,255,0.25)',
        }}
      >
        {displayNum}
      </span>
      <span
        style={{
          fontFamily: "'Cormorant Garamond', serif",
          fontSize: 'clamp(1.8rem, 3.5vw, 3.2rem)',
          fontWeight: 300,
          color: 'rgba(255, 255, 255, 0.7)',
          marginLeft: '0.15rem',
          letterSpacing: '0.02em',
        }}
      >
        /{totalChapters}
      </span>
    </div>
  );
};
