import * as THREE from 'three';

export interface CameraWaypoint {
  progress: number;
  position: THREE.Vector3;
  lookAt: THREE.Vector3;
  fov: number;
}

/**
 * Continuous Earth-to-Space Cinematic Camera Spline:
 * - 0.0: Half-View Earth Curved Horizon with 3D Location Pins
 * - 0.15: Atmospheric Cloud Dive toward Modinagar Ground Station
 * - 0.30: Ground Optical Antenna Gimbal Calibration & Sky Pointing
 * - 0.45: Upward Laser Carrier Beam Fired into Space
 * - 0.65: Ascending along the Beam through Cloud Layers into LEO
 * - 0.85 -> 1.0: Optical Link Lock with Orbiting FSOC Satellite & Telemetry
 */
export const CAMERA_WAYPOINTS: CameraWaypoint[] = [
  // 00 START SCREEN: 40% Curved Earth Horizon with 3D Silk Ribbon Bridge
  {
    progress: 0.0,
    position: new THREE.Vector3(0.0, 9.5, 46.0),
    lookAt: new THREE.Vector3(0.0, 0.0, 0.0),
    fov: 46,
  },
  // 00B HERO EXIT: Camera stays perfectly fixed until past the hero section
  {
    progress: 0.08,
    position: new THREE.Vector3(0.0, 9.5, 46.0),
    lookAt: new THREE.Vector3(0.0, 0.0, 0.0),
    fov: 46,
  },
  // 01 UNKNOWN: Initiating orbital descent toward India (Modinagar / Delhi NCR)
  {
    progress: 0.12,
    position: new THREE.Vector3(3.2, 18.0, 32.0),
    lookAt: new THREE.Vector3(0.0, -2.0, 0.0),
    fov: 44,
  },
  // 02 CAMERA: Diving through the atmospheric cloud layer
  {
    progress: 0.18,
    position: new THREE.Vector3(4.5, 12.0, 16.0),
    lookAt: new THREE.Vector3(0.0, 6.0, 0.0),
    fov: 40,
  },
  // 03 SEARCH: Ground Optical Antenna Gimbal aligning its elevation axis
  {
    progress: 0.28,
    position: new THREE.Vector3(6.5, 8.2, 10.5),
    lookAt: new THREE.Vector3(0.0, 7.2, 0.0),
    fov: 36,
  },
  // 04 ACQUIRE: Optical telescope firing the coherent laser beam into the sky
  {
    progress: 0.38,
    position: new THREE.Vector3(2.2, 6.5, 4.8),
    lookAt: new THREE.Vector3(0.0, 28.0, 0.0),
    fov: 38,
  },
  // 05 TRACK: Camera ascending upward along the laser carrier beam
  {
    progress: 0.48,
    position: new THREE.Vector3(4.8, 18.0, 12.0),
    lookAt: new THREE.Vector3(0.0, 45.0, 0.0),
    fov: 42,
  },
  // 06 DISTURBANCE: Stratospheric turbulence layer with beam scintillation
  {
    progress: 0.58,
    position: new THREE.Vector3(-6.5, 32.0, 18.0),
    lookAt: new THREE.Vector3(0.0, 60.0, 0.0),
    fov: 46,
  },
  // 07 LOSS: Breaking through cloud boundary into deep space vacuum
  {
    progress: 0.68,
    position: new THREE.Vector3(8.5, 42.0, 24.0),
    lookAt: new THREE.Vector3(2.5, 25.0, -15.0),
    fov: 44,
  },
  // 08 REACQUIRE: Approaching the orbiting FSOC satellite terminal
  {
    progress: 0.77,
    position: new THREE.Vector3(5.5, 14.0, 12.0),
    lookAt: new THREE.Vector3(2.5, 1.0, 0.0),
    fov: 36,
  },
  // 09 SYSTEM: High-resolution view of satellite antenna & solar panels
  {
    progress: 0.86,
    position: new THREE.Vector3(-6.5, 6.0, 10.0),
    lookAt: new THREE.Vector3(2.5, 0.5, 0.0),
    fov: 34,
  },
  // 10 PROOF: Optical link confirmed between ground station and orbit
  {
    progress: 0.94,
    position: new THREE.Vector3(3.8, 4.2, 8.5),
    lookAt: new THREE.Vector3(2.0, 0.8, 0.0),
    fov: 32,
  },
  // 11 CLOSING: Symmetrical beauty shot of the satellite in Low Earth Orbit
  {
    progress: 1.0,
    position: new THREE.Vector3(0.0, 3.8, 9.5),
    lookAt: new THREE.Vector3(2.2, 0.5, 0.0),
    fov: 35,
  },
];

export class CameraSplinePath {
  private curve: THREE.CatmullRomCurve3;
  private lookAtCurve: THREE.CatmullRomCurve3;

  constructor() {
    const points = CAMERA_WAYPOINTS.map((w) => w.position);
    const lookAts = CAMERA_WAYPOINTS.map((w) => w.lookAt);

    this.curve = new THREE.CatmullRomCurve3(points, false, 'catmullrom', 0.5);
    this.lookAtCurve = new THREE.CatmullRomCurve3(lookAts, false, 'catmullrom', 0.5);
  }

  public evaluate(progress: number): { position: THREE.Vector3; lookAt: THREE.Vector3; fov: number } {
    const clampedProgress = Math.max(0, Math.min(1, progress));
    const position = this.curve.getPoint(clampedProgress);
    const lookAt = this.lookAtCurve.getPoint(clampedProgress);

    let fov = 42;
    for (let i = 0; i < CAMERA_WAYPOINTS.length - 1; i++) {
      const w0 = CAMERA_WAYPOINTS[i];
      const w1 = CAMERA_WAYPOINTS[i + 1];
      if (clampedProgress >= w0.progress && clampedProgress <= w1.progress) {
        const localT = (clampedProgress - w0.progress) / (w1.progress - w0.progress || 1);
        fov = THREE.MathUtils.lerp(w0.fov, w1.fov, localT);
        break;
      }
    }

    return { position, lookAt, fov };
  }
}

export const cameraSpline = new CameraSplinePath();
