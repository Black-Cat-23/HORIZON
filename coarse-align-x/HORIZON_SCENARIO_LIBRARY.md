# HORIZON Scenario Library Specification

## 1. Scenario Architecture Overview

The HORIZON Mission framework supports 13 predefined and custom operational scenarios. Every scenario is backed by a deterministic, strongly-typed `AppConfig` instance, providing reproducible simulation parameters across trajectory kinematics, sensor disturbances, optical target characteristics, and solver seeds.

---

## 2. Comprehensive Scenario Registry

| Scenario ID | Name | Difficulty | Motion Pattern | Disturbance Preset | Objective & Backend Configuration |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `nominal_acq` | Nominal acquisition | Nominal | Figure-8 (`amp=(220,140)`, `w=0.6`) | `NOMINAL` | Verify baseline optical acquisition and lock-on under zero environmental disturbance. |
| `straight` | Straight track | Nominal | Straight (`vx=120`, `vy=40`) | `NOMINAL` | Verify constant-velocity linear trajectory estimation and dual-axis gimbal tracking. |
| `circular` | Circular track | Nominal | Circular (`radius=150`, `w=0.6`) | `NOMINAL` | Verify centripetal acceleration tracking and gimbal phase lag response. |
| `figure8` | Figure-8 track | Moderate | Figure-8 (`amp=(220,140)`, `w=0.6`) | `NOMINAL` | Verify dual-axis harmonic motion tracking across zero-velocity inflection points. |
| `random` | Random track | Moderate | Stochastic Random Walk | `NOMINAL` | Verify stochastic maneuvering target tracking and Adaptive Extended Kalman Filter (AEKF) process noise update. |
| `low_light` | Low light | Moderate | Figure-8 (`amp=(220,140)`, `w=0.6`) | `RECOVERY` | Evaluate optical beacon detection under severe photon attenuation and high sensor shot noise (`intensity=120`). |
| `fog_haze` | Fog / haze | Moderate | Figure-8 (`amp=(220,140)`, `w=0.6`) | `DIFFICULT` | Test contrast attenuation, Mie scattering, and Gaussian blurring on neural bounding box detection. |
| `jitter` | Camera jitter | Moderate | Straight (`vx=120`, `vy=40`) | `DIFFICULT` | Measure high-frequency angular sensor jitter rejection via feedforward gyro integration. |
| `platform_motion` | Platform motion | Severe | Circular (`radius=150`, `w=0.6`) | `SEVERE` | Test moving vehicle/vessel mount dynamics and platform velocity disturbance cancellation. |
| `multi_distractor` | Multi-distractor | Severe | Figure-8 (`amp=(220,140)`, `w=0.6`) | `SEVERE` | Verify visual clutter rejection and target data association under multiple optical false alarms. |
| `recovery` | Disturbance recovery | Severe | Figure-8 (`amp=(220,140)`, `w=0.6`) | `RECOVERY` | Validate PAT state machine lifecycle (`TRACK` -> `DEGRADED` -> `REACQUIRE` -> `TRACK`) during forced target blackout. |
| `severe_combined` | Severe combined | Adversarial | Figure-8 (`amp=(220,140)`, `w=0.6`) | `ADVERSARIAL` | Stress test full system under simultaneous maximum noise, optical blur, platform motion, and angular jitter. |
| `custom` | Custom | Custom | User Selected | User Defined | User-configured experimental parameter set spanning all trajectory equations and disturbance models. |

---

## 3. Backend Configuration Data Mapping (`AppConfig`)

Each scenario directly sets parameters inside the unified backend configuration structure (`simulator/core/config.py`):

```yaml
trajectory:
  type: "figure8" | "circular" | "straight" | "sinusoidal" | "spiral" | "random"
  figure8:
    amplitude_x: 220.0
    amplitude_y: 140.0
    angular_velocity: 0.6
  circular:
    radius: 150.0
    angular_velocity: 0.6
  straight:
    velocity_x: 120.0
    velocity_y: 40.0

disturbance:
  preset: "NOMINAL" | "DIFFICULT" | "SEVERE" | "RECOVERY" | "ADVERSARIAL"
  sensor_noise_sigma: float
  blur_kernel_size: int
  jitter_amplitude_rad: float
  platform_motion_amplitude: float

simulation:
  frequency_hz: 30.0
  duration_seconds: 30.0
  seed: 42

target:
  size_px: 10
  intensity: 255
```

---

## 4. Trajectory Preview Geometry Generation

The preview trajectory displayed on the Mission Screen (`ExperimentPreviewWidget`) is mathematically evaluated in real-time from `ScenarioDefinition.generate_preview_path()`:

- **Straight**: \(x(t) = x_0 + v_x t, \quad y(t) = y_0 + v_y t\)
- **Circular**: \(x(t) = c_x + R \cos(\omega t), \quad y(t) = c_y + R \sin(\omega t)\)
- **Figure-8**: \(x(t) = c_x + A_x \sin(\omega t), \quad y(t) = c_y + A_y \sin(2\omega t)\)
- **Sinusoidal**: \(x(t) = x_0 + v_x t, \quad y(t) = y_0 + A \sin(\omega t)\)
- **Spiral**: \(x(t) = c_x + (R_0 + k t) \cos(\omega t), \quad y(t) = c_y + (R_0 + k t) \sin(\omega t)\)
