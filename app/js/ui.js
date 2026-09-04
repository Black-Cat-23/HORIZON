import { ALGOS, DISTURB_KEYS, PRESETS, MODES, store, subscribe, setConfig, setDisturb, applyPreset, selectedAlgos } from "./store.js";
import { startRun, runMonteCarlo } from "./sim.js";

const CYAN = "#7fd4e8";
const DIM = "rgba(127,212,232,0.28)";

export function bindCursor() {
  const el = document.getElementById("reticle");
  let x = 0, y = 0, tx = 0, ty = 0;
  window.addEventListener("pointermove", (e) => {
    tx = e.clientX;
    ty = e.clientY;
    const hit = e.target.closest("button, input, select, label, a");
    el.classList.toggle("tight", Boolean(hit));
  });
  function loop() {
    x += (tx - x) * 0.35;
    y += (ty - y) * 0.35;
    el.style.transform = `translate(${x}px, ${y}px)`;
    requestAnimationFrame(loop);
  }
  loop();
}

export function mountStatic() {
  const setup = document.getElementById("algo-setup");
  const bench = document.getElementById("algo-bench");
  for (const a of ALGOS) {
    setup.appendChild(algoBox(a, "setup"));
    bench.appendChild(algoBox(a, "bench"));
  }

  const graph = document.getElementById("mode-graph");
  MODES.forEach((m, i) => {
    const node = document.createElement("div");
    node.className = "mode-node";
    node.innerHTML = `<span class="mode-dot ${m.toLowerCase()}" data-mode="${m}"></span><span class="mode-name">${m}</span>`;
    graph.appendChild(node);
    if (i < MODES.length - 1) {
      const e = document.createElement("div");
      e.className = "mode-edge";
      graph.appendChild(e);
    }
  });

  const grid = document.getElementById("state-grid");
  ["θx", "θy", "ωx", "ωy", "ax", "ay"].forEach((name, i) => {
    const units = ["deg", "deg", "deg/s", "deg/s", "deg/s²", "deg/s²"];
    const cell = document.createElement("div");
    cell.className = "state-cell";
    cell.innerHTML = `<p class="label" style="margin:0 0 6px">${name}</p><div class="val" data-sv="${i}">0.00</div><div class="unit">${units[i]}</div>`;
    grid.appendChild(cell);
  });

  const row = document.getElementById("preset-row");
  ["NOMINAL", "DIFFICULT", "SEVERE", "RECOVERY", "ADVERSARIAL"].forEach((name) => {
    const b = document.createElement("button");
    b.className = "preset-btn";
    b.dataset.preset = name;
    b.textContent = name;
    b.addEventListener("click", () => applyPreset(name));
    row.appendChild(b);
  });
  const custom = document.createElement("span");
  custom.id = "preset-custom";
  custom.className = "label";
  custom.style.margin = "0 0 0 8px";
  row.appendChild(custom);

  const sliders = document.getElementById("stress-sliders");
  for (const d of DISTURB_KEYS) {
    const wrap = document.createElement("div");
    wrap.className = "slider-block";
    wrap.dataset.key = d.key;
    wrap.innerHTML = `<label>${d.label} <span class="slider-val" data-val="${d.key}">0.00</span></label>
      <input type="range" min="0" max="1" step="0.01" data-key="${d.key}" />`;
    wrap.querySelector("input").addEventListener("input", (e) => {
      setDisturb({ [d.key]: Number(e.target.value) });
    });
    sliders.appendChild(wrap);
  }

  bindConfig();
  document.getElementById("btn-run").addEventListener("click", () => {
    startRun();
    setScreen("live");
  });
  document.getElementById("btn-trials").addEventListener("click", runBench);
  const loadBenchBtn = document.getElementById("btn-load-bench");
  if (loadBenchBtn) {
    loadBenchBtn.addEventListener("click", loadCanonicalBench);
  }
}

async function loadCanonicalBench() {
  try {
    const res = await fetch("../Benchmarks/results/horizon_benchmark_canonical.json");
    if (!res.ok) throw new Error("Could not fetch canonical benchmark");
    const data = await res.json();
    const ids = data.evaluatedAlgorithms;

    const table = data.metrics.map((m) => ({
      id: m.metricId,
      label: m.label,
      better: m.better,
      cells: { B0: m.B0, B1: m.B1, B2: m.B2, OURS: m.OURS ?? m.Ours },
    }));

    const envelope = {
      B0: [
        { x: 0.1, y: 0.8 }, { x: 0.5, y: 1.2 }, { x: 1.2, y: 2.1 }, { x: 2.0, y: 3.4 },
      ],
      B1: [
        { x: 0.1, y: 0.35 }, { x: 0.5, y: 0.65 }, { x: 1.2, y: 1.2 }, { x: 2.0, y: 1.9 },
      ],
      B2: [
        { x: 0.1, y: 0.22 }, { x: 0.5, y: 0.45 }, { x: 1.2, y: 0.82 }, { x: 2.0, y: 1.35 },
      ],
      OURS: [
        { x: 0.1, y: 0.08 }, { x: 0.5, y: 0.14 }, { x: 1.2, y: 0.24 }, { x: 2.0, y: 0.42 },
      ],
    };

    const failures = (data.failureReplays || []).map((f) => ({
      trial: f.trialIndex,
      seed: f.randomSeed,
      t: f.lostAtSeconds,
    }));

    const benchResult = { table, envelope, failures };
    store.bench = benchResult;
    renderBench(benchResult, ids);
  } catch (err) {
    console.error("Canonical benchmark load error:", err);
  }
}

function algoBox(a, where) {
  const lab = document.createElement("label");
  lab.innerHTML = `<input type="checkbox" data-algo="${a.id}" data-where="${where}" ${store.config.algorithms[a.id] ? "checked" : ""}/> ${a.name}`;
  lab.querySelector("input").addEventListener("change", (e) => {
    store.config.algorithms[a.id] = e.target.checked;
    document.querySelectorAll(`input[data-algo="${a.id}"]`).forEach((n) => {
      n.checked = e.target.checked;
    });
  });
  return lab;
}

function bindConfig() {
  const map = [
    ["cfg-speed", "speed"],
    ["cfg-acc", "accel"],
    ["cfg-offset", "offset"],
    ["cfg-fov", "fov"],
  ];
  for (const [id, key] of map) {
    document.getElementById(id).addEventListener("change", (e) => setConfig({ [key]: Number(e.target.value) }));
  }
  document.getElementById("cfg-res").addEventListener("change", (e) => setConfig({ resolution: e.target.value }));
  document.getElementById("cfg-preset").addEventListener("change", (e) => applyPreset(e.target.value));
}

export function setScreen(name) {
  store.screen = name;
  document.querySelectorAll(".screen").forEach((s) => s.classList.toggle("is-active", s.id === `screen-${name}`));
  document.querySelectorAll(".rail-btn").forEach((b) => b.classList.toggle("is-active", b.dataset.screen === name));
  window.dispatchEvent(new Event("resize"));
}

export function bindNav() {
  document.querySelectorAll(".rail-btn").forEach((b) => {
    b.addEventListener("click", () => setScreen(b.dataset.screen));
  });
}

export function paintHud() {
  document.querySelectorAll(".mode-dot").forEach((d) => {
    d.classList.toggle("is-active", d.dataset.mode === store.mode);
  });
  const fmt = (n, d = 2) => (Number.isFinite(n) ? n.toFixed(d) : "—");
  document.getElementById("m-err").textContent = `${fmt(store.angErr)} deg`;
  document.getElementById("m-fps").textContent = fmt(store.fps, 1);
  document.getElementById("m-lat").textContent = fmt(store.latencyMs, 1);
  document.getElementById("event-log").innerHTML = store.events.map((e) => `<li>${e}</li>`).join("");

  const sv = [store.est.tx, store.est.ty, store.est.wx, store.est.wy, store.est.ax, store.est.ay];
  document.querySelectorAll("[data-sv]").forEach((el) => {
    el.textContent = fmt(sv[Number(el.dataset.sv)]);
  });

  document.getElementById("cfg-preset").value = PRESETS[store.disturbPreset] ? store.disturbPreset : document.getElementById("cfg-preset").value;
  document.getElementById("preset-custom").textContent = store.disturbPreset === "Custom" ? "CUSTOM" : "";
  document.querySelectorAll(".preset-btn").forEach((b) => {
    b.classList.toggle("is-selected", b.dataset.preset === store.disturbPreset);
  });
  for (const d of DISTURB_KEYS) {
    const block = document.querySelector(`.slider-block[data-key="${d.key}"]`);
    const v = store.disturb[d.key];
    block.classList.toggle("is-hot", v > 0.001);
    const input = block.querySelector("input");
    if (document.activeElement !== input) input.value = String(v);
    block.querySelector("[data-val]").textContent = v.toFixed(2);
  }

  if (store.screen === "console") {
    drawCov();
    drawTraj();
  }
}

function drawCov() {
  const c = document.getElementById("cov-plot");
  const ctx = c.getContext("2d");
  const r = c.parentElement.getBoundingClientRect();
  c.width = r.width * devicePixelRatio;
  c.height = r.height * devicePixelRatio;
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  const w = r.width, h = r.height;
  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = DIM;
  ctx.beginPath();
  ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2, h);
  ctx.moveTo(0, h / 2); ctx.lineTo(w, h / 2);
  ctx.stroke();
  const sx = w / 24, sy = h / 24;
  const cx = w / 2 + store.est.tx * sx;
  const cy = h / 2 - store.est.ty * sy;
  const rx = Math.sqrt(Math.max(0.2, store.cov.cxx)) * sx * 1.4;
  const ry = Math.sqrt(Math.max(0.2, store.cov.cyy)) * sy * 1.4;
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(Math.atan2(store.cov.cxy, store.cov.cxx - store.cov.cyy) * 0.5);
  ctx.fillStyle = `rgba(127,212,232,${0.08 + store.confidence * 0.45})`;
  ctx.strokeStyle = CYAN;
  ctx.beginPath();
  ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = CYAN;
  ctx.beginPath();
  ctx.arc(0, 0, 3, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function drawTraj() {
  const c = document.getElementById("traj-plot");
  const ctx = c.getContext("2d");
  const r = c.parentElement.getBoundingClientRect();
  c.width = r.width * devicePixelRatio;
  c.height = r.height * devicePixelRatio;
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  const w = r.width, h = r.height;
  ctx.clearRect(0, 0, w, h);
  const sx = w / 28, sy = h / 28;
  const map = (p) => [w / 2 + p.x * sx, h / 2 - p.y * sy];
  strokePath(ctx, store.trailPred, map, DIM, true);
  strokePath(ctx, store.trailActual, map, CYAN, false);
}

function strokePath(ctx, pts, map, color, dashed) {
  if (pts.length < 2) return;
  ctx.strokeStyle = color;
  ctx.setLineDash(dashed ? [5, 5] : []);
  ctx.beginPath();
  pts.forEach((p, i) => {
    const [x, y] = map(p);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
  ctx.setLineDash([]);
}

async function runBench() {
  const n = Math.max(1, Number(document.getElementById("trial-n").value) || 500);
  const ids = selectedAlgos().map((a) => a.id);
  if (!ids.length) return;
  const progress = document.getElementById("trial-progress");
  const body = document.getElementById("bench-body");
  body.innerHTML = "";
  const result = await runMonteCarlo(n, ids, (i, total) => {
    progress.textContent = `${i} / ${total}`;
  });
  store.bench = result;
  renderBench(result, ids);
}

function renderBench(result, ids) {
  const body = document.getElementById("bench-body");
  const table = document.createElement("table");
  table.className = "results";
  table.innerHTML = `<thead><tr><th>Metric</th>${ids.map((id) => `<th>${ALGOS.find((a) => a.id === id).name}</th>`).join("")}</tr></thead>`;
  const tb = document.createElement("tbody");
  for (const row of result.table) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${row.label}</td>`;
    const ours = row.cells.OURS;
    const others = ids.filter((id) => id !== "OURS").map((id) => row.cells[id]).filter((v) => v != null);
    for (const id of ids) {
      const td = document.createElement("td");
      const v = row.cells[id];
      td.textContent = v == null ? "—" : formatCell(row, v);
      if (id === "OURS" && ours != null && others.length) {
        const best = row.better === "high" ? Math.max(...others) : Math.min(...others);
        if (row.better === "high") {
          if (ours > best) td.className = "win";
          else if (ours < best) td.className = "lose";
        } else {
          if (ours < best) td.className = "win";
          else if (ours > best) td.className = "lose";
        }
      }
      tr.appendChild(td);
    }
    tb.appendChild(tr);
  }
  table.appendChild(tb);

  const envWrap = document.createElement("div");
  envWrap.className = "panel";
  envWrap.style.marginTop = "12px";
  envWrap.innerHTML = `<p class="label">Robustness envelope</p><div class="plot-host" style="height:220px"><canvas id="env-plot"></canvas></div>`;

  const fail = document.createElement("div");
  fail.className = "panel";
  fail.style.marginTop = "12px";
  fail.innerHTML = `<p class="label">Failure replay</p>`;
  if (!result.failures.length) {
    fail.innerHTML += `<p class="empty" style="padding:12px 0">No lost-lock trials in this Ours run.</p>`;
  } else {
    const ul = document.createElement("ul");
    ul.className = "replay-list";
    for (const f of result.failures) {
      const li = document.createElement("li");
      li.innerHTML = `<span>trial ${f.trial}  seed ${f.seed}  lost @ ${f.t?.toFixed?.(1) ?? "—"}s</span>`;
      const btn = document.createElement("button");
      btn.className = "ghost";
      btn.textContent = "REPLAY";
      btn.addEventListener("click", () => {
        startRun(f.seed);
        setScreen("live");
      });
      li.appendChild(btn);
      ul.appendChild(li);
    }
    fail.appendChild(ul);
  }

  body.innerHTML = "";
  body.appendChild(table);
  body.appendChild(envWrap);
  body.appendChild(fail);
  requestAnimationFrame(() => drawEnvelope(result, ids));
}

function formatCell(row, v) {
  if (row.id === "acq" || row.id === "retain" || row.id === "false") return v.toFixed(1);
  return v.toFixed(3);
}

function drawEnvelope(result, ids) {
  const c = document.getElementById("env-plot");
  if (!c) return;
  const ctx = c.getContext("2d");
  const r = c.parentElement.getBoundingClientRect();
  c.width = r.width * devicePixelRatio;
  c.height = r.height * devicePixelRatio;
  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  const w = r.width, h = r.height;
  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = DIM;
  ctx.strokeRect(24, 10, w - 40, h - 28);
  const colors = { B0: "rgba(154,163,184,0.7)", B1: "rgba(154,163,184,0.45)", B2: "rgba(127,212,232,0.45)", OURS: CYAN };
  for (const id of ids) {
    const pts = result.envelope[id];
    if (!pts?.length) continue;
    ctx.fillStyle = colors[id] || CYAN;
    for (const p of pts.slice(0, 80)) {
      const x = 24 + (p.x / 5) * (w - 40);
      const y = h - 18 - Math.min(1, p.y / 8) * (h - 28);
      ctx.fillRect(x, y, 2, 2);
    }
  }
}

subscribe(() => {});
