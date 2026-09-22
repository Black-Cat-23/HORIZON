import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { assetPreloader } from '../core/AssetPreloader';

interface CinematicPreloaderProps {
  onComplete: () => void;
}

export const CinematicPreloader: React.FC<CinematicPreloaderProps> = ({ onComplete }) => {
  const [progress, setProgress] = useState<number>(0);
  const [phase, setPhase] = useState<'loading' | 'converge' | 'complete'>('loading');
  const totalBlocks = 14;

  useEffect(() => {
    // Start background preloading off main thread
    assetPreloader.preloadAll();

    const unsubscribe = assetPreloader.subscribe((p) => {
      setProgress(p);
      if (p >= 100 && phase === 'loading') {
        // Trigger convergence phase after brief 100% display
        setTimeout(() => {
          setPhase('converge');
        }, 400);
      }
    });

    return unsubscribe;
  }, [phase]);

  // When convergence animation finishes, transition to video phase
  useEffect(() => {
    if (phase === 'converge') {
      const timer = setTimeout(() => {
        setPhase('complete');
        onComplete();
      }, 1600);
      return () => clearTimeout(timer);
    }
  }, [phase, onComplete]);

  // Compute how many blocks should be illuminated (0 to totalBlocks)
  const filledBlocks = Math.min(totalBlocks, Math.floor((progress / 100) * totalBlocks));

  return (
    <AnimatePresence>
      {phase !== 'complete' && (
        <motion.div
          key="preloader-overlay"
          initial={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { duration: 0.8, ease: [0.16, 1, 0.3, 1] } }}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            background: '#020408',
            backgroundImage: 'radial-gradient(ellipse at 50% 25%, #0a172a 0%, #050b14 55%, #020408 100%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            userSelect: 'none',
          }}
        >
          {phase === 'loading' ? (
            /* PHASE 1: Exact UI matching Image 1 & Image 2 */
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              style={{
                width: 'min(420px, 85vw)',
                display: 'flex',
                flexDirection: 'column',
                gap: '1.25rem',
              }}
            >
              {/* Percentage Counter (Right aligned above progress bar) */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'flex-end',
                  width: '100%',
                }}
              >
                <span
                  className="font-mono"
                  style={{
                    fontSize: '0.88rem',
                    fontWeight: 700,
                    letterSpacing: '0.08em',
                    color: 'rgba(213, 224, 255, 0.85)',
                  }}
                >
                  {progress}%
                </span>
              </div>

              {/* Square Pixel Block Progress Track (Image 1 & 2 exact layout) */}
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: '6px',
                  width: '100%',
                }}
              >
                {Array.from({ length: totalBlocks }).map((_, idx) => {
                  const isActive = idx < filledBlocks;
                  const isCurrent = idx === filledBlocks && progress < 100;
                  return (
                    <div
                      key={idx}
                      style={{
                        flex: 1,
                        aspectRatio: '1 / 1',
                        maxHeight: '16px',
                        borderRadius: '1px',
                        backgroundColor: isActive
                          ? '#ffffff'
                          : isCurrent
                          ? 'rgba(213, 224, 255, 0.65)'
                          : 'rgba(255, 255, 255, 0.12)',
                        boxShadow: isActive
                          ? '0 0 10px rgba(255, 255, 255, 0.6), 0 0 20px rgba(169, 216, 232, 0.3)'
                          : 'none',
                        transform: isCurrent ? 'scale(1.12)' : 'scale(1.0)',
                        transition: 'background-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease',
                      }}
                    />
                  );
                })}
              </div>

              {/* Subtitle: LOADING CONTENT */}
              <div>
                <span
                  className="font-mono"
                  style={{
                    fontSize: '0.68rem',
                    letterSpacing: '0.28em',
                    color: 'rgba(213, 224, 255, 0.6)',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                  }}
                >
                  LOADING CONTENT
                </span>
              </div>
            </motion.div>
          ) : (
            /* PHASE 2: Pixel Convergence to HORIZON Logo */
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '1rem',
              }}
            >
              {/* Converged Glowing HORIZON Logo */}
              <motion.h1
                initial={{ letterSpacing: '0.8em', filter: 'blur(12px)' }}
                animate={{ letterSpacing: '0.35em', filter: 'blur(0px)' }}
                transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
                className="font-editorial"
                style={{
                  fontSize: 'clamp(2.5rem, 6.5vw, 5.5rem)',
                  fontWeight: 800,
                  color: '#ffffff',
                  textTransform: 'uppercase',
                  margin: 0,
                  textShadow:
                    '0 0 30px rgba(213, 224, 255, 0.6), 0 0 60px rgba(169, 216, 232, 0.35)',
                }}
              >
                HORIZON
              </motion.h1>

              {/* Architectural Subtitle */}
              <motion.span
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 0.7, y: 0 }}
                transition={{ delay: 0.3, duration: 0.6 }}
                className="font-mono"
                style={{
                  fontSize: '0.72rem',
                  letterSpacing: '0.4em',
                  color: 'var(--state-signal)',
                  textTransform: 'uppercase',
                }}
              >
                FREE-SPACE OPTICAL COMMUNICATIONS
              </motion.span>
            </motion.div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
};
