import React, { useMemo, useRef } from 'react';
import * as THREE from 'three';
import { useFrame } from '@react-three/fiber';

// Custom GLSL Shader for Photorealistic Deep-Space Astronomical Starfield
const AstronomicalStarShader = {
  vertexShader: `
    attribute float aScale;
    attribute float aAlpha;
    attribute float aTwinkleSpeed;
    attribute float aTwinklePhase;
    attribute vec3 aColor;
    
    uniform float uTime;
    
    varying float vAlpha;
    varying vec3 vColor;
    
    void main() {
      vColor = aColor;
      
      // Natural organic dual-wave scintillation
      float wave1 = sin(uTime * aTwinkleSpeed * 0.45 + aTwinklePhase);
      float wave2 = cos(uTime * aTwinkleSpeed * 0.85 + aTwinklePhase * 1.6);
      float organicMod = 0.5 + 0.35 * wave1 + 0.15 * wave2;
      
      // Radiant breathing: 80% baseline luminance + 20% shimmering glint
      float twinkle = 0.80 + 0.20 * organicMod;
      vAlpha = aAlpha * twinkle;
      
      vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
      
      // Astronomical sub-pixel point sizing (1.0px - 3.2px)
      float size = aScale * (0.85 + 0.35 * organicMod) * (85.0 / -mvPosition.z);
      gl_PointSize = clamp(size, 1.0, 3.2);
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  fragmentShader: `
    varying float vAlpha;
    varying vec3 vColor;
    
    void main() {
      vec2 coord = gl_PointCoord - vec2(0.5);
      float dist = length(coord);
      if (dist > 0.5) discard;
      
      // Photorealistic Gaussian stellar core + radiant corona
      float core = exp(-dist * dist * 32.0);
      float halo = smoothstep(0.5, 0.0, dist) * 0.35;
      
      vec3 finalColor = vColor * (core + halo);
      gl_FragColor = vec4(finalColor, (core + halo) * vAlpha * 0.95);
    }
  `,
};

// Shader for Dynamic Fluid Shooting Star Meteors
const ShootingStarTrailShader = {
  vertexShader: `
    attribute float aTrailProgress;
    attribute float aAlpha;
    varying float vTrailProgress;
    varying float vAlpha;
    
    void main() {
      vTrailProgress = aTrailProgress;
      vAlpha = aAlpha;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    varying float vTrailProgress;
    varying float vAlpha;
    
    void main() {
      float intensity = pow(vTrailProgress, 2.8);
      vec3 headColor = vec3(1.0, 1.0, 1.0);
      vec3 trailColor = vec3(0.55, 0.85, 1.0);
      vec3 col = mix(trailColor, headColor, pow(vTrailProgress, 4.0));
      
      gl_FragColor = vec4(col, intensity * vAlpha * 0.95);
    }
  `,
};

interface ActiveMeteor {
  origin: THREE.Vector3;
  dir: THREE.Vector3;
  speed: number;
  length: number;
  progress: number;
  maxDistance: number;
  active: boolean;
  delay: number;
  alpha: number;
}

export const ParticleStarfield: React.FC = () => {
  const pointsRef = useRef<THREE.Points>(null);
  const starMaterialRef = useRef<THREE.ShaderMaterial>(null);

  // 1. Deep Space Starfield (5500 Brilliant Pinpoint Stars across the Celestial Dome)
  const [positions, scales, alphas, speeds, phases, colors] = useMemo(() => {
    const count = 5500;
    const pos = new Float32Array(count * 3);
    const sc = new Float32Array(count);
    const al = new Float32Array(count);
    const sp = new Float32Array(count);
    const ph = new Float32Array(count);
    const col = new Float32Array(count * 3);

    const spectralColors = [
      new THREE.Color('#ffffff'), // Pure Brilliant Diamond White (40%)
      new THREE.Color('#dbeafe'), // Icy Radiant Blue (35%)
      new THREE.Color('#93c5fd'), // Azure Celestial Blue (15%)
      new THREE.Color('#fef3c7'), // Warm Stellar Yellow (10%)
    ];

    for (let i = 0; i < count; i++) {
      const radius = 30 + Math.random() * 240;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);

      pos[i * 3 + 0] = radius * Math.sin(phi) * Math.cos(theta);
      pos[i * 3 + 1] = Math.abs(radius * Math.cos(phi)) * 0.95 - 4; // High celestial dome
      pos[i * 3 + 2] = -35 + radius * Math.sin(phi) * Math.sin(theta);

      const magnitude = Math.pow(Math.random(), 2.8);
      sc[i] = 1.0 + magnitude * 2.5;
      al[i] = 0.45 + Math.random() * 0.55;
      sp[i] = 1.0 + Math.random() * 4.0;
      ph[i] = Math.random() * Math.PI * 2;

      const starColor = spectralColors[Math.floor(Math.random() * spectralColors.length)];
      col[i * 3 + 0] = starColor.r;
      col[i * 3 + 1] = starColor.g;
      col[i * 3 + 2] = starColor.b;
    }

    return [pos, sc, al, sp, ph, col];
  }, []);

  // 2. Fluid Tapered Shooting Stars (3 simultaneous independent meteors)
  const meteorMeshRef = useRef<THREE.LineSegments>(null);
  const segmentsPerMeteor = 16;
  const meteorCount = 3;

  const meteors = useRef<ActiveMeteor[]>([
    {
      origin: new THREE.Vector3(-40, 32, -10),
      dir: new THREE.Vector3(1.4, -0.6, 0.3).normalize(),
      speed: 65,
      length: 22,
      progress: 0,
      maxDistance: 130,
      active: true,
      delay: 1.0,
      alpha: 1.0,
    },
    {
      origin: new THREE.Vector3(30, 42, -20),
      dir: new THREE.Vector3(-1.3, -0.7, 0.4).normalize(),
      speed: 72,
      length: 26,
      progress: 0,
      maxDistance: 140,
      active: false,
      delay: 4.5,
      alpha: 1.0,
    },
    {
      origin: new THREE.Vector3(-10, 48, -15),
      dir: new THREE.Vector3(0.8, -0.9, -0.3).normalize(),
      speed: 60,
      length: 20,
      progress: 0,
      maxDistance: 120,
      active: false,
      delay: 8.0,
      alpha: 1.0,
    },
  ]);

  const [meteorPositions, meteorProgresses, meteorAlphas] = useMemo(() => {
    const totalVertices = meteorCount * segmentsPerMeteor * 2;
    const pos = new Float32Array(totalVertices * 3);
    const prog = new Float32Array(totalVertices);
    const alp = new Float32Array(totalVertices);

    let vIdx = 0;
    for (let m = 0; m < meteorCount; m++) {
      for (let s = 0; s < segmentsPerMeteor; s++) {
        prog[vIdx] = s / segmentsPerMeteor;
        alp[vIdx] = 1.0;
        vIdx++;
        prog[vIdx] = (s + 1) / segmentsPerMeteor;
        alp[vIdx] = 1.0;
        vIdx++;
      }
    }

    return [pos, prog, alp];
  }, []);

  const uniforms = useMemo(
    () => ({
      uTime: { value: 0 },
    }),
    []
  );

  useFrame(({ clock }, delta) => {
    const t = clock.getElapsedTime();

    if (starMaterialRef.current) {
      starMaterialRef.current.uniforms.uTime.value = t;
    }
    if (pointsRef.current) {
      pointsRef.current.rotation.y = t * 0.002;
    }

    // Update smooth fluid meteors
    if (meteorMeshRef.current) {
      const posAttr = meteorMeshRef.current.geometry.attributes.position as THREE.BufferAttribute;
      const alpAttr = meteorMeshRef.current.geometry.attributes.aAlpha as THREE.BufferAttribute;
      const posArray = posAttr.array as Float32Array;
      const alpArray = alpAttr.array as Float32Array;

      meteors.current.forEach((m, mIdx) => {
        if (!m.active) {
          m.delay -= delta;
          if (m.delay <= 0) {
            m.active = true;
            m.progress = 0;
            m.origin.set(
              -60 + Math.random() * 120,
              28 + Math.random() * 25,
              -40 + Math.random() * 30
            );
            const angle = -0.35 - Math.random() * 0.45;
            const xDir = Math.random() > 0.5 ? 1.0 : -1.0;
            m.dir.set(xDir * (1.0 + Math.random() * 0.5), angle, (Math.random() - 0.5) * 0.5).normalize();
            m.speed = 58 + Math.random() * 30;
            m.length = 18 + Math.random() * 14;
            m.maxDistance = 120 + Math.random() * 40;
          }

          const baseV = mIdx * segmentsPerMeteor * 2;
          for (let i = 0; i < segmentsPerMeteor * 2; i++) {
            posArray[(baseV + i) * 3 + 1] = -9999;
          }
          return;
        }

        m.progress += delta * m.speed;

        const lifeFraction = m.progress / m.maxDistance;
        let globalAlpha = 1.0;
        if (lifeFraction < 0.15) {
          globalAlpha = lifeFraction / 0.15;
        } else if (lifeFraction > 0.75) {
          globalAlpha = (1.0 - lifeFraction) / 0.25;
        }

        const headPos = m.origin.clone().add(m.dir.clone().multiplyScalar(m.progress));
        const tailPos = headPos.clone().sub(m.dir.clone().multiplyScalar(m.length));

        const baseV = mIdx * segmentsPerMeteor * 2;
        for (let s = 0; s < segmentsPerMeteor; s++) {
          const t0 = s / segmentsPerMeteor;
          const t1 = (s + 1) / segmentsPerMeteor;

          const p0 = new THREE.Vector3().lerpVectors(tailPos, headPos, t0);
          const p1 = new THREE.Vector3().lerpVectors(tailPos, headPos, t1);

          const idx0 = (baseV + s * 2) * 3;
          posArray[idx0 + 0] = p0.x;
          posArray[idx0 + 1] = p0.y;
          posArray[idx0 + 2] = p0.z;

          const idx1 = (baseV + s * 2 + 1) * 3;
          posArray[idx1 + 0] = p1.x;
          posArray[idx1 + 1] = p1.y;
          posArray[idx1 + 2] = p1.z;

          alpArray[baseV + s * 2] = globalAlpha;
          alpArray[baseV + s * 2 + 1] = globalAlpha;
        }

        if (m.progress >= m.maxDistance) {
          m.active = false;
          m.delay = 3.0 + Math.random() * 5.0;
        }
      });

      posAttr.needsUpdate = true;
      alpAttr.needsUpdate = true;
    }
  });

  return (
    <group>
      {/* 1. Deep Space 5,500 Dense Astronomical Pinpoint Stars */}
      <points ref={pointsRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
          <bufferAttribute attach="attributes-aScale" args={[scales, 1]} />
          <bufferAttribute attach="attributes-aAlpha" args={[alphas, 1]} />
          <bufferAttribute attach="attributes-aTwinkleSpeed" args={[speeds, 1]} />
          <bufferAttribute attach="attributes-aTwinklePhase" args={[phases, 1]} />
          <bufferAttribute attach="attributes-aColor" args={[colors, 3]} />
        </bufferGeometry>
        <shaderMaterial
          ref={starMaterialRef}
          vertexShader={AstronomicalStarShader.vertexShader}
          fragmentShader={AstronomicalStarShader.fragmentShader}
          uniforms={uniforms}
          transparent={true}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </points>

      {/* 2. Fluid Tapered Glowing Shooting Star Trails */}
      <lineSegments ref={meteorMeshRef}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[meteorPositions, 3]} />
          <bufferAttribute attach="attributes-aTrailProgress" args={[meteorProgresses, 1]} />
          <bufferAttribute attach="attributes-aAlpha" args={[meteorAlphas, 1]} />
        </bufferGeometry>
        <shaderMaterial
          vertexShader={ShootingStarTrailShader.vertexShader}
          fragmentShader={ShootingStarTrailShader.fragmentShader}
          transparent={true}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </lineSegments>
    </group>
  );
};
