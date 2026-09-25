import React from 'react';
import { CHAPTERS, ChapterMeta } from '../core/StateManager';
import { scrollManager } from '../core/ScrollManager';

interface ChapterRailProps {
  activeChapterId: string;
}

export const ChapterRail: React.FC<ChapterRailProps> = ({ activeChapterId }) => {
  const handleChapterClick = (chapter: ChapterMeta) => {
    const el = document.getElementById(chapter.id);
    if (el) {
      scrollManager.scrollTo(el);
    }
  };

  return (
    <nav
      aria-label="Chapter Rail"
      style={{
        position: 'fixed',
        right: '2.5vw',
        top: '50%',
        transform: 'translateY(-50%)',
        zIndex: 90,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.85rem',
        pointerEvents: 'auto',
      }}
    >
      {CHAPTERS.map((chapter) => {
        const isActive = chapter.id === activeChapterId;
        return (
          <button
            key={chapter.id}
            onClick={() => handleChapterClick(chapter)}
            aria-label={`Jump to Phase ${chapter.num}: ${chapter.title}`}
            style={{
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: '0.75rem',
              padding: '0.2rem 0',
              outline: 'none',
            }}
          >
            {/* Label revealed on active or hover */}
            <span
              className="font-mono"
              style={{
                fontSize: '0.65rem',
                letterSpacing: '0.12em',
                color: isActive ? 'var(--state-signal)' : 'var(--text-dim)',
                opacity: isActive ? 1 : 0,
                transform: isActive ? 'translateX(0)' : 'translateX(6px)',
                transition: 'all 0.3s ease',
                pointerEvents: 'none',
              }}
            >
              {chapter.num}
            </span>

            {/* Marker Dot / Dash */}
            <span
              style={{
                display: 'block',
                width: isActive ? '20px' : '4px',
                height: '2px',
                backgroundColor: isActive ? 'var(--state-signal)' : 'var(--border-strong)',
                borderRadius: '1px',
                transition: 'all 0.4s var(--ease-out-expo)',
                boxShadow: isActive ? '0 0 10px var(--state-signal)' : 'none',
              }}
            />
          </button>
        );
      })}
    </nav>
  );
};
