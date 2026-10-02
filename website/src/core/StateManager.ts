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
  { id: 'preload',        num: '00', title: 'INITIALIZATION',          subtitle: 'Virtual Optical Test Range',                   progressStart: 0.00, progressEnd: 0.06 },
  { id: 'unknown',        num: '01', title: 'THE BOTTLENECK',           subtitle: 'Four Failure Modes of FSOC Pointing',           progressStart: 0.06, progressEnd: 0.14 },
  { id: 'camera',        num: '02', title: 'THE VIRTUAL CAMERA',        subtitle: '4°×3° Narrow Optical Window',                  progressStart: 0.14, progressEnd: 0.22 },
  { id: 'search',        num: '03', title: 'SEARCH & SCAN',             subtitle: 'Archimedean Uncertainty Sweeping',              progressStart: 0.22, progressEnd: 0.30 },
  { id: 'acquire',       num: '04', title: 'ACQUISITION',               subtitle: '0.11 s Median · 18× ISRO Spec Margin',          progressStart: 0.30, progressEnd: 0.38 },
  { id: 'track',         num: '05', title: 'CLOSED-LOOP LOCK',          subtitle: 'NLESO ADRC + Smith Predictor',                  progressStart: 0.38, progressEnd: 0.48 },
  { id: 'disturbance',   num: '06', title: 'DISTURBANCE INJECTION',     subtitle: '5 Atmospheric Presets + ±20 px Jitter',         progressStart: 0.48, progressEnd: 0.57 },
  { id: 'loss',          num: '07', title: 'LOCK LOSS',                 subtitle: 'IMM-EKF Covariance Coasting — 1.5 s Hold',      progressStart: 0.57, progressEnd: 0.65 },
  { id: 'reacquire',     num: '08', title: 'RAPID REACQUISITION',       subtitle: '<180 ms Under 2G Break-Turns',                   progressStart: 0.65, progressEnd: 0.73 },
  { id: 'system',        num: '09', title: 'SYSTEM ARCHITECTURE',       subtitle: 'Dual-Mode SIL Validation Platform',             progressStart: 0.73, progressEnd: 0.82 },
  { id: 'differentiator', num: '09½', title: 'THE COMPETITIVE EDGE',    subtitle: 'Not a Tracker — An Audited Platform',           progressStart: 0.82, progressEnd: 0.90 },
  { id: 'proof',         num: '10', title: 'BENCHMARK PROOF',           subtitle: '50-Trial Monte Carlo · ISRO Spec Margins',      progressStart: 0.90, progressEnd: 0.97 },
  { id: 'closing',       num: '11', title: 'AUDITED PLATFORM',          subtitle: 'Team Xcalibur · SIH 2026 · PS26169',           progressStart: 0.97, progressEnd: 1.00 },
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
