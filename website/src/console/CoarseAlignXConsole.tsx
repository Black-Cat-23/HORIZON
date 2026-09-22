import React, { useState, useEffect } from 'react';
import { useSimulationEngine } from './core/SimulationEngineCore';
import { GlobalHeader } from './shell/GlobalHeader';
import { ModeSelectorBank } from './shell/ModeSelectorBank';
import { MissionScreenView } from './screens/MissionScreenView';
import { LiveScreenView } from './screens/LiveScreenView';
import { TrackScreenView } from './screens/TrackScreenView';
import { StressScreenView } from './screens/StressScreenView';
import { BenchmarkScreenView } from './screens/BenchmarkScreenView';

interface CoarseAlignXConsoleProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CoarseAlignXConsole: React.FC<CoarseAlignXConsoleProps> = ({ isOpen, onClose }) => {
  const [activeModeIndex, setActiveModeIndex] = useState<number>(1); // Default to Mode 1 (Live Flight Ops)

  const {
    engine,
    state,
    isPlaying,
    start,
    pause,
    reset,
    step,
  } = useSimulationEngine();

  // Keyboard shortcut listener (ESC to exit, 1-5 to switch modes, Space to pause/play)
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === '1') {
        setActiveModeIndex(0);
      } else if (e.key === '2') {
        setActiveModeIndex(1);
      } else if (e.key === '3') {
        setActiveModeIndex(2);
      } else if (e.key === '4') {
        setActiveModeIndex(3);
      } else if (e.key === '5') {
        setActiveModeIndex(4);
      } else if (e.code === 'Space') {
        if (e.target === document.body) {
          e.preventDefault();
          if (isPlaying) pause();
          else start();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isPlaying, start, pause, onClose]);

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 99999,
        background: 'rgba(2, 6, 12, 0.96)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        display: 'flex',
        flexDirection: 'column',
        color: '#f8fafc',
        fontFamily: "'JetBrains Mono', 'Space Mono', monospace, -apple-system, sans-serif",
        overflow: 'hidden',
        animation: 'consoleFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards',
      }}
    >
      <style>{`
        @keyframes consoleFadeIn {
          from { opacity: 0; transform: scale(0.99); }
          to { opacity: 1; transform: scale(1); }
        }
      `}</style>

      {/* Persistent Global HUD Header */}
      <GlobalHeader state={state} onClose={onClose} />

      {/* 5-Mode Navigation Bar */}
      <ModeSelectorBank activeModeIndex={activeModeIndex} onSelectMode={setActiveModeIndex} />

      {/* Main Workspace Body */}
      <div style={{ flex: 1, minHeight: 0, padding: '16px', overflow: 'hidden' }}>
        {activeModeIndex === 0 && (
          <MissionScreenView
            engine={engine}
            onLaunch={() => setActiveModeIndex(1)}
          />
        )}

        {activeModeIndex === 1 && (
          <LiveScreenView
            engine={engine}
          />
        )}

        {activeModeIndex === 2 && (
          <TrackScreenView
            engine={engine}
            state={state}
          />
        )}

        {activeModeIndex === 3 && (
          <StressScreenView
            engine={engine}
            state={state}
          />
        )}

        {activeModeIndex === 4 && <BenchmarkScreenView />}
      </div>
    </div>
  );
};
