import React, { useRef, useMemo, useEffect, useState } from 'react';
import * as THREE from 'three';
import { useFrame, useLoader } from '@react-three/fiber';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { TextureLoader } from 'three';

interface RealisticSatelliteProps {
  progress: number;
}

interface OrbitDefinition {
  radius: number;          // Orbital radius from Earth center
  rotation: [number, number, number]; // Euler rotation [rotX, rotY, rotZ]
  speed: number;           // Orbital angular velocity (rad/s)
  phaseOffset: number;     // Initial phase angle (rad)
  scale: number;           // Satellite model scale
  color: string;           // Orbit line ring & optical beacon color
}

const EARTH_CENTER = new THREE.Vector3(0.0, -32.5, 0.0);

// 5 Synchronized Keplerian Orbital Planes (72° relay intervals with slightly muted telemetry styling)
const SATELLITE_ORBITS: OrbitDefinition[] = [
  {
    // Sat 1: Primary Equatorial Tracking Arc
    radius: 43.0,
    rotation: [0.18, 0.35, 0.10],
    speed: 0.085,
    phaseOffset: 0.0,
    scale: 0.35,
    color: '#4e9a78',
  },
  {
    // Sat 2: High Diagonal Polar Passage
    radius: 44.8,
    rotation: [-0.28, -0.55, 0.38],
    speed: 0.085,
    phaseOffset: 1.2566, // 72 deg
    scale: 0.32,
    color: '#628e9e',
  },
  {
    // Sat 3: Central Sun-Synchronous Arc
    radius: 46.2,
    rotation: [0.32, 0.70, -0.32],
    speed: 0.085,
    phaseOffset: 2.5132, // 144 deg
    scale: 0.30,
    color: '#559489',
  },
  {
    // Sat 4: High Inclination Crossing Arc
    radius: 47.5,
    rotation: [-0.22, -0.95, 0.50],
    speed: 0.085,
    phaseOffset: 3.7699, // 216 deg
    scale: 0.28,
    color: '#658caa',
  },
  {
    // Sat 5: Retrograde Orbital Relay (Closes the continuous loop)
    radius: 45.0,
    rotation: [0.25, -0.40, -0.20],
    speed: 0.085,
    phaseOffset: 5.0265, // 288 deg
    scale: 0.33,
    color: '#529676',
  },
];

// Helper: Calculate 3D position on an arbitrarily oriented Keplerian orbital circle
function calculate3DOrbitalPosition(
  orbit: OrbitDefinition,
  theta: number,
  center: THREE.Vector3
): THREE.Vector3 {
  const R = orbit.radius;
  const localPos = new THREE.Vector3(R * Math.cos(theta), R * Math.sin(theta), 0);
  const euler = new THREE.Euler(orbit.rotation[0], orbit.rotation[1], orbit.rotation[2], 'XYZ');
  localPos.applyEuler(euler);
  return localPos.add(center);
}

export const RealisticSatellite: React.FC<RealisticSatelliteProps> = ({ progress }) => {
  const satRefs = [
    useRef<THREE.Group>(null),
    useRef<THREE.Group>(null),
    useRef<THREE.Group>(null),
    useRef<THREE.Group>(null),
    useRef<THREE.Group>(null),
  ];

  const [satelliteModel, setSatelliteModel] = useState<THREE.Group | null>(null);

  // Load PBR Texture Maps
  const [
    satBase, satNormal, satRoughness, satMetallic,
    antennaBase, antennaNormal, antennaRoughness, antennaMetallic,
    solarBase, solarNormal, solarRoughness, solarMetallic
  ] = useLoader(TextureLoader, [
    '/textures/satellite/satellite_Satélite_BaseColor.jpg',
    '/textures/satellite/satellite_Satélite_Normal.jpg',
    '/textures/satellite/satellite_Satélite_Roughness.jpg',
    '/textures/satellite/satellite_Satélite_Metallic.jpg',
    '/textures/satellite/satellite_Antenna_BaseColor.jpg',
    '/textures/satellite/satellite_Antenna_Normal.jpg',
    '/textures/satellite/satellite_Antenna_Roughness.jpg',
    '/textures/satellite/satellite_Antenna_Metallic.jpg',
    '/textures/satellite/satellite_Placas_BaseColor.jpg',
    '/textures/satellite/satellite_Placas_Normal.jpg',
    '/textures/satellite/satellite_Placas_Roughness.jpg',
    '/textures/satellite/satellite_Placas_Metallic.jpg',
  ]);

  useMemo(() => {
    satBase.colorSpace = THREE.SRGBColorSpace;
    antennaBase.colorSpace = THREE.SRGBColorSpace;
    solarBase.colorSpace = THREE.SRGBColorSpace;
  }, [satBase, antennaBase, solarBase]);

  const satMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        map: satBase,
        normalMap: satNormal,
        roughnessMap: satRoughness,
        metalnessMap: satMetallic,
        roughness: 0.35,
        metalness: 0.85,
      }),
    [satBase, satNormal, satRoughness, satMetallic]
  );

  const antennaMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        map: antennaBase,
        normalMap: antennaNormal,
        roughnessMap: antennaRoughness,
        metalnessMap: antennaMetallic,
        roughness: 0.25,
        metalness: 0.9,
      }),
    [antennaBase, antennaNormal, antennaRoughness, antennaMetallic]
  );

  const solarMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        map: solarBase,
        normalMap: solarNormal,
        roughnessMap: solarRoughness,
        metalnessMap: solarMetallic,
        roughness: 0.15,
        metalness: 0.95,
      }),
    [solarBase, solarNormal, solarRoughness, solarMetallic]
  );

  useEffect(() => {
    const loader = new OBJLoader();
    loader.load(
      '/models/Satellite.obj',
      (obj) => {
        obj.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            mesh.castShadow = true;
            mesh.receiveShadow = true;

            const name = mesh.name.toLowerCase();
            if (name.includes('antenna') || name.includes('dish') || name.includes('feed')) {
              mesh.material = antennaMaterial;
            } else if (name.includes('placa') || name.includes('solar') || name.includes('panel')) {
              mesh.material = solarMaterial;
            } else {
              mesh.material = satMaterial;
            }
          }
        });
        setSatelliteModel(obj);
      },
      undefined,
      (err) => console.warn('Error loading Satellite.obj:', err)
    );
  }, [satMaterial, antennaMaterial, solarMaterial]);

  const models = useMemo(
    () => SATELLITE_ORBITS.map(() => (satelliteModel ? satelliteModel.clone() : null)),
    [satelliteModel]
  );

  // Generate 3D visible Orbit Ring Geometries (128 points per orbit loop)
  const orbitLineGeometries = useMemo(() => {
    return SATELLITE_ORBITS.map((orbit) => {
      const points: THREE.Vector3[] = [];
      const steps = 128;
      for (let i = 0; i <= steps; i++) {
        const theta = (i / steps) * Math.PI * 2;
        points.push(calculate3DOrbitalPosition(orbit, theta, EARTH_CENTER));
      }
      return new THREE.BufferGeometry().setFromPoints(points);
    });
  }, []);

  useFrame(({ clock }, delta) => {
    const t = clock.getElapsedTime();

    SATELLITE_ORBITS.forEach((orbit, idx) => {
      const ref = satRefs[idx].current;
      if (!ref) return;

      const theta = orbit.phaseOffset + t * orbit.speed;
      const pos = calculate3DOrbitalPosition(orbit, theta, EARTH_CENTER);

      ref.position.x = THREE.MathUtils.damp(ref.position.x, pos.x, 4.0, delta);
      ref.position.y = THREE.MathUtils.damp(ref.position.y, pos.y, 4.0, delta);
      ref.position.z = THREE.MathUtils.damp(ref.position.z, pos.z, 4.0, delta);

      const nextTheta = theta + 0.05;
      const nextPos = calculate3DOrbitalPosition(orbit, nextTheta, EARTH_CENTER);
      const velocityVec = new THREE.Vector3().subVectors(nextPos, pos).normalize();

      ref.lookAt(pos.clone().add(velocityVec));
      // Dynamic autonomous axial spin around communication axis
      ref.rotation.z += (t * 0.2 + idx * 0.5);
    });
  });

  const isVisible = progress < 0.25;

  return (
    <group visible={isVisible}>
      {/* 1. Visible Glowing 3D Orbital Trajectory Rings encircling 40% Earth horizon */}
      {SATELLITE_ORBITS.map((orbit, idx) => (
        <line key={`orbit-ring-${idx}`} geometry={orbitLineGeometries[idx]}>
          <lineBasicMaterial
            color={orbit.color}
            transparent={true}
            opacity={0.22}
            blending={THREE.NormalBlending}
            depthTest={true}
            depthWrite={false}
            linewidth={1}
          />
        </line>
      ))}

      {/* 2. 5 Revolving 3D Satellites in Synchronized Constellation Relay */}
      {SATELLITE_ORBITS.map((orbit, idx) => (
        <group
          key={`sat-${idx}`}
          ref={satRefs[idx]}
          position={[0, 0, 0]}
          scale={[orbit.scale, orbit.scale, orbit.scale]}
        >
          {models[idx] && <primitive object={models[idx]!} />}

          {/* Optical Transceiver Communication Beacon */}
          <mesh position={[0, 0.6, 0.4]}>
            <sphereGeometry args={[0.08, 16, 16]} />
            <meshBasicMaterial color={orbit.color} />
            <pointLight color={orbit.color} intensity={2.8} distance={8} decay={2} />
          </mesh>
        </group>
      ))}
    </group>
  );
};
