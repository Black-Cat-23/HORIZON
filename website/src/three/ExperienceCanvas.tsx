import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import * as THREE from 'three';
import { CameraRig } from './CameraRig';
import { EarthCurvedHorizon } from './components/EarthCurvedHorizon';
import { GroundTerminalStation } from './components/GroundTerminalStation';
import { RealisticSatellite } from './components/RealisticSatellite';
import { ParticleStarfield } from './components/ParticleStarfield';

interface ExperienceCanvasProps {
  progress: number;
}

export const ExperienceCanvas: React.FC<ExperienceCanvasProps> = ({ progress }) => {
  const [scrollY, setScrollY] = React.useState<number>(0);

  React.useEffect(() => {
    const handleScroll = () => {
      setScrollY(window.scrollY);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Synchronous 1:1 scroll translation with DOM Hero section
  const translateY = -Math.min(window.innerHeight * 1.25, scrollY);

  return (
    <div
      id="webgl-canvas-container"
      style={{
        transform: `translate3d(0, ${translateY}px, 0)`,
        maskImage: scrollY > 10
          ? 'linear-gradient(180deg, rgba(0,0,0,1) 0%, rgba(0,0,0,1) 78%, rgba(0,0,0,0) 100%)'
          : 'none',
        WebkitMaskImage: scrollY > 10
          ? 'linear-gradient(180deg, rgba(0,0,0,1) 0%, rgba(0,0,0,1) 78%, rgba(0,0,0,0) 100%)'
          : 'none',
      }}
    >
      {/* 100% Flat, Pristine, Uncurved 2D Hero Background Image (20% transparent) */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          width: '100vw',
          height: '100vh',
          backgroundImage: 'url(/images/5.jpg)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          backgroundRepeat: 'no-repeat',
          opacity: 0.55,
          zIndex: 0,
          pointerEvents: 'none',
        }}
      />

      <Canvas
        camera={{ position: [0.0, 10.5, 48.0], fov: 46, near: 0.1, far: 1200 }}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: 'high-performance',
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: 0.95,
        }}
        dpr={[1, 1.5]}
      >
        <fog attach="fog" args={['#020408', 80, 450]} />

        {/* Cinematic Balanced Lighting (Rich Earth Daylight + Deep Space Contrast) */}
        <ambientLight intensity={1.15} color="#e0eeff" />
        <directionalLight position={[24, 26, 48]} intensity={3.5} color="#ffffff" />
        <directionalLight position={[-32, 12, 32]} intensity={1.2} color="#85b4ea" />

        <Suspense fallback={null}>
          <CameraRig progress={progress} />
          <ParticleStarfield />
          <EarthCurvedHorizon progress={progress} />
          <RealisticSatellite progress={progress} />
        </Suspense>
      </Canvas>
    </div>
  );
};
