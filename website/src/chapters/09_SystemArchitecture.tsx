import React, { useState } from 'react';
import { SplitText } from '../components/SplitText';
import { DocumentationVault } from '../components/DocumentationVault';

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
    description: 'Deterministic trajectory generation across 6 patterns (straight, circular, figure-8, sinusoidal, spiral, random) and 3 disturbance presets (Nominal, Difficult, Severe). Fully seeded for reproducible Monte Carlo sweeps.',
  },
  {
    id: 'camera',
    name: 'Virtual PTZ Camera',
    category: 'Optics & Actuation',
    inputs: 'Pan/Tilt Rate Commands [ω_az, ω_el]',
    outputs: '640×480 uint8 Monochrome Frame',
    description: 'Pinhole focal-plane camera model with 4°×3° FOV, ±45°/s physical slew limits, platform vibration, atmospheric degradation (5 contrast/brightness presets), and 3-stage sensor noise injection (Salt & Pepper, Gaussian, Poisson).',
  },
  {
    id: 'perception',
    name: 'Hybrid Perception Pipeline',
    category: 'Computer Vision',
    inputs: 'Raw 640×480 Sensor Frame / External Video Bypass',
    outputs: 'Sub-Pixel Centroid [u, v], Confidence ∈ [0,1]',
    description: 'Adaptive median impulse filtering → MAD background estimation → dynamic thresholding → multi-criteria candidate scoring (SNR, circularity, area). Sub-pixel localisation via Weighted CoG + 2D Gaussian surface fit (Levenberg–Marquardt). YOLOv8n fallback for degraded scenes.',
  },
  {
    id: 'estimation',
    name: 'IMM-EKF State Estimator',
    category: 'Kalman Filtering',
    inputs: '2D Angular Measurement [θx, θy], Adaptive R(confidence)',
    outputs: '6-State Fused Estimate [θx, θy, ωx, ωy, ax, ay], Mode Probabilities',
    description: 'Interacting Multiple Model EKF blending 3 kinematic sub-models (CV σ=5, CA σ=25, MANOEUVRE σ=150) via Bayesian Markov mixing. Joseph-form covariance update, Mahalanobis χ²(2) gating at 99% confidence, and multi-candidate association cost minimisation.',
  },
  {
    id: 'mode_manager',
    name: 'PAT Mode Manager FSM',
    category: 'Decision Logic',
    inputs: 'Track Quality Qtrack, Miss Counter, Confidence',
    outputs: 'State ∈ {SEARCH, ACQUIRE, TRACK, DEGRADED, REACQUIRE}',
    description: 'Composite track quality metric Qtrack combines perception confidence (35%), Mahalanobis score (25%), covariance trace (20%), and miss penalty (20%). Hysteresis gates: 3-frame acquire confirmation, 5-frame reacquisition trigger, 30-frame coasting limit.',
  },
  {
    id: 'controller',
    name: 'ADRC Gimbal Controller',
    category: 'Gimbal Control',
    inputs: '6-State Estimate, FOV Error, Δt',
    outputs: 'Pan/Tilt Rate Commands [deg/s]',
    description: 'Active Disturbance Rejection Controller with 2nd-order Non-Linear Extended State Observer (NLESO). ESO estimates total lumped disturbance (target motion + platform vibration + atmospheric drift) and cancels it in real time. Controller bandwidth ωc=2.8 rad/s, observer bandwidth ωo=12 rad/s. Anti-windup output clamping to ±20°/s.',
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
            text="ADAPTIVE PAT PIPELINE ARCHITECTURE."
            as="h2"
            className="title-giant text-primary"
            isVisible={isActive}
            baseDelay={80}
          />
        </div>

        {/* Interactive Module Grid & Detailed Drawer */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '2.5rem' }}>
          {/* Module Selection Pills */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {MODULES.map((mod) => {
              const isSelected = selectedModule.id === mod.id;
              return (
                <button
                  key={mod.id}
                  onClick={() => setSelectedModule(mod)}
                  className="beveled-glass-card"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0.9rem 1.25rem',
                    backgroundColor: isSelected ? 'rgba(169, 216, 232, 0.12)' : 'rgba(10, 19, 34, 0.55)',
                    borderColor: isSelected ? 'var(--state-signal)' : 'var(--border-subtle)',
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
            className="beveled-glass-card"
            style={{
              padding: '2rem',
              backgroundColor: 'rgba(10, 19, 34, 0.75)',
              borderColor: 'var(--border-active)',
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

            <div className="font-mono data-mono" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', paddingTop: '1.5rem', borderTop: '1px solid rgba(213, 224, 255, 0.08)', fontSize: '0.8rem' }}>
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

        {/* Technical Documentation & Blueprint Vault */}
        <div style={{ marginTop: '3rem' }}>
          <DocumentationVault />
        </div>
      </div>
    </section>
  );
};
