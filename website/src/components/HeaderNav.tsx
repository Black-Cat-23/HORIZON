import React, { useState, useEffect } from 'react';
import { audioManager } from '../core/AudioManager';
import { scrollManager } from '../core/ScrollManager';
import clsx from 'clsx';

interface HeaderNavProps {
  activeChapterNum: string;
  isAudioActive: boolean;
  onToggleAudio: () => void;
}

export const HeaderNav: React.FC<HeaderNavProps> = ({
  activeChapterNum,
  isAudioActive,
  onToggleAudio,
}) => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const unsubscribe = scrollManager.subscribeProgress((p) => {
      setScrolled(p > 0.02);
    });
    return unsubscribe;
  }, []);

  return (
    <header
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 'var(--header-height)',
        zIndex: 100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 5vw',
        background: scrolled
          ? 'linear-gradient(180deg, rgba(2,6,12,0.88) 0%, rgba(2,6,12,0) 100%)'
          : 'transparent',
        backdropFilter: scrolled ? 'blur(16px)' : 'none',
        transition: 'all 0.5s ease',
      }}
    >
      {/* Brand Badge */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
        <span
          className="font-editorial"
          style={{
            fontSize: '1.25rem',
            fontWeight: 800,
            letterSpacing: '0.12em',
            color: 'var(--text-primary)',
          }}
        >
          HORIZON
        </span>
        <span
          style={{
            width: '1px',
            height: '12px',
            backgroundColor: 'var(--border-strong)',
          }}
        />
        <span
          className="font-mono"
          style={{
            fontSize: '0.68rem',
            letterSpacing: '0.16em',
            color: 'var(--text-muted)',
            textTransform: 'uppercase',
          }}
        >
          SIH26169 · FSOC
        </span>
      </div>

      {/* Floating Center Phase Numerals */}
      <div
        className="font-mono"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.6rem',
          fontSize: '0.72rem',
          color: 'var(--text-secondary)',
          letterSpacing: '0.2em',
        }}
      >
        <span style={{ color: 'var(--text-muted)' }}>PHASE</span>
        <span style={{ color: 'var(--text-ice)', fontWeight: 700 }}>
          {activeChapterNum}
        </span>
        <span style={{ color: 'var(--text-dim)' }}>/</span>
        <span style={{ color: 'var(--text-muted)' }}>11</span>
      </div>

      {/* Right Controls: Sound Equalizer & External Links */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '2.5rem' }}>
        <button
          onClick={onToggleAudio}
          className={clsx('font-mono', isAudioActive && 'is-audio-active')}
          style={{
            background: 'transparent',
            border: 'none',
            color: isAudioActive ? 'var(--text-ice)' : 'var(--text-secondary)',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            fontSize: '0.7rem',
            letterSpacing: '0.18em',
            cursor: 'pointer',
            padding: '0.4rem 0.6rem',
            outline: 'none',
            transition: 'color 0.3s ease',
          }}
          title={isAudioActive ? 'Mute Atmosphere' : 'Unmute Atmosphere'}
        >
          <span>SOUND</span>
          <span className="equalizer-bar-group">
            <span className="equalizer-bar" />
            <span className="equalizer-bar" />
            <span className="equalizer-bar" />
            <span className="equalizer-bar" />
            <span className="equalizer-bar" />
          </span>
        </button>

        <a
          href="https://github.com/Black-Cat-23/HORIZON"
          target="_blank"
          rel="noopener noreferrer"
          className="font-mono"
          style={{
            color: 'var(--text-muted)',
            fontSize: '0.7rem',
            letterSpacing: '0.15em',
            textDecoration: 'none',
            transition: 'color 0.3s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
        >
          REPOSITORY ↗
        </a>
      </div>
    </header>
  );
};
