export const ALGOS = [
  { id: "B0", name: "B0-Naive" },
  { id: "B1", name: "B1-Classical" },
  { id: "B2", name: "B2-Neural" },
  { id: "OURS", name: "Ours" },
];

export const MODES = ["SEARCH", "ACQUIRE", "TRACK", "DEGRADED", "REACQUIRE"];

export const DISTURB_KEYS = [
  { key: "vibration", label: "Vibration" },
  { key: "sensorNoise", label: "Sensor noise" },
  { key: "motionBlur", label: "Motion blur" },
  { key: "intensity", label: "Signal intensity" },
  { key: "occlusion", label: "Occlusion duration" },
  { key: "distractors", label: "False distractors" },
  { key: "latency", label: "Actuator latency" },
];

export const PRESETS = {
  NOMINAL: { vibration: 0, sensorNoise: 0.04, motionBlur: 0, intensity: 0, occlusion: 0, distractors: 0, latency: 0 },
  DIFFICULT: { vibration: 0.25, sensorNoise: 0.18, motionBlur: 0.2, intensity: 0.15, occlusion: 0.1, distractors: 0.15, latency: 0.08 },
  SEVERE: { vibration: 0.55, sensorNoise: 0.4, motionBlur: 0.45, intensity: 0.35, occlusion: 0.3, distractors: 0.35, latency: 0.22 },
  RECOVERY: { vibration: 0.35, sensorNoise: 0.22, motionBlur: 0.15, intensity: 0.2, occlusion: 0.45, distractors: 0.1, latency: 0.12 },
  ADVERSARIAL: { vibration: 0.7, sensorNoise: 0.55, motionBlur: 0.6, intensity: 0.5, occlusion: 0.55, distractors: 0.7, latency: 0.4 },
};

const listeners = new Set();

export const store = {
  screen: "setup",
  running: false,
  simTime: 0,
  fps: 0,
  latencyMs: 0,
  mode: "SEARCH",
  config: {
    speed: 12,
    accel: 1.5,
    offset: 8,
    fov: 40,
    resolution: "1920x1080",
    preset: "NOMINAL",
    algorithms: { B0: true, B1: true, B2: true, OURS: true },
  },
  disturb: { ...PRESETS.NOMINAL },
  disturbPreset: "NOMINAL",
  activeAlgo: "OURS",
  truth: { tx: 8, ty: 0, wx: 0, wy: 0, ax: 0, ay: 0 },
  meas: { tx: 8, ty: 0 },
  est: { tx: 8, ty: 0, wx: 0, wy: 0, ax: 0, ay: 0 },
  cov: { cxx: 4, cxy: 0, cyy: 4 },
  confidence: 0.2,
  angErr: 8,
  trailActual: [],
  trailPred: [],
  events: [],
  replaySeed: null,
  bench: null,
  benchProgress: null,
};

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function emit() {
  for (const fn of listeners) fn(store);
}

export function patch(partial) {
  Object.assign(store, partial);
  emit();
}

export function setConfig(partial) {
  Object.assign(store.config, partial);
  emit();
}

export function setDisturb(partial, fromPreset = false) {
  Object.assign(store.disturb, partial);
  if (!fromPreset) store.disturbPreset = "Custom";
  emit();
}

export function applyPreset(name) {
  store.disturb = { ...PRESETS[name] };
  store.disturbPreset = name;
  store.config.preset = name;
  emit();
}

export function pushEvent(text) {
  const t = store.simTime.toFixed(1);
  store.events = [`${t}s — ${text}`, ...store.events].slice(0, 8);
  emit();
}

export function selectedAlgos() {
  return ALGOS.filter((a) => store.config.algorithms[a.id]);
}
