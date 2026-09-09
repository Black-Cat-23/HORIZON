/**
 * HORIZON Central State Manager
 * Tracks global scroll progress, active chapter, live simulation telemetry, and UI modes.
 */

export interface ChapterMeta {
  id: string;
  num: string;
  title: string;
  subtitle: string;
  progressStart: number;
  progressEnd: number;
}

export const CHAPTERS: ChapterMeta[] = [
  { id: 'preload', num: '00', title: 'INITIALIZATION', subtitle: 'Virtual Optical Test Range', progressStart: 0.0, progressEnd: 0.06 },
  { id: 'unknown', num: '01', title: 'THE UNKNOWN SIGNAL', subtitle: 'Wide Angular Uncertainty', progressStart: 0.06, progressEnd: 0.15 },
  { id: 'camera', num: '02', title: 'THE VIRTUAL CAMERA', subtitle: '4°×3° Narrow Optical Window', progressStart: 0.15, progressEnd: 0.24 },
  { id: 'search', num: '03', title: 'SEARCH & SCAN', subtitle: 'Archimedean Uncertainty Sweeping', progressStart: 0.24, progressEnd: 0.33 },
  { id: 'acquire', num: '04', title: 'ACQUISITION', subtitle: 'Centroid Detection & Aperture Transit', progressStart: 0.33, progressEnd: 0.42 },
  { id: 'track', num: '05', title: 'KINEMATIC TRACKING', subtitle: 'Closed-Loop Feedforward Lock', progressStart: 0.42, progressEnd: 0.53 },
  { id: 'disturbance', num: '06', title: 'DISTURBANCE INJECTION', subtitle: 'Atmospheric Scintillation & Jitter', progressStart: 0.53, progressEnd: 0.63 },
  { id: 'loss', num: '07', title: 'LOCK LOSS', subtitle: 'Temporary Optical Occlusion', progressStart: 0.63, progressEnd: 0.72 },
  { id: 'reacquire', num: '08', title: 'RAPID REACQUISITION', subtitle: 'Adaptive Recovery Scan', progressStart: 0.72, progressEnd: 0.81 },
  { id: 'system', num: '09', title: 'SYSTEM ARCHITECTURE', subtitle: 'Modular Hardware-in-the-Loop Pipeline', progressStart: 0.81, progressEnd: 0.90 },
  { id: 'proof', num: '10', title: 'BENCHMARK PROOF', subtitle: 'Quantitative Empirical Performance', progressStart: 0.90, progressEnd: 0.97 },
  { id: 'closing', num: '11', title: 'FROM SEARCH TO LOCK', subtitle: 'Team Xcalibur · SIH 2026', progressStart: 0.97, progressEnd: 1.0 },
];

export type TrackingMode = 'SEARCH' | 'ACQUIRE' | 'TRACK' | 'DEGRADED' | 'LOST' | 'REACQUIRE';

export interface TelemetryState {
  mode: TrackingMode;
  azErrorDeg: number;
  elErrorDeg: number;
  rmsePixels: number;
  lockRetentionPct: number;
  fps: number;
  processingTimeMs: number;
  beaconConfidence: number;
}

export const INITIAL_TELEMETRY: TelemetryState = {
  mode: 'SEARCH',
  azErrorDeg: 1.84,
  elErrorDeg: -1.22,
  rmsePixels: 4.82,
  lockRetentionPct: 99.4,
  fps: 60,
  processingTimeMs: 4.2,
  beaconConfidence: 0.0,
};
