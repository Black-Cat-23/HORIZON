import React from 'react';

export interface ModeTab {
  id: number;
  code: string;
  name: string;
  description: string;
}

export const MODE_TABS: ModeTab[] = [
  { id: 0, code: 'MODE 01', name: 'MISSION CONTROL', description: 'Scenario & Trajectory Setup' },
  { id: 1, code: 'MODE 02', name: 'LIVE FLIGHT OPS', description: 'Real-time Optical Camera Viewport' },
  { id: 2, code: 'MODE 03', name: 'TRACK DIAGNOSTICS', description: '6-DOF IMM / Kalman State Estimation' },
  { id: 3, code: 'MODE 04', name: 'STRESS LAB', description: 'Real-time Disturbance & Jitter Injection' },
  { id: 4, code: 'MODE 05', name: 'BENCHMARK LAB', description: '500-Trial Monte Carlo Performance' },
];

interface ModeSelectorBankProps {
  activeModeIndex: number;
  onSelectMode: (index: number) => void;
}

export const ModeSelectorBank: React.FC<ModeSelectorBankProps> = ({ activeModeIndex, onSelectMode }) => {
  return (
    <nav
      style={{
        display: 'flex',
        alignItems: 'stretch',
        backgroundColor: 'rgba(2, 6, 12, 0.98)',
        borderBottom: '1px solid rgba(213, 224, 255, 0.12)',
        padding: '0 2rem',
        overflowX: 'auto',
      }}
    >
      {MODE_TABS.map((tab) => {
        const isActive = tab.id === activeModeIndex;
        return (
          <button
            key={tab.id}
            onClick={() => onSelectMode(tab.id)}
            style={{
              flex: 1,
              padding: '1rem 1.25rem',
              backgroundColor: isActive ? 'rgba(14, 28, 54, 0.65)' : 'transparent',
              border: 'none',
              borderBottom: isActive ? '2px solid #6fe8a8' : '2px solid transparent',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'flex-start',
              gap: '0.25rem',
              transition: 'all 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
              minWidth: '180px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span
                className="font-mono"
                style={{
                  fontSize: '0.68rem',
                  color: isActive ? '#6fe8a8' : 'var(--text-muted)',
                  fontWeight: 700,
                  letterSpacing: '0.1em',
                }}
              >
                {tab.code}
              </span>
              {isActive && (
                <span style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: '#6fe8a8' }} />
              )}
            </div>

            <span
              className="font-display"
              style={{
                fontSize: '0.92rem',
                fontWeight: 700,
                color: isActive ? '#F0F4FA' : 'var(--text-secondary)',
                letterSpacing: '0.04em',
              }}
            >
              {tab.name}
            </span>

            <span
              className="font-mono"
              style={{
                fontSize: '0.65rem',
                color: 'var(--text-muted)',
              }}
            >
              {tab.description}
            </span>
          </button>
        );
      })}
    </nav>
  );
};
