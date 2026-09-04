import { store, patch, pushEvent } from "./store.js";

let lastMode = "SEARCH";
let lastTs = 0;
let frames = 0;
let fpsWindow = 0;
let rng = mulberry32(1);

export function setSeed(seed) {
  rng = mulberry32(seed >>> 0 || 1);
}

function mulberry32(a) {
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function gauss() {
  const u = Math.max(1e-9, rng());
  const v = rng();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
}

function damp(cur, target, dt, tau) {
  const a = 1 - Math.exp(-dt / tau);
  return cur + (target - cur) * a;
}

export function startRun(seed = null) {
  const s = seed ?? ((Math.random() * 1e9) | 0);
  setSeed(s);
  store.replaySeed = s;
  store.running = true;
  store.simTime = 0;
  store.events = [];
  store.trailActual = [];
  store.trailPred = [];
  store.mode = "SEARCH";
  lastMode = "SEARCH";
  const off = store.config.offset;
  store.truth = { tx: off, ty: 0, wx: store.config.speed * 0.02, wy: 0, ax: 0, ay: 0 };
  store.est = { tx: 0, ty: 0, wx: 0, wy: 0, ax: 0, ay: 0 };
  store.cov = { cxx: 12, cxy: 0, cyy: 12 };
  store.confidence = 0.15;
  pushEvent("run armed — searching");
}

export function tick(now) {
  if (!lastTs) lastTs = now;
  const dt = Math.min(0.05, (now - lastTs) / 1000);
  lastTs = now;
  frames += 1;
  fpsWindow += dt;
  if (fpsWindow >= 0.25) {
    store.fps = frames / fpsWindow;
    frames = 0;
    fpsWindow = 0;
  }

  const d = store.disturb;
  const cfg = store.config;
  if (store.running) store.simTime += dt;

  const wobble = Math.sin(store.simTime * 0.7) * cfg.speed * 0.04;
  store.truth.ax = cfg.accel * Math.sin(store.simTime * 0.35) * 0.2;
  store.truth.ay = cfg.accel * Math.cos(store.simTime * 0.28) * 0.12;
  store.truth.wx += store.truth.ax * dt;
  store.truth.wy += store.truth.ay * dt;
  store.truth.tx += (store.truth.wx + wobble) * dt * 4;
  store.truth.ty += store.truth.wy * dt * 4;
  store.truth.tx += Math.sin(store.simTime * (1 + d.vibration * 8)) * d.vibration * 0.35;

  const noise = 0.15 + d.sensorNoise * 4 + d.motionBlur * 2;
  const occluded = d.occlusion > 0.05 && (store.simTime % 4) < d.occlusion * 1.6;
  const measTx = occluded ? store.meas.tx : store.truth.tx + gauss() * noise + (rng() - 0.5) * d.distractors * 6;
  const measTy = occluded ? store.meas.ty : store.truth.ty + gauss() * noise + (rng() - 0.5) * d.distractors * 6;
  store.meas = { tx: measTx, ty: measTy };

  const algoLag = store.activeAlgo === "B0" ? 0.22 : store.activeAlgo === "B1" ? 0.12 : store.activeAlgo === "B2" ? 0.09 : 0.05;
  const tau = 0.08 + algoLag + d.latency * 0.4;
  store.est.tx = damp(store.est.tx, measTx, dt, tau);
  store.est.ty = damp(store.est.ty, measTy, dt, tau);
  store.est.wx = damp(store.est.wx, (measTx - store.est.tx) / Math.max(dt, 1e-3), dt, 0.25);
  store.est.wy = damp(store.est.wy, (measTy - store.est.ty) / Math.max(dt, 1e-3), dt, 0.25);
  store.est.ax = damp(store.est.ax, store.truth.ax, dt, 0.4);
  store.est.ay = damp(store.est.ay, store.truth.ay, dt, 0.4);

  const predTx = store.est.tx + store.est.wx * 0.12;
  const predTy = store.est.ty + store.est.wy * 0.12;

  const dx = store.est.tx - store.truth.tx;
  const dy = store.est.ty - store.truth.ty;
  store.angErr = Math.hypot(dx, dy);

  const q = 0.4 + noise;
  store.cov.cxx = damp(store.cov.cxx, q + Math.abs(dx), dt, 0.2);
  store.cov.cyy = damp(store.cov.cyy, q + Math.abs(dy), dt, 0.2);
  store.cov.cxy = damp(store.cov.cxy, dx * dy * 0.05, dt, 0.3);
  store.confidence = Math.max(0.05, Math.min(0.95, 1 / (1 + store.angErr * (0.35 + d.sensorNoise))));

  store.latencyMs = (4 + algoLag * 40 + d.latency * 18 + d.motionBlur * 8) * (0.85 + rng() * 0.3);

  if (store.running) {
    store.trailActual.push({ x: store.truth.tx, y: store.truth.ty });
    store.trailPred.push({ x: predTx, y: predTy });
    if (store.trailActual.length > 180) {
      store.trailActual.shift();
      store.trailPred.shift();
    }
    updateMode();
  }

  patch({});
}

function updateMode() {
  const e = store.angErr;
  const d = store.disturb;
  const load = d.vibration + d.occlusion + d.distractors + d.sensorNoise;
  let next = store.mode;
  if (e > 6.5) next = store.mode === "TRACK" || store.mode === "DEGRADED" ? "REACQUIRE" : "SEARCH";
  else if (e > 3.2) next = load > 0.6 ? "DEGRADED" : "ACQUIRE";
  else if (e > 1.4) next = load > 0.85 ? "DEGRADED" : store.mode === "SEARCH" ? "ACQUIRE" : "TRACK";
  else next = load > 1.2 ? "DEGRADED" : "TRACK";

  if (next !== lastMode) {
    store.mode = next;
    lastMode = next;
    const msg = {
      SEARCH: "searching field",
      ACQUIRE: "target acquired",
      TRACK: "lock confirmed",
      DEGRADED: "disturbance: track degraded",
      REACQUIRE: "lock lost — reacquire",
    }[next];
    pushEvent(msg);
  }
}

export function runMonteCarlo(n, algoIds, onProgress) {
  const metrics = {};
  for (const id of algoIds) {
    metrics[id] = {
      acq: [],
      ttl: [],
      err: [],
      retain: [],
      reac: [],
      falseLock: [],
      envelope: [],
      failures: [],
    };
  }

  return new Promise((resolve) => {
    let i = 0;
    function step() {
      const batch = Math.min(n, i + 8);
      for (; i < batch; i++) {
        for (const id of algoIds) {
          const seed = (i + 1) * 9973 + id.charCodeAt(0) * 13;
          const r = trial(seed, id, store.disturb);
          const m = metrics[id];
          m.acq.push(r.acquired ? 1 : 0);
          if (r.ttl != null) m.ttl.push(r.ttl);
          m.err.push(r.meanErr);
          m.retain.push(r.retained ? 1 : 0);
          if (r.reac != null) m.reac.push(r.reac);
          m.falseLock.push(r.falseLock ? 1 : 0);
          m.envelope.push({ x: r.severity, y: r.meanErr });
          if (id === "OURS" && !r.retained) m.failures.push({ trial: i, seed, t: r.lostAt });
        }
      }
      onProgress(i, n);
      if (i < n) requestAnimationFrame(step);
      else resolve(summarize(metrics, algoIds));
    }
    step();
  });
}

function trial(seed, algoId, disturb) {
  const rand = mulberry32(seed);
  const g = () => {
    const u = Math.max(1e-9, rand());
    const v = rand();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  };
  const lag = algoId === "B0" ? 0.28 : algoId === "B1" ? 0.16 : algoId === "B2" ? 0.11 : 0.05;
  const skill = algoId === "OURS" ? 0.62 : algoId === "B2" ? 0.85 : algoId === "B1" ? 1.05 : 1.35;
  const severity =
    disturb.vibration + disturb.sensorNoise + disturb.motionBlur + disturb.occlusion + disturb.distractors + disturb.latency + disturb.intensity;
  let errAcc = 0;
  let acquired = false;
  let ttl = null;
  let lostAt = null;
  let retained = true;
  let reac = null;
  let falseLock = false;
  let est = 0;
  let truth = store.config.offset;
  const steps = 240;
  for (let s = 0; s < steps; s++) {
    const t = s * 0.05;
    truth += (store.config.speed * 0.03 + Math.sin(t) * 0.2) * 0.05;
    const n = (0.2 + severity * 1.4) * skill;
    const meas = truth + g() * n;
    est += (meas - est) * (1 - Math.exp(-0.05 / (0.07 + lag)));
    const e = Math.abs(est - truth);
    errAcc += e;
    if (!acquired && e < 1.6) {
      acquired = true;
      ttl = t;
    }
    if (acquired && e > 5.5 && lostAt == null) {
      lostAt = t;
      retained = false;
    }
    if (lostAt != null && e < 1.8 && reac == null) reac = t - lostAt;
    if (!acquired && e < 0.8 && t < 0.4) falseLock = true;
  }
  return {
    acquired,
    ttl,
    meanErr: errAcc / steps,
    retained,
    reac,
    falseLock,
    severity,
    lostAt,
  };
}

function pct(arr) {
  if (!arr.length) return null;
  return (arr.reduce((a, b) => a + b, 0) / arr.length) * 100;
}

function mean(arr) {
  if (!arr.length) return null;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function percentile(arr, p) {
  if (!arr.length) return null;
  const s = [...arr].sort((a, b) => a - b);
  const i = Math.min(s.length - 1, Math.floor((p / 100) * s.length));
  return s[i];
}

function summarize(metrics, algoIds) {
  const rows = [
    { id: "acq", label: "Acquisition success %", better: "high", pick: (m) => pct(m.acq) },
    { id: "ttlMed", label: "Median time-to-lock (s)", better: "low", pick: (m) => percentile(m.ttl, 50) },
    { id: "ttlP95", label: "P95 time-to-lock (s)", better: "low", pick: (m) => percentile(m.ttl, 95) },
    { id: "errMean", label: "Mean tracking error (deg)", better: "low", pick: (m) => mean(m.err) },
    { id: "errP95", label: "P95 tracking error (deg)", better: "low", pick: (m) => percentile(m.err, 95) },
    { id: "errP99", label: "P99 tracking error (deg)", better: "low", pick: (m) => percentile(m.err, 99) },
    { id: "retain", label: "Lock retention %", better: "high", pick: (m) => pct(m.retain) },
    { id: "reac", label: "Reacquisition time (s)", better: "low", pick: (m) => mean(m.reac) },
    { id: "false", label: "False-lock rate %", better: "low", pick: (m) => pct(m.falseLock) },
  ];

  const table = rows.map((row) => {
    const cells = {};
    for (const id of algoIds) cells[id] = row.pick(metrics[id]);
    return { ...row, cells };
  });

  return {
    table,
    envelope: Object.fromEntries(algoIds.map((id) => [id, metrics[id].envelope])),
    failures: metrics.OURS ? metrics.OURS.failures.slice(0, 12) : [],
  };
}
