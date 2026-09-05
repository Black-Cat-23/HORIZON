# Phase 6 — Camera Gimbal Control & Actuator Model Specification

## 1. Control Equations
The camera pan and tilt axes are controlled by independent PID loops with anti-windup clamping, low-pass derivative filtering, velocity feed-forward, and rate saturation.

### Pointing Error Conversion
For camera frame resolution $W \times H = 640 \times 480\text{ px}$ and optical FOV $\Theta_{\text{pan}} \times \Theta_{\text{tilt}} = 4.0^\circ \times 3.0^\circ$:
$$e_{\text{pan}} = \frac{\hat{u} - 320}{640} \times 4.0^\circ, \quad e_{\text{tilt}} = \frac{\hat{v} - 240}{480} \times 3.0^\circ$$

### Discrete PID Control Law
$$u_{\text{PID}}(t_k) = K_p \cdot e(t_k) + K_i \sum_{i=0}^k e(t_i) \Delta t + K_d \cdot D(t_k)$$

where derivative $D(t_k)$ is filtered via a first-order low-pass filter ($\tau_d = 0.02\text{ s}$):
$$\alpha = \frac{\Delta t}{\Delta t + \tau_d}, \quad D(t_k) = (1 - \alpha) D(t_{k-1}) + \alpha \frac{e(t_k) - e(t_{k-1})}{\Delta t}$$

### Anti-Windup Clamping
$$I(t_k) = \text{clamp}\left(I(t_{k-1}) + e(t_k) \Delta t, -I_{\max}, I_{\max}\right), \quad I_{\max} = 2.0^\circ$$

### Velocity Feed-Forward
$$u_{\text{FF}}(t_k) = K_{\text{FF}} \cdot \hat{\omega}_{\text{target}}(t_k)$$

### Gimbal Actuator Rate Limits
$$u_{\text{actual}} = \text{clamp}\left(u_{\text{PID}} + u_{\text{FF}}, -5.0^\circ/\text{s}, +5.0^\circ/\text{s}\right)$$

```
Pointing Error e(t) ───► [ Kp ] ───────┐
                       ► [ Ki / s ] ───┼──► ( + ) ───► [ Clamping Saturation ] ───► Gimbal Command (u)
                       ► [ Kd * s ] ───┘
```
