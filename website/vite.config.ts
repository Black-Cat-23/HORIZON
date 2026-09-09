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

    // Sync 1.jpg (vibrant purple/blue cosmic nebula) to website public images
    const hero1Src = 'C:\\Users\\Ankit\\.gemini\\antigravity-ide\\brain\\0f597a1c-3514-4b86-bb36-efdf53002187\\.user_uploaded\\media_1788964028995.jpg';
    const imagesPublicDir = path.join(__dirname, 'public', 'images');
    if (!fs.existsSync(imagesPublicDir)) {
      fs.mkdirSync(imagesPublicDir, { recursive: true });
    }
    if (fs.existsSync(hero1Src)) {
      fs.copyFileSync(hero1Src, path.join(imagesPublicDir, 'hero-bg-1.jpg'));
      fs.copyFileSync(hero1Src, path.join(imagesPublicDir, '1.jpg'));
      fs.copyFileSync(hero1Src, path.join(__dirname, 'public', '1.jpg'));
      console.log('[Hero Image Sync] Synced vibrant nebula -> hero-bg-1.jpg & 1.jpg');
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
    configureServer(server) {
      doCopy();
      server.middlewares.use((req, res, next) => {
        const hero1Src = 'C:\\Users\\Ankit\\.gemini\\antigravity-ide\\brain\\0f597a1c-3514-4b86-bb36-efdf53002187\\.user_uploaded\\media_1788964028995.jpg';
        const url = req.url ? req.url.split('?')[0] : '';
        if (
          url === '/images/1.jpg' ||
          url === '/images/hero-bg-1.jpg' ||
          url === '/1.jpg' ||
          url === '/textures/milky_way.jpg'
        ) {
          if (fs.existsSync(hero1Src)) {
            res.setHeader('Content-Type', 'image/jpeg');
            res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0');
            fs.createReadStream(hero1Src).pipe(res);
            return;
          }
        }
        next();
      });
    }
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
