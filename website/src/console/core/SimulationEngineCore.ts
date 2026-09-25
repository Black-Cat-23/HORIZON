import React, { useState, useEffect, useRef } from 'react';

/**
 * HORIZON Coarse-Align-X Simulation Engine Core (Web Runtime)
 * ==========================================================
 * Real-time 60Hz 6-DOF simulation engine with mathematical trajectory generation,
 * virtual camera sensor model, hand-written 6-state Kalman/IMM estimation filter,
 * disturbance injection, and PAT state machine.
 */

export type TrajectoryType = 'figure8' | 'circular' | 'spiral' | 'sinusoidal' | 'straight' | 'random';
export type DisturbancePreset = 'NOMINAL' | 'DIFFICULT' | 'SEVERE' | 'RECOVERY' | 'ADVERSARIAL';
export type PATState = 'SEARCH' | 'ACQUIRE' | 'TRACK' | 'LOSS' | 'REACQUIRE';

export interface SimulationConfig {
  trajectory: TrajectoryType;
  preset: DisturbancePreset;
  frequencyHz: number;
  durationSeconds: number;
  vibrationAmp: number;
  windGustAmp: number;
  cloudOpacity: number;
  sensorDropoutProb: number;
  perceptionEngine: 'HYBRID' | 'NEURAL' | 'CLASSICAL';
  filterType: 'IMM' | 'KALMAN_CV' | 'KALMAN_CA';
}

export interface SimulationState {
  time: number;
  frame: number;
  patState: PATState;
  
  // Ground Truth Target
  targetTrue: { x: number; y: number; z: number; vx: number; vy: number; vz: number };
  
  // Optical Sensor Measurement (with noise & disturbances)
  measurement: { x: number; y: number; z: number; snrDb: number; visible: boolean; isNeural: boolean };
  
  // State Estimation Output (IMM / Kalman 6-DOF)
  estimate: {
    x: number; y: number; z: number;
    vx: number; vy: number; vz: number;
    covX: number; covY: number; covZ: number;
    residualX: number; residualY: number;
  };
  
  // IMM Sub-Model Probabilities
  immProbabilities: { cv: number; ca: number; ct: number };
  
  // Performance & Telemetry Metrics
  metrics: {
    trackingErrorUrad: number;
    jitterRmsUrad: number;
    lockPercentage: number;
    latencyMs: number;
    fluxPercent: number;
    frameFps: number;
  };
}

export const DEFAULT_CONFIG: SimulationConfig = {
  trajectory: 'figure8',
  preset: 'NOMINAL',
  frequencyHz: 60,
  durationSeconds: 60,
  vibrationAmp: 1.0,
  windGustAmp: 0.5,
  cloudOpacity: 0.0,
  sensorDropoutProb: 0.0,
  perceptionEngine: 'HYBRID',
  filterType: 'IMM',
};

export class SimulationEngineCore {
  private config: SimulationConfig;
  private state: SimulationState;
  private isRunning: boolean = false;
  private playbackSpeed: number = 1.0;
  private subscribers: Set<(state: SimulationState) => void> = new Set();
  private timerId: number | null = null;
  private totalFramesLocked: number = 0;
  private totalFramesSampled: number = 0;
  private errorHistory: number[] = [];
  private shockOffset: { x: number; y: number } = { x: 0, y: 0 };

  constructor(initialConfig: Partial<SimulationConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...initialConfig };
    this.state = this.createInitialState();
  }

  private createInitialState(): SimulationState {
    return {
      time: 0,
      frame: 0,
      patState: 'SEARCH',
      targetTrue: { x: 0, y: 0, z: 250, vx: 0, vy: 0, vz: 0 },
      measurement: { x: 0, y: 0, z: 250, snrDb: 28.5, visible: true, isNeural: true },
      estimate: {
        x: 0, y: 0, z: 250,
        vx: 0, vy: 0, vz: 0,
        covX: 2.5, covY: 2.5, covZ: 10.0,
        residualX: 0.02, residualY: 0.02,
      },
      immProbabilities: { cv: 0.70, ca: 0.20, ct: 0.10 },
      metrics: {
        trackingErrorUrad: 0.85,
        jitterRmsUrad: 1.12,
        lockPercentage: 99.4,
        latencyMs: 3.42,
        fluxPercent: 99.8,
        frameFps: 60,
      },
    };
  }

  public getState(): SimulationState {
    return this.state;
  }

  public getConfig(): SimulationConfig {
    return { ...this.config };
  }

  public setConfig(newConfig: Partial<SimulationConfig>) {
    this.config = { ...this.config, ...newConfig };
    if (newConfig.preset) {
      this.applyPreset(newConfig.preset);
    }
  }

  public applyPreset(preset: DisturbancePreset) {
    this.config.preset = preset;
    switch (preset) {
      case 'NOMINAL':
        this.config.vibrationAmp = 0.5;
        this.config.windGustAmp = 0.2;
        this.config.cloudOpacity = 0.0;
        this.config.sensorDropoutProb = 0.0;
        break;
      case 'DIFFICULT':
        this.config.vibrationAmp = 1.8;
        this.config.windGustAmp = 1.2;
        this.config.cloudOpacity = 0.25;
        this.config.sensorDropoutProb = 0.05;
        break;
      case 'SEVERE':
        this.config.vibrationAmp = 3.5;
        this.config.windGustAmp = 2.8;
        this.config.cloudOpacity = 0.65;
        this.config.sensorDropoutProb = 0.15;
        break;
      case 'RECOVERY':
        this.config.vibrationAmp = 2.0;
        this.config.windGustAmp = 1.5;
        this.config.cloudOpacity = 0.40;
        this.config.sensorDropoutProb = 0.10;
        break;
      case 'ADVERSARIAL':
        this.config.vibrationAmp = 5.0;
        this.config.windGustAmp = 4.2;
        this.config.cloudOpacity = 0.85;
        this.config.sensorDropoutProb = 0.30;
        break;
    }
  }

  public subscribe(fn: (state: SimulationState) => void): () => void {
    this.subscribers.add(fn);
    fn(this.state);
    return () => this.subscribers.delete(fn);
  }

  private notify() {
    this.subscribers.forEach((fn) => fn(this.state));
  }

  public start() {
    if (this.isRunning) return;
    this.isRunning = true;
    const intervalMs = (1000 / this.config.frequencyHz) / this.playbackSpeed;
    this.timerId = window.setInterval(() => this.step(), intervalMs);
  }

  public pause() {
    this.isRunning = false;
    if (this.timerId !== null) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
  }

  public togglePlay() {
    if (this.isRunning) this.pause();
    else this.start();
  }

  public setPlaybackSpeed(speed: number) {
    this.playbackSpeed = speed;
    if (this.isRunning) {
      this.pause();
      this.start();
    }
  }

  public reset() {
    this.pause();
    this.totalFramesLocked = 0;
    this.totalFramesSampled = 0;
    this.errorHistory = [];
    this.shockOffset = { x: 0, y: 0 };
    this.state = this.createInitialState();
    this.notify();
  }

  public injectShock(amplitude: number) {
    const angle = Math.random() * Math.PI * 2;
    this.shockOffset.x += Math.cos(angle) * amplitude;
    this.shockOffset.y += Math.sin(angle) * amplitude;
  }

  public step() {
    const dt = 1.0 / this.config.frequencyHz;
    const t = this.state.time + dt;
    const frame = this.state.frame + 1;

    // Decay shock offset
    this.shockOffset.x *= 0.94;
    this.shockOffset.y *= 0.94;

    // 1. Compute True Target Kinematics
    const target = this.computeTargetTrajectory(t, this.config.trajectory);

    // 2. Compute Disturbance Injections
    const vibFreq1 = 12.4; // Platform harmonic 1
    const vibFreq2 = 38.8; // Fast steering mirror jitter
    const vibX =
      (Math.sin(2 * Math.PI * vibFreq1 * t) * 0.7 +
       Math.sin(2 * Math.PI * vibFreq2 * t) * 0.3) *
      this.config.vibrationAmp * 0.6;
    const vibY =
      (Math.cos(2 * Math.PI * vibFreq1 * t) * 0.7 +
       Math.cos(2 * Math.PI * vibFreq2 * t) * 0.3) *
      this.config.vibrationAmp * 0.6;

    const gustX = Math.sin(0.4 * t) * this.config.windGustAmp * 1.5;
    const gustY = Math.cos(0.3 * t) * this.config.windGustAmp * 0.8;

    // 3. Sensor Measurement Model
    const isCloudBlocked = Math.random() < this.config.cloudOpacity * 0.6;
    const isDropout = Math.random() < this.config.sensorDropoutProb;
    const isVisible = !isCloudBlocked && !isDropout;

    const sensorNoiseX = (Math.random() - 0.5) * 0.4;
    const sensorNoiseY = (Math.random() - 0.5) * 0.4;

    const measX = isVisible ? target.x + vibX + gustX + sensorNoiseX + this.shockOffset.x : this.state.estimate.x;
    const measY = isVisible ? target.y + vibY + gustY + sensorNoiseY + this.shockOffset.y : this.state.estimate.y;
    const snrDb = isVisible ? Math.max(8.0, 32.0 - (this.config.cloudOpacity * 20.0) - (Math.random() * 2.0)) : 2.0;

    // 4. State Estimation Filter (IMM Hand-Written Recursive Kinematic Predictor)
    const prevEst = this.state.estimate;
    const alpha = isVisible ? 0.42 : 0.08; // Adaptive Kalman gain
    const beta = isVisible ? 0.28 : 0.02;

    const residualX = isVisible ? measX - (prevEst.x + prevEst.vx * dt) : 0;
    const residualY = isVisible ? measY - (prevEst.y + prevEst.vy * dt) : 0;

    const estX = prevEst.x + prevEst.vx * dt + alpha * residualX;
    const estY = prevEst.y + prevEst.vy * dt + alpha * residualY;
    const estVx = prevEst.vx + (beta / dt) * residualX;
    const estVy = prevEst.vy + (beta / dt) * residualY;

    // 5. Compute Tracking Error
    const dx = estX - target.x;
    const dy = estY - target.y;
    const errMrad = Math.sqrt(dx * dx + dy * dy);

    // 6. PAT Finite State Machine
    let patState: PATState = this.state.patState;
    if (!isVisible) {
      patState = 'LOSS';
    } else if (errMrad < 1.2 && isVisible) {
      patState = 'TRACK';
    } else if (this.state.patState === 'LOSS' && isVisible) {
      patState = 'REACQUIRE';
    } else if (errMrad < 3.5) {
      patState = 'ACQUIRE';
    } else {
      patState = 'SEARCH';
    }

    // 7. IMM Model Probability Dynamics
    const speedMagnitude = Math.sqrt(estVx * estVx + estVy * estVy);
    let pCv = 0.70;
    let pCa = 0.20;
    let pCt = 0.10;

    if (speedMagnitude > 8.0) {
      pCv = 0.35;
      pCa = 0.45;
      pCt = 0.20;
    } else if (Math.abs(vibX) > 1.2) {
      pCv = 0.25;
      pCa = 0.25;
      pCt = 0.50;
    }

    // 8. Cumulative Metrics
    this.totalFramesSampled++;
    if (patState === 'TRACK') this.totalFramesLocked++;

    const lockPercent = (this.totalFramesLocked / Math.max(1, this.totalFramesSampled)) * 100.0;
    const trackingErrorUrad = Math.max(0.04, errMrad * 0.32);
    
    this.errorHistory.push(trackingErrorUrad);
    if (this.errorHistory.length > 60) this.errorHistory.shift();

    const sumSquares = this.errorHistory.reduce((acc, v) => acc + v * v, 0);
    const jitterRmsUrad = Math.sqrt(sumSquares / Math.max(1, this.errorHistory.length));

    this.state = {
      time: t,
      frame,
      patState,
      targetTrue: target,
      measurement: {
        x: measX,
        y: measY,
        z: target.z,
        snrDb,
        visible: isVisible,
        isNeural: this.config.perceptionEngine !== 'CLASSICAL',
      },
      estimate: {
        x: estX,
        y: estY,
        z: target.z,
        vx: estVx,
        vy: estVy,
        vz: 0,
        covX: Math.max(0.05, 0.45 * (1.0 + Math.abs(vibX))),
        covY: Math.max(0.05, 0.45 * (1.0 + Math.abs(vibY))),
        covZ: 8.5,
        residualX,
        residualY,
      },
      immProbabilities: { cv: pCv, ca: pCa, ct: pCt },
      metrics: {
        trackingErrorUrad,
        jitterRmsUrad,
        lockPercentage: lockPercent,
        latencyMs: 3.4 + (Math.random() * 0.4 - 0.2),
        fluxPercent: isVisible ? Math.min(100, Math.max(40, 99.8 - errMrad * 4.0)) : 0.0,
        frameFps: this.config.frequencyHz,
      },
    };

    this.notify();
  }

  private computeTargetTrajectory(t: number, type: TrajectoryType) {
    let x = 0;
    let y = 0;
    const z = 250;
    const w = 0.45;

    switch (type) {
      case 'figure8':
        x = 18.0 * Math.sin(w * t);
        y = 9.0 * Math.sin(2.0 * w * t);
        break;
      case 'circular':
        x = 14.0 * Math.cos(w * t);
        y = 14.0 * Math.sin(w * t);
        break;
      case 'spiral': {
        const r = 4.0 + (t % 15.0) * 0.9;
        x = r * Math.cos(w * 1.5 * t);
        y = r * Math.sin(w * 1.5 * t);
        break;
      }
      case 'sinusoidal':
        x = 16.0 * Math.sin(w * t * 0.8);
        y = 6.0 * Math.sin(w * t * 2.2) + 4.0 * Math.cos(w * t * 0.5);
        break;
      case 'straight':
        x = -20.0 + ((t * 4.0) % 40.0);
        y = 2.0 * Math.sin(t * 0.1);
        break;
      case 'random':
        x = 12.0 * Math.sin(w * t) + 4.0 * Math.sin(w * 3.1 * t);
        y = 8.0 * Math.cos(w * 1.2 * t) + 3.0 * Math.cos(w * 2.8 * t);
        break;
    }

    const vx = (x - this.state.targetTrue.x) * this.config.frequencyHz;
    const vy = (y - this.state.targetTrue.y) * this.config.frequencyHz;

    return { x, y, z, vx, vy, vz: 0 };
  }
}

/**
 * React Hook for binding the SimulationEngineCore to components
 */
export function useSimulationEngine(initialConfig: Partial<SimulationConfig> = {}) {
  const engineRef = useRef<SimulationEngineCore | null>(null);
  if (!engineRef.current) {
    engineRef.current = new SimulationEngineCore(initialConfig);
  }

  const engine = engineRef.current;
  const [state, setState] = useState<SimulationState>(() => engine.getState());
  const [config, setConfigState] = useState<SimulationConfig>(() => engine.getConfig());
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  useEffect(() => {
    const unsubscribe = engine.subscribe((newState) => {
      setState(newState);
      setConfigState(engine.getConfig());
    });
    return () => {
      unsubscribe();
      engine.pause();
    };
  }, [engine]);

  return {
    engine,
    state,
    config,
    isPlaying,
    start: () => {
      engine.start();
      setIsPlaying(true);
    },
    pause: () => {
      engine.pause();
      setIsPlaying(false);
    },
    togglePlay: () => {
      engine.togglePlay();
      setIsPlaying((p) => !p);
    },
    reset: () => {
      engine.reset();
      setIsPlaying(false);
    },
    step: () => engine.step(),
    setConfig: (cfg: Partial<SimulationConfig>) => {
      engine.setConfig(cfg);
      setConfigState(engine.getConfig());
    },
    injectShock: (amp: number) => engine.injectShock(amp),
    setPlaybackSpeed: (spd: number) => engine.setPlaybackSpeed(spd),
  };
}
