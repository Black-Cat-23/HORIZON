import Lenis from 'lenis';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

export class ScrollManager {
  private static instance: ScrollManager;
  public lenis: Lenis | null = null;
  private onProgressCallbacks: ((progress: number) => void)[] = [];

  private constructor() {
    this.init();
  }

  public static getInstance(): ScrollManager {
    if (!ScrollManager.instance) {
      ScrollManager.instance = new ScrollManager();
    }
    return ScrollManager.instance;
  }

  private init() {
    if (typeof window === 'undefined') return;

    this.lenis = new Lenis({
      duration: 1.4,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      orientation: 'vertical',
      smoothWheel: true,
      wheelMultiplier: 0.9,
      touchMultiplier: 1.5,
    });

    // Synchronize Lenis with GSAP ScrollTrigger
    this.lenis.on('scroll', (e: { progress: number }) => {
      ScrollTrigger.update();
      this.onProgressCallbacks.forEach((cb) => cb(e.progress));
    });

    gsap.ticker.add((time) => {
      this.lenis?.raf(time * 1000);
    });

    gsap.ticker.lagSmoothing(0);
  }

  public subscribeProgress(cb: (progress: number) => void) {
    this.onProgressCallbacks.push(cb);
    return () => {
      this.onProgressCallbacks = this.onProgressCallbacks.filter((fn) => fn !== cb);
    };
  }

  public scrollTo(target: string | HTMLElement | number) {
    this.lenis?.scrollTo(target, { duration: 1.6 });
  }

  public stop() {
    this.lenis?.stop();
  }

  public start() {
    this.lenis?.start();
  }
}

export const scrollManager = ScrollManager.getInstance();
