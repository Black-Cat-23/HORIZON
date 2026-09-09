import React from 'react';
import {
  SimulationConfig,
  SimulationEngineCore,
  TrajectoryType,
  DisturbancePreset,
} from '../core/SimulationEngineCore';

interface MissionScreenViewProps {
  engine: SimulationEngineCore;
  onLaunch: () => void;
}

export const MissionScreenView: React.FC<MissionScreenViewProps> = ({ engine, onLaunch }) => {
  const [config, setConfig] = React.useState<SimulationConfig>(engine.getConfig());

  const handleTrajectoryChange = (type: TrajectoryType) => {
    const updated = { ...config, trajectory: type };
    setConfig(updated);
    engine.setConfig(updated);
  };

  const handlePresetChange = (preset: DisturbancePreset) => {
    const updated = { ...config, preset };
    setConfig(updated);
    engine.setConfig(updated);
  };

  const handleFilterChange = (filter: 'IMM' | 'KALMAN_CV' | 'KALMAN_CA') => {
    const updated = { ...config, filterType: filter };
    setConfig(updated);
    engine.setConfig(updated);
  };

  const handlePerceptionChange = (perception: 'HYBRID' | 'NEURAL' | 'CLASSICAL') => {
    const updated = { ...config, perceptionEngine: perception };
    setConfig(updated);
    engine.setConfig(updated);
  };

  return (
    <div
      style={{
        padding: '2.5rem 3rem',
        maxWidth: '1400px',
        margin: '0 auto',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
        gap: '2rem',
      }}
    >
      {/* 1. Trajectory Scenario Selector */}
      <div className="beveled-glass-card" style={{ padding: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: '#6fe8a8' }}>01 // SCENARIO CONFIGURATION</span>
        </div>
        <h3 className="font-display" style={{ fontSize: '1.3rem', color: '#F0F4FA', marginBottom: '1rem' }}>
          Target Dynamic Trajectory
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.5rem' }}>
          {(['figure8', 'circular', 'spiral', 'sinusoidal', 'straight', 'random'] as TrajectoryType[]).map((type) => {
            const isSelected = config.trajectory === type;
            return (
              <button
                key={type}
                onClick={() => handleTrajectoryChange(type)}
                style={{
                  padding: '0.85rem 1rem',
                  backgroundColor: isSelected ? 'rgba(111, 232, 168, 0.15)' : 'rgba(213, 224, 255, 0.03)',
                  border: isSelected ? '1px solid #6fe8a8' : '1px solid var(--border-subtle)',
                  color: isSelected ? '#F0F4FA' : 'var(--text-secondary)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.2s ease',
                  textTransform: 'uppercase',
                }}
              >
                {type}
              </button>
            );
          })}
        </div>

        <p className="font-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
          Executes 6-DOF geometric vector calculations simulating optical line-of-sight velocity dynamics at 60Hz.
        </p>
      </div>

      {/* 2. Environmental Disturbance Preset */}
      <div className="beveled-glass-card" style={{ padding: '2rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: '#e8a15c' }}>02 // DISTURBANCE MODEL</span>
        </div>
        <h3 className="font-display" style={{ fontSize: '1.3rem', color: '#F0F4FA', marginBottom: '1rem' }}>
          Atmospheric & Platform Noise
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', marginBottom: '1.5rem' }}>
          {(['NOMINAL', 'DIFFICULT', 'SEVERE', 'RECOVERY', 'ADVERSARIAL'] as DisturbancePreset[]).map((preset) => {
            const isSelected = config.preset === preset;
            return (
              <button
                key={preset}
                onClick={() => handlePresetChange(preset)}
                style={{
                  padding: '0.75rem 1rem',
                  backgroundColor: isSelected ? 'rgba(232, 161, 92, 0.15)' : 'rgba(213, 224, 255, 0.03)',
                  border: isSelected ? '1px solid #e8a15c' : '1px solid var(--border-subtle)',
                  color: isSelected ? '#F0F4FA' : 'var(--text-secondary)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span>{preset}</span>
                <span style={{ fontSize: '0.70rem', color: 'var(--text-muted)' }}>
                  {preset === 'NOMINAL' ? '0.5g Jitter | 0% Occlusion' : preset === 'SEVERE' ? '3.5g High Jitter | 65% Cloud' : 'Dynamic Stress'}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 3. Filter Architecture & Launch Trigger */}
      <div className="beveled-glass-card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem' }}>
            <span className="label-caps" style={{ color: '#a9d8e8' }}>03 // PAT ESTIMATION ENGINE</span>
          </div>
          <h3 className="font-display" style={{ fontSize: '1.3rem', color: '#F0F4FA', marginBottom: '1rem' }}>
            Perception & Filter Stack
          </h3>

          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
            {(['IMM', 'KALMAN_CV', 'KALMAN_CA'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => handleFilterChange(filter)}
                style={{
                  flex: 1,
                  padding: '0.65rem 0.5rem',
                  backgroundColor: config.filterType === filter ? 'rgba(169, 216, 232, 0.18)' : 'rgba(213, 224, 255, 0.03)',
                  border: config.filterType === filter ? '1px solid #a9d8e8' : '1px solid var(--border-subtle)',
                  color: config.filterType === filter ? '#F0F4FA' : 'var(--text-secondary)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {filter}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
            {(['HYBRID', 'NEURAL', 'CLASSICAL'] as const).map((perc) => (
              <button
                key={perc}
                onClick={() => handlePerceptionChange(perc)}
                style={{
                  flex: 1,
                  padding: '0.65rem 0.5rem',
                  backgroundColor: config.perceptionEngine === perc ? 'rgba(111, 232, 168, 0.18)' : 'rgba(213, 224, 255, 0.03)',
                  border: config.perceptionEngine === perc ? '1px solid #6fe8a8' : '1px solid var(--border-subtle)',
                  color: config.perceptionEngine === perc ? '#F0F4FA' : 'var(--text-secondary)',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {perc}
              </button>
            ))}
          </div>
        </div>

        {/* Launch Button */}
        <button
          onClick={onLaunch}
          style={{
            padding: '1.25rem 2rem',
            backgroundColor: '#6fe8a8',
            color: '#02060C',
            border: 'none',
            fontFamily: 'var(--font-display)',
            fontSize: '1.1rem',
            fontWeight: 800,
            letterSpacing: '0.06em',
            cursor: 'pointer',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '0.75rem',
            boxShadow: '0 8px 30px rgba(111, 232, 168, 0.35)',
            transition: 'all 0.25s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 12px 40px rgba(111, 232, 168, 0.50)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = '0 8px 30px rgba(111, 232, 168, 0.35)';
          }}
        >
          <span>LAUNCH LIVE SIMULATION</span>
          <span>→</span>
        </button>
      </div>
    </div>
  );
};
