import React, { useMemo } from 'react';
import * as THREE from 'three';
import { useLoader } from '@react-three/fiber';
import { TextureLoader } from 'three';

interface HeroBackgroundLayerProps {
  progress: number;
}

const HeroBackgroundShader = {
  uniforms: {
    uTexture: { value: null as THREE.Texture | null },
    uOpacity: { value: 1.0 },
    uVibrancy: { value: 1.25 },
  },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D uTexture;
    uniform float uOpacity;
    uniform float uVibrancy;
    varying vec2 vUv;

    void main() {
      vec4 texColor = texture2D(uTexture, vUv);
      
      // Preserve crisp sRGB vibrancy without dark midtone compression
      vec3 color = texColor.rgb;
      
      // Subtle contrast & brightness enhancement for space depth
      color = pow(color, vec3(0.96)) * uVibrancy;
      
      gl_FragColor = vec4(color, uOpacity);
    }
  `,
};

export const HeroBackgroundLayer: React.FC<HeroBackgroundLayerProps> = ({ progress }) => {
  const texture = useLoader(TextureLoader, '/images/5.jpg');

  useMemo(() => {
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.generateMipmaps = true;
    texture.minFilter = THREE.LinearMipmapLinearFilter;
    texture.magFilter = THREE.LinearFilter;
    texture.anisotropy = 16;
    texture.wrapS = THREE.ClampToEdgeWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    texture.needsUpdate = true;
  }, [texture]);

  // Smooth scroll fade-out past Hero section (progress > 0.12)
  const opacity = Math.max(0, 1.0 * Math.max(0, 1 - progress / 0.12));

  const shaderMaterial = useMemo(() => {
    const mat = new THREE.ShaderMaterial({
      uniforms: {
        uTexture: { value: texture },
        uOpacity: { value: opacity },
        uVibrancy: { value: 1.15 },
      },
      vertexShader: HeroBackgroundShader.vertexShader,
      fragmentShader: HeroBackgroundShader.fragmentShader,
      transparent: true,
      depthWrite: false,
      fog: false,
      toneMapped: false,
    });
    return mat;
  }, [texture]);

  // Keep uniforms in sync with scroll
  useMemo(() => {
    if (shaderMaterial) {
      shaderMaterial.uniforms.uOpacity.value = opacity;
    }
  }, [shaderMaterial, opacity]);

  if (opacity <= 0.001) return null;

  // Perfectly framed across upper sky area above Earth horizon (Y = 5.5)
  return (
    <mesh position={[0, 16.0, -50]} scale={[240, 135, 1]} material={shaderMaterial}>
      <planeGeometry args={[1, 1]} />
    </mesh>
  );
};
