import React, { useState } from 'react';
import { SplitText } from '../components/SplitText';

interface SystemArchitectureProps {
  isActive: boolean;
}

interface ModuleData {
  id: string;
  name: string;
  category: string;
  inputs: string;
  outputs: string;
  description: string;
}

const MODULES: ModuleData[] = [
  {
    id: 'scenario',
    name: 'Scenario Engine',
    category: 'Environment',
    inputs: 'YAML Scenario Parameters, Seed',
    outputs: '6-DOF Ground Truth Target Trajectory',
    description: 'Deterministic 3D trajectory generation (straight, circular, figure-8, random) and environmental disturbance conditions.',
  },
  {
    id: 'camera',
    name: 'Virtual PTZ Camera',
    category: 'Optics & Actuation',
    inputs: 'Pan/Tilt Rate Commands [ω_az, ω_el]',
    outputs: '640×480 @ 30+ FPS Sensor Frame',
    description: 'Monochrome focal-plane camera model with 4°×3° FOV, physical slew limits (±45°/s), and sub-pixel optical projection.',
  },
  {
    id: 'perception',
    name: 'Perception Pipeline',
    category: 'Computer Vision',
    inputs: 'Raw Sensor Frame / Video Bypass',
    outputs: 'Sub-Pixel Pixel Centroid [u, v], Confidence',
    description: 'Adaptive contrast enhancement, median background filtering, center-of-gravity sub-pixel centroiding, and ONNX YOLOv8 fallback.',
  },
  {
    id: 'estimation',
    name: 'State Estimation (IMM-EKF)',
    category: 'Kalman Filtering',
    inputs: 'Pixel Measurements, Sensor Covariance R',
    outputs: 'Estimated Position & Velocity States [x, y, ẋ, ẏ]',
    description: 'Interacting Multiple Model Extended Kalman Filter switching between Constant Velocity (CV) and Constant Acceleration (CA) modes.',
  },
  {
    id: 'mode_manager',
    name: 'Mode Manager FSM',
    category: 'Decision Logic',
    inputs: 'Track Quality, Lock Status, Drop Counter',
    outputs: 'Operational State (SEARCH, ACQUIRE, TRACK, REACQ)',
    description: 'Deterministic finite-state machine governing acquisition hysteresis, coasting timeout, and recovery triggering.',
  },
  {
    id: 'controller',
    name: 'Kinematic Feedforward Controller',
    category: 'Gimbal Control',
    inputs: 'State Estimate, FOV Error, Time Step Δt',
    outputs: 'Pan/Tilt Gimbal Velocity Commands [deg/s]',
    description: 'Combines proactive velocity feedforward with proportional-integral corrective feedback to eliminate tracking lag.',
  },
];

export const SystemArchitecture: React.FC<SystemArchitectureProps> = ({ isActive }) => {
  const [selectedModule, setSelectedModule] = useState<ModuleData>(MODULES[2]);

  return (
    <section id="system" className="chapter-section">
      <div className="chapter-content-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <span className="label-caps" style={{ color: 'var(--state-signal)' }}>
            PHASE 09
          </span>
          <span style={{ width: '28px', height: '1px', backgroundColor: 'var(--border-strong)' }} />
          <span className="label-caps">MODULAR SUBSYSTEMS</span>
        </div>

        <div style={{ marginBottom: '2.5rem' }}>
          <SplitText
            text="HARDWARE-IN-THE-LOOP ARCHITECTURE."
            as="h2"
            className="title-giant text-primary"
            isVisible={isActive}
            baseDelay={80}
          />
        </div>

        {/* Interactive Module Grid & Detailed Drawer */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
          {/* Module Selection Pills */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {MODULES.map((mod) => {
              const isSelected = selectedModule.id === mod.id;
              return (
                <button
                  key={mod.id}
                  onClick={() => setSelectedModule(mod)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '1rem 1.25rem',
                    backgroundColor: isSelected ? 'var(--bg-surface-elevated)' : 'rgba(11, 16, 24, 0.65)',
                    border: isSelected ? '1px solid var(--state-signal)' : '1px solid var(--border-subtle)',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    outline: 'none',
                    textAlign: 'left',
                    transition: 'all 0.3s ease',
                  }}
                >
                  <div>
                    <span className="label-caps" style={{ fontSize: '0.65rem', color: isSelected ? 'var(--state-signal)' : 'var(--text-muted)' }}>
                      {mod.category}
                    </span>
                    <h4 className="font-display" style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.2rem' }}>
                      {mod.name}
                    </h4>
                  </div>
                  <span style={{ color: isSelected ? 'var(--state-signal)' : 'var(--text-dim)', fontSize: '1.1rem' }}>
                    {isSelected ? '●' : '○'}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Selected Module Detail Panel */}
          <div
            style={{
              padding: '2rem',
              backgroundColor: 'rgba(11, 16, 24, 0.85)',
              border: '1px solid var(--border-active)',
              backdropFilter: 'blur(12px)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
                <span className="label-caps" style={{ color: 'var(--state-signal)' }}>
                  SUBSYSTEM SPECIFICATION
                </span>
                <span className="label-caps" style={{ color: 'var(--text-muted)' }}>
                  {selectedModule.category.toUpperCase()}
                </span>
              </div>

              <h3 className="font-display" style={{ fontSize: '1.75rem', fontWeight: 700, marginBottom: '1rem' }}>
                {selectedModule.name}
              </h3>

              <p className="font-body" style={{ color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: '1.75rem' }}>
                {selectedModule.description}
              </p>
            </div>

            <div className="font-mono data-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-subtle)', fontSize: '0.8rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>INPUTS: </span>
                <span style={{ color: 'var(--text-primary)' }}>{selectedModule.inputs}</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>OUTPUTS: </span>
                <span style={{ color: 'var(--state-signal)' }}>{selectedModule.outputs}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
