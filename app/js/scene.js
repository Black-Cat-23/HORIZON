import * as THREE from "three";
import { store } from "./store.js";

const worlds = new Map();

// Color Tokens
const VOID_COLOR = 0x070912;
const FIELD_COLOR = 0x141a30;
const CYAN_COLOR = 0x7fd4e8;
const GREEN_COLOR = 0x6fe8a8;
const AMBER_COLOR = 0xe8a15c;
const RED_COLOR = 0xe86f7f;

function makeWorld(host) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(VOID_COLOR);
  scene.fog = new THREE.FogExp2(VOID_COLOR, 0.015);

  const camera = new THREE.PerspectiveCamera(store.config.fov, 1, 0.1, 300);
  camera.position.set(-3.2, 2.2, 7.5);
  camera.lookAt(new THREE.Vector3(0.5, 0.8, -1.0));

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  host.appendChild(renderer.domElement);

  // Lighting
  const ambient = new THREE.AmbientLight(0x7fd4e8, 0.22);
  scene.add(ambient);

  const keyLight = new THREE.DirectionalLight(0xdce5f5, 0.95);
  keyLight.position.set(6, 12, 8);
  scene.add(keyLight);

  const fillLight = new THREE.DirectionalLight(0x405075, 0.4);
  fillLight.position.set(-6, -2, -4);
  scene.add(fillLight);

  // Precision Datum Reference Floor
  const gridGroup = new THREE.Group();
  const majorGrid = new THREE.GridHelper(36, 18, 0x7fd4e8, 0x1c2748);
  majorGrid.position.y = -0.01;
  gridGroup.add(majorGrid);

  // Concentric Range Rings on Floor
  for (let r = 5; r <= 25; r += 5) {
    const ringGeo = new THREE.RingGeometry(r - 0.03, r + 0.03, 64);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x7fd4e8, transparent: true, opacity: 0.12, side: THREE.DoubleSide });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.rotation.x = Math.PI / 2;
    ring.position.y = 0.005;
    gridGroup.add(ring);
  }
  scene.add(gridGroup);

  // --- 1. Observer Platform & 2-Axis Tracking Gimbal Turret ---
  const gimbalRoot = new THREE.Group();
  gimbalRoot.position.set(-2.2, 0.0, 0);

  // Stator Base
  const baseGeo = new THREE.CylinderGeometry(0.5, 0.55, 0.16, 32);
  const baseMat = new THREE.MeshStandardMaterial({ color: 0x161c2e, metalness: 0.85, roughness: 0.35 });
  const stator = new THREE.Mesh(baseGeo, baseMat);
  stator.position.y = 0.08;
  gimbalRoot.add(stator);

  // Azimuth Rotating Yoke
  const azimuthYoke = new THREE.Group();
  azimuthYoke.position.set(0, 0.16, 0);
  gimbalRoot.add(azimuthYoke);

  const yokeCrossGeo = new THREE.BoxGeometry(0.72, 0.09, 0.3);
  const yokeMat = new THREE.MeshStandardMaterial({ color: 0x0f1424, metalness: 0.9, roughness: 0.25 });
  const yokeCross = new THREE.Mesh(yokeCrossGeo, yokeMat);
  yokeCross.position.y = 0.045;
  azimuthYoke.add(yokeCross);

  const leftArmGeo = new THREE.BoxGeometry(0.09, 0.6, 0.24);
  const leftArm = new THREE.Mesh(leftArmGeo, yokeMat);
  leftArm.position.set(-0.315, 0.34, 0);
  azimuthYoke.add(leftArm);

  const rightArm = leftArm.clone();
  rightArm.position.x = 0.315;
  azimuthYoke.add(rightArm);

  // Elevation Cradle & Optical Telescope
  const elevationCradle = new THREE.Group();
  elevationCradle.position.set(0, 0.55, 0);
  azimuthYoke.add(elevationCradle);

  const barrelGeo = new THREE.CylinderGeometry(0.2, 0.22, 0.75, 32);
  const barrelMat = new THREE.MeshStandardMaterial({ color: 0x182038, metalness: 0.8, roughness: 0.3 });
  const barrel = new THREE.Mesh(barrelGeo, barrelMat);
  barrel.rotation.x = Math.PI / 2;
  elevationCradle.add(barrel);

  const baffleGeo = new THREE.CylinderGeometry(0.24, 0.22, 0.18, 32);
  const baffleMat = new THREE.MeshStandardMaterial({ color: 0x0e1322, metalness: 0.95, roughness: 0.2 });
  const baffle = new THREE.Mesh(baffleGeo, baffleMat);
  baffle.rotation.x = Math.PI / 2;
  baffle.position.z = -0.42;
  elevationCradle.add(baffle);

  // Coated Objective Lens
  const lensGeo = new THREE.CylinderGeometry(0.19, 0.19, 0.02, 32);
  const lensMat = new THREE.MeshStandardMaterial({
    color: 0x7fd4e8,
    emissive: 0x7fd4e8,
    emissiveIntensity: 0.35,
    metalness: 0.95,
    roughness: 0.05,
    transparent: true,
    opacity: 0.88,
  });
  const lens = new THREE.Mesh(lensGeo, lensMat);
  lens.rotation.x = Math.PI / 2;
  lens.position.z = -0.44;
  elevationCradle.add(lens);

  scene.add(gimbalRoot);

  // --- 2. Mobile Target Platform with Beacon ---
  const targetGroup = new THREE.Group();

  const busGeo = new THREE.CylinderGeometry(0.32, 0.32, 0.26, 6);
  const busMat = new THREE.MeshStandardMaterial({ color: 0x222a42, metalness: 0.7, roughness: 0.4 });
  const targetBus = new THREE.Mesh(busGeo, busMat);
  targetGroup.add(targetBus);

  const panelGeo = new THREE.BoxGeometry(0.65, 0.02, 0.32);
  const panelMat = new THREE.MeshStandardMaterial({ color: 0x09101f, metalness: 0.95, roughness: 0.1 });
  const leftWing = new THREE.Mesh(panelGeo, panelMat);
  leftWing.position.x = -0.58;
  targetGroup.add(leftWing);

  const rightWing = leftWing.clone();
  rightWing.position.x = 0.58;
  targetGroup.add(rightWing);

  // Beacon Core & Airy Diffraction Rings
  const beaconCoreGeo = new THREE.SphereGeometry(0.09, 24, 24);
  const beaconCoreMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const beaconCore = new THREE.Mesh(beaconCoreGeo, beaconCoreMat);
  beaconCore.position.set(0, 0.18, 0);
  targetGroup.add(beaconCore);

  const beaconHaloGeo = new THREE.RingGeometry(0.12, 0.36, 32);
  const beaconHaloMat = new THREE.MeshBasicMaterial({
    color: CYAN_COLOR,
    transparent: true,
    opacity: 0.75,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
  });
  const beaconHalo = new THREE.Mesh(beaconHaloGeo, beaconHaloMat);
  beaconHalo.position.copy(beaconCore.position);
  targetGroup.add(beaconHalo);

  scene.add(targetGroup);

  // --- 3. Dynamic Viewing Frustum Volume ---
  const frustumGeo = new THREE.BufferGeometry();
  const frustumMat = new THREE.MeshBasicMaterial({
    color: CYAN_COLOR,
    transparent: true,
    opacity: 0.12,
    wireframe: true,
  });
  const frustumMesh = new THREE.Mesh(frustumGeo, frustumMat);
  elevationCradle.add(frustumMesh);

  // --- 4. Line-of-Sight Laser Alignment Beam ---
  const losPoints = [new THREE.Vector3(), new THREE.Vector3()];
  const losGeo = new THREE.BufferGeometry().setFromPoints(losPoints);
  const losMat = new THREE.LineBasicMaterial({
    color: CYAN_COLOR,
    transparent: true,
    opacity: 0.85,
    linewidth: 2,
    blending: THREE.AdditiveBlending,
  });
  const losLine = new THREE.Line(losGeo, losMat);
  scene.add(losLine);

  return {
    host,
    scene,
    camera,
    renderer,
    gimbalRoot,
    azimuthYoke,
    elevationCradle,
    lens,
    targetGroup,
    beaconCore,
    beaconHalo,
    frustumMesh,
    losLine,
    losMat,
  };
}

export function attachWorld(id, host) {
  worlds.set(id, makeWorld(host));
  resize();
}

export function resize() {
  for (const w of worlds.values()) {
    const { host, camera, renderer } = w;
    const r = host.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    camera.aspect = r.width / r.height;
    camera.fov = store.config.fov;
    camera.updateProjectionMatrix();
    renderer.setSize(r.width, r.height, false);
  }
}

export function renderWorlds() {
  const t = store.simTime;
  const d = store.disturb;
  const conf = store.confidence;

  // Target coordinates in 3D world space
  const tx = store.truth.tx * 0.15 + 1.2;
  const ty = 0.8 + store.truth.ty * 0.15;
  const tz = -4.5;

  // Target platform position
  const targetWorldPos = new THREE.Vector3(tx, ty, tz);

  for (const w of worlds.values()) {
    // 1. Update Target Platform
    w.targetGroup.position.copy(targetWorldPos);
    w.beaconHalo.lookAt(w.camera.position);

    // Scintillation & Occlusion
    const isOccluded = d.occlusion > 0.05 && (t % 4.0) < d.occlusion * 1.6;
    const scintAlpha = isOccluded ? 0.0 : Math.max(0.15, (1.0 - d.intensity * 0.75) * (0.4 + conf * 0.6));
    w.beaconHalo.material.opacity = scintAlpha;
    w.beaconCore.material.color.setRGB(scintAlpha, scintAlpha, scintAlpha);

    // 2. Gimbal Turret Tracking (Azimuth and Elevation)
    const gimbalWorldPos = new THREE.Vector3();
    w.elevationCradle.getWorldPosition(gimbalWorldPos);

    const relVec = new THREE.Vector3().subVectors(targetWorldPos, gimbalWorldPos);
    const targetAzimuth = Math.atan2(relVec.x, -relVec.z);
    const horizDist = Math.hypot(relVec.x, relVec.z);
    const targetElevation = Math.atan2(relVec.y, horizDist);

    // Damped gimbal motion matching actuator limits
    w.azimuthYoke.rotation.y += (targetAzimuth - w.azimuthYoke.rotation.y) * 0.12;
    w.elevationCradle.rotation.x += (-targetElevation - w.elevationCradle.rotation.x) * 0.12;

    // Platform vibration perturbation
    if (d.vibration > 0.01) {
      const vib = Math.sin(t * 45) * d.vibration * 0.02;
      w.elevationCradle.rotation.x += vib;
      w.azimuthYoke.rotation.y += vib * 0.7;
    }

    // 3. Dynamic Viewing Frustum Update
    const fovRad = (store.config.fov * 0.5 * Math.PI) / 180;
    const aspect = w.camera.aspect;
    const dist = 5.5;
    const halfH = Math.tan(fovRad) * dist;
    const halfW = halfH * aspect;

    const fVerts = new Float32Array([
      0, 0, 0,  -halfW,  halfH, -dist,
      0, 0, 0,   halfW,  halfH, -dist,
      0, 0, 0,   halfW, -halfH, -dist,
      0, 0, 0,  -halfW, -halfH, -dist,
      -halfW,  halfH, -dist,   halfW,  halfH, -dist,
       halfW,  halfH, -dist,   halfW, -halfH, -dist,
       halfW, -halfH, -dist,  -halfW, -halfH, -dist,
      -halfW, -halfH, -dist,  -halfW,  halfH, -dist,
    ]);
    w.frustumMesh.geometry.setAttribute("position", new THREE.BufferAttribute(fVerts, 3));

    // 4. Line-of-Sight Laser Vector
    const lensWorldPos = new THREE.Vector3();
    w.lens.getWorldPosition(lensWorldPos);

    const losVerts = new Float32Array([
      lensWorldPos.x, lensWorldPos.y, lensWorldPos.z,
      targetWorldPos.x, targetWorldPos.y + 0.18, targetWorldPos.z,
    ]);
    w.losLine.geometry.setAttribute("position", new THREE.BufferAttribute(losVerts, 3));

    // Semantic State Color for LOS Beam
    let beamColor = CYAN_COLOR;
    if (store.mode === "TRACK") beamColor = GREEN_COLOR;
    else if (store.mode === "DEGRADED") beamColor = AMBER_COLOR;
    else if (store.mode === "REACQUIRE") beamColor = RED_COLOR;

    w.losMat.color.setHex(beamColor);
    w.losMat.opacity = isOccluded ? 0.1 : 0.8;

    // 5. Camera Vibration Shake & Motion Blur Filter
    w.camera.position.x = -3.2 + (Math.sin(t * 30) * d.vibration * 0.08);
    w.camera.position.y = 2.2 + (Math.cos(t * 22) * d.vibration * 0.05);

    const blur = d.motionBlur;
    w.renderer.domElement.style.filter = blur > 0.02 ? `blur(${blur * 2.8}px)` : "none";

    w.renderer.render(w.scene, w.camera);
  }
}

window.addEventListener("resize", resize);
