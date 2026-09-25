import React, { useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

interface BeaconTargetProps {
  progress: number;
}

export const BeaconTarget: React.FC<BeaconTargetProps> = ({ progress }) => {
  const beaconRef = useRef<THREE.Group>(null);
  const glowRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (!beaconRef.current) return;
    const t = clock.getElapsedTime();

    // Trajectory computation according to narrative chapter
    let x = 0;
    let y = 2.5;
    let z = -60;

    if (progress < 0.22) {
      // 01 Unknown Signal: Distant static angular offset
      x = 18;
      y = 12;
      z = -70;
    } else if (progress >= 0.22 && progress < 0.42) {
      // 03 Search / 04 Acquire: Target moving along smooth entry vector
      x = THREE.MathUtils.lerp(18, 4, (progress - 0.22) / 0.2);
      y = THREE.MathUtils.lerp(12, 2.5, (progress - 0.22) / 0.2);
      z = THREE.MathUtils.lerp(-70, -55, (progress - 0.22) / 0.2);
    } else if (progress >= 0.42 && progress < 0.62) {
      // 05 Track: Dynamic Figure-8 motion trajectory
      const f8Scale = 6.0;
      x = Math.sin(t * 1.2) * f8Scale;
      y = 2.5 + Math.sin(t * 2.4) * (f8Scale * 0.45);
      z = -55;
    } else if (progress >= 0.62 && progress < 0.72) {
      // 06 Disturbance / 07 Loss: Severe jitter & dropping signal
      const jitter = (Math.random() - 0.5) * 1.8;
      x = Math.sin(t * 1.2) * 6.0 + jitter;
      y = 2.5 + Math.sin(t * 2.4) * 2.7 + jitter;
      z = -55;
    } else if (progress >= 0.72 && progress < 0.85) {
      // 08 Reacquire: Settling back into stable circular orbit
      const radius = 3.5;
      x = Math.cos(t * 1.0) * radius;
      y = 2.5 + Math.sin(t * 1.0) * radius;
      z = -55;
    } else {
      // 09-11 System & Proof & Closing: Stable locked position
      x = Math.cos(t * 0.4) * 1.5;
      y = 2.5 + Math.sin(t * 0.4) * 1.0;
      z = -55;
    }

    beaconRef.current.position.set(x, y, z);

    // Pulsing optical emitter glow
    if (glowRef.current) {
      const scale = 1.0 + Math.sin(t * 6.0) * 0.15;
      glowRef.current.scale.set(scale, scale, scale);
    }
  });

  const isLoss = progress >= 0.63 && progress < 0.72;
  const isDisturbed = progress >= 0.53 && progress < 0.63;
  const isLocked = (progress >= 0.35 && progress < 0.53) || progress >= 0.75;

  const beaconColor = isLoss
    ? '#e86f7f'
    : isDisturbed
    ? '#e8a15c'
    : isLocked
    ? '#6fe8a8'
    : '#a9d8e8';

  return (
    <group ref={beaconRef} position={[0, 2.5, -60]}>
      {/* Central Core Spot */}
      <mesh>
        <sphereGeometry args={[0.35, 32, 32]} />
        <meshBasicMaterial color={beaconColor} />
      </mesh>

      {/* Atmospheric Halo Glow */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[0.85, 24, 24]} />
        <meshBasicMaterial
          color={beaconColor}
          transparent
          opacity={isLoss ? 0.1 : 0.35}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Optical Point Light */}
      <pointLight
        color={beaconColor}
        intensity={isLoss ? 0.5 : 3.5}
        distance={25}
        decay={2}
      />
    </group>
  );
};
