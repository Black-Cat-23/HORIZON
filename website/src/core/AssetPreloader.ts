/**
 * HORIZON High-Performance Asset Preloader & Texture Manager
 * Prevents main thread stuttering by using off-thread decoding and smooth frame interpolation.
 */

export interface PreloadProgressCallback {
  (progress: number, label: string): void;
}

const CRITICAL_TEXTURES = [
  '/textures/earth/earth albedo.jpg',
  '/textures/earth/earth bump.jpg',
  '/textures/earth/earth land ocean mask.png',
  '/textures/earth/clouds earth.png',
  '/textures/milky_way.jpg',
];

class AssetPreloaderManager {
  private loadedCount = 0;
  private totalCount = CRITICAL_TEXTURES.length;
  private targetProgress = 0;
  private currentProgress = 0;
  private animationFrameId: number | null = null;
  private listeners: Set<PreloadProgressCallback> = new Set();
  private isLoaded = false;
  private lastReportedRounded = -1;

  public subscribe(cb: PreloadProgressCallback): () => void {
    this.listeners.add(cb);
    cb(Math.floor(this.currentProgress), this.isLoaded ? 'READY' : 'LOADING CONTENT');
    return () => this.listeners.delete(cb);
  }

  private notify(progress: number, status: string) {
    if (progress === this.lastReportedRounded) return;
    this.lastReportedRounded = progress;
    this.listeners.forEach((cb) => cb(progress, status));
  }

  public async preloadAll(): Promise<void> {
    if (this.isLoaded) return;

    this.startSmoothLoop();

    const loadPromises = CRITICAL_TEXTURES.map((url) => this.preloadSingleTexture(url));

    await Promise.all(loadPromises);

    this.targetProgress = 100;
  }

  private async preloadSingleTexture(url: string): Promise<void> {
    return new Promise<void>((resolve) => {
      const img = new Image();
      img.src = url;

      const onDone = async () => {
        if ('decode' in img) {
          try {
            await img.decode();
          } catch {
            // Fallback if decode API is unsupported
          }
        }
        this.loadedCount++;
        this.targetProgress = Math.min(99, Math.floor((this.loadedCount / this.totalCount) * 100));
        resolve();
      };

      img.onload = onDone;
      img.onerror = () => {
        this.loadedCount++;
        this.targetProgress = Math.min(99, Math.floor((this.loadedCount / this.totalCount) * 100));
        resolve();
      };
    });
  }

  private startSmoothLoop() {
    let lastTime = performance.now();

    const loop = (now: number) => {
      const delta = Math.min(0.05, (now - lastTime) / 1000);
      lastTime = now;

      // Smooth lerp progress towards targetProgress at silky 60 FPS
      if (this.currentProgress < this.targetProgress) {
        const step = Math.max(0.6, (this.targetProgress - this.currentProgress) * (delta * 10.0));
        this.currentProgress = Math.min(this.targetProgress, this.currentProgress + step);
      } else if (this.targetProgress >= 100 && this.currentProgress < 100) {
        this.currentProgress = Math.min(100, this.currentProgress + delta * 45.0);
      }

      const rounded = Math.floor(this.currentProgress);
      this.notify(rounded, rounded >= 100 ? 'SYSTEM READY' : 'LOADING CONTENT');

      if (rounded >= 100) {
        this.isLoaded = true;
        if (this.animationFrameId !== null) {
          cancelAnimationFrame(this.animationFrameId);
          this.animationFrameId = null;
        }
        return;
      }

      this.animationFrameId = requestAnimationFrame(loop);
    };

    this.animationFrameId = requestAnimationFrame(loop);
  }
}

export const assetPreloader = new AssetPreloaderManager();
