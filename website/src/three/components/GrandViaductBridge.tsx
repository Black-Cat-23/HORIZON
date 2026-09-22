import React, { useMemo } from 'react';
import * as THREE from 'three';

export const GrandViaductBridge: React.FC = () => {
  // Rich architectural stone material
  const stoneMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#28384e',
        roughness: 0.65,
        metalness: 0.25,
      }),
    []
  );

  const darkStoneMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#141e2c',
        roughness: 0.85,
        metalness: 0.15,
      }),
    []
  );

  const roadBedMaterial = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: '#202d3e',
        roughness: 0.75,
        metalness: 0.2,
      }),
    []
  );

  const bridgeWidth = 11.0;
  const bridgeLength = 220; // from z = 50 to z = -170

  // Balustrade crenellation pillars spaced along both edges
  const pillars = useMemo(() => {
    const items = [];
    const step = 4.8;
    for (let z = 45; z >= -150; z -= step) {
      items.push(z);
    }
    return items;
  }, []);

  return (
    <group position={[0, 0, 0]}>
      {/* 1. Main Monumental Bridge Roadway Deck */}
      <mesh position={[0, -0.6, -55]} material={roadBedMaterial} receiveShadow>
        <boxGeometry args={[bridgeWidth, 1.2, bridgeLength]} />
      </mesh>

      {/* Raised Cobblestone Curbs (Left & Right) */}
      <mesh position={[-bridgeWidth / 2 + 0.4, 0.2, -55]} material={darkStoneMaterial}>
        <boxGeometry args={[0.8, 0.4, bridgeLength]} />
      </mesh>
      <mesh position={[bridgeWidth / 2 - 0.4, 0.2, -55]} material={darkStoneMaterial}>
        <boxGeometry args={[0.8, 0.4, bridgeLength]} />
      </mesh>

      {/* 2. Massive Stone Balustrade Crenellations & Pillars */}
      {pillars.map((z, idx) => (
        <group key={idx}>
          {/* Left Edge Balustrade Pillar */}
          <group position={[-bridgeWidth / 2 + 0.4, 1.1, z]}>
            <mesh material={stoneMaterial} castShadow>
              <boxGeometry args={[0.7, 1.6, 0.7]} />
            </mesh>
            {/* Ornate Capital Cap */}
            <mesh position={[0, 0.95, 0]} material={darkStoneMaterial}>
              <boxGeometry args={[0.88, 0.35, 0.88]} />
            </mesh>
          </group>

          {/* Right Edge Balustrade Pillar */}
          <group position={[bridgeWidth / 2 - 0.4, 1.1, z]}>
            <mesh material={stoneMaterial} castShadow>
              <boxGeometry args={[0.7, 1.6, 0.7]} />
            </mesh>
            <mesh position={[0, 0.95, 0]} material={darkStoneMaterial}>
              <boxGeometry args={[0.88, 0.35, 0.88]} />
            </mesh>
          </group>

          {/* Railing Spans between Pillars */}
          {idx < pillars.length - 1 && (
            <>
              <mesh position={[-bridgeWidth / 2 + 0.4, 0.8, z - 2.4]} material={stoneMaterial}>
                <boxGeometry args={[0.3, 0.6, 4.2]} />
              </mesh>
              <mesh position={[bridgeWidth / 2 - 0.4, 0.8, z - 2.4]} material={stoneMaterial}>
                <boxGeometry args={[0.3, 0.6, 4.2]} />
              </mesh>
            </>
          )}
        </group>
      ))}

      {/* 3. Colossal Under-Bridge Support Piers Plunging into the Abyss */}
      {pillars.filter((_, i) => i % 3 === 0).map((z, idx) => (
        <group key={`pier-${idx}`} position={[0, -35, z]}>
          {/* Left Towering Column */}
          <mesh position={[-bridgeWidth / 2 + 0.6, 0, 0]} material={darkStoneMaterial}>
            <cylinderGeometry args={[1.4, 1.9, 70, 20]} />
          </mesh>
          {/* Right Towering Column */}
          <mesh position={[bridgeWidth / 2 - 0.6, 0, 0]} material={darkStoneMaterial}>
            <cylinderGeometry args={[1.4, 1.9, 70, 20]} />
          </mesh>
          {/* Transverse Cross Support Archway Beam */}
          <mesh position={[0, 31, 0]} material={darkStoneMaterial}>
            <boxGeometry args={[bridgeWidth + 2.0, 2.4, 2.4]} />
          </mesh>
        </group>
      ))}
    </group>
  );
};
