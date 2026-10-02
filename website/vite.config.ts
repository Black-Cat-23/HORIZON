import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';

function doCopy() {
  try {
    const rootDir = path.resolve(__dirname, '..');
    const c4dDir = path.join(rootDir, 'blender', 'C4D Earth');
    const earthPublicDir = path.join(__dirname, 'public', 'textures', 'earth');
    const texturesPublicDir = path.join(__dirname, 'public', 'textures');

    if (!fs.existsSync(earthPublicDir)) {
      fs.mkdirSync(earthPublicDir, { recursive: true });
    }

    const cdJpg = path.join(c4dDir, 'r', 'cd.jpg');
    if (fs.existsSync(cdJpg)) {
      fs.copyFileSync(cdJpg, path.join(earthPublicDir, 'c4d_earth_albedo.jpg'));
      console.log('[C4D Sync] Synced cd.jpg -> c4d_earth_albedo.jpg');
    }

    const cPng = path.join(c4dDir, 'r', 'c.png');
    if (fs.existsSync(cPng)) {
      fs.copyFileSync(cPng, path.join(earthPublicDir, 'c4d_earth_clouds.png'));
      console.log('[C4D Sync] Synced c.png -> c4d_earth_clouds.png');
    }

    const starsJpg = path.join(c4dDir, '8k_stars_milky_way.jpg');
    if (fs.existsSync(starsJpg)) {
      fs.copyFileSync(starsJpg, path.join(texturesPublicDir, '8k_stars_milky_way.jpg'));
      console.log('[C4D Sync] Synced 8k_stars_milky_way.jpg');
    }

  } catch (err) {
    console.warn('[C4D Sync] Copy error:', err);
  }
}

// Run copy immediately when module loads
doCopy();

function syncC4dEarthAssets() {
  return {
    name: 'sync-c4d-earth-assets',
    buildStart() {
      doCopy();
    },
  };
}

export default defineConfig({
  plugins: [react(), syncC4dEarthAssets()],
  server: {
    port: 3000,
    host: true,
  },
  build: {
    target: 'esnext',
    outDir: 'dist',
  },
});
