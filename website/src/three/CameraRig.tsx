import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';
import { useFrame, useThree } from '@react-three/fiber';
import { cameraSpline } from './CameraSplinePath';

interface CameraRigProps {
  progress: number;
}

export const CameraRig: React.FC<CameraRigProps> = ({ progress }) => {
  const { camera } = useThree();
  const currentLookAt = useRef(new THREE.Vector3(0, 0, 0));
  const mouse = useRef({ x: 0, y: 0, targetX: 0, targetY: 0 });

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      // Normalized mouse coordinates [-1, 1]
      mouse.current.targetX = (e.clientX / window.innerWidth) * 2 - 1;
      mouse.current.targetY = -(e.clientY / window.innerHeight) * 2 + 1;
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  useFrame((_, delta) => {
    // Smooth mouse lerp for subtle cinematic parallax
    mouse.current.x = THREE.MathUtils.damp(mouse.current.x, mouse.current.targetX, 3.5, delta);
    mouse.current.y = THREE.MathUtils.damp(mouse.current.y, mouse.current.targetY, 3.5, delta);

    const target = cameraSpline.evaluate(progress);

    // Apply mouse parallax offset to camera position
    const posX = target.position.x + mouse.current.x * 0.8;
    const posY = target.position.y + mouse.current.y * 0.5;
    const posZ = target.position.z;

    camera.position.x = THREE.MathUtils.damp(camera.position.x, posX, 4.0, delta);
    camera.position.y = THREE.MathUtils.damp(camera.position.y, posY, 4.0, delta);
    camera.position.z = THREE.MathUtils.damp(camera.position.z, posZ, 4.0, delta);

    // Apply mouse parallax offset to lookAt
    const lookX = target.lookAt.x + mouse.current.x * 1.2;
    const lookY = target.lookAt.y + mouse.current.y * 0.8;
    const lookZ = target.lookAt.z;

    currentLookAt.current.x = THREE.MathUtils.damp(currentLookAt.current.x, lookX, 4.0, delta);
    currentLookAt.current.y = THREE.MathUtils.damp(currentLookAt.current.y, lookY, 4.0, delta);
    currentLookAt.current.z = THREE.MathUtils.damp(currentLookAt.current.z, lookZ, 4.0, delta);

    camera.lookAt(currentLookAt.current);

    if ('fov' in camera) {
      const persp = camera as THREE.PerspectiveCamera;
      persp.fov = THREE.MathUtils.damp(persp.fov, target.fov, 3.5, delta);
      persp.updateProjectionMatrix();
    }
  });

  return null;
};
