import React, { useRef, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';

const videoSource = '/videos/hero.mp4';

interface CinematicIntroVideoProps {
  onComplete: () => void;
}

export const CinematicIntroVideo: React.FC<CinematicIntroVideoProps> = ({ onComplete }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isFadingOut, setIsFadingOut] = useState<boolean>(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    let isHandled = false;

    const safeTriggerComplete = () => {
      if (isHandled) return;
      isHandled = true;
      setIsFadingOut(true);
      setTimeout(() => {
        onComplete();
      }, 750);
    };

    const handleLoadedData = async () => {
      try {
        await video.play();
      } catch (err) {
        console.warn('Autoplay or video play fallback:', err);
      }
    };

    const handleEnded = () => {
      safeTriggerComplete();
    };

    const handleTimeUpdate = () => {
      if (video.duration && video.currentTime >= video.duration - 0.15) {
        safeTriggerComplete();
      }
    };

    const handleError = () => {
      console.warn('Video load error fallback, skipping intro video cleanly');
      safeTriggerComplete();
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        safeTriggerComplete();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    video.addEventListener('loadeddata', handleLoadedData);
    video.addEventListener('canplay', handleLoadedData);
    video.addEventListener('ended', handleEnded);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('error', handleError);

    if (video.readyState >= 2) {
      handleLoadedData();
    }

    // Safety timeout: Ensure intro video doesn't get stuck if browser blocks video playback (18.2s video + buffer)
    const maxSafetyTimeout = setTimeout(() => {
      safeTriggerComplete();
    }, 24000);

    return () => {
      clearTimeout(maxSafetyTimeout);
      window.removeEventListener('keydown', handleKeyDown);
      video.removeEventListener('loadeddata', handleLoadedData);
      video.removeEventListener('canplay', handleLoadedData);
      video.removeEventListener('ended', handleEnded);
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('error', handleError);
    };
  }, [onComplete]);

  const triggerComplete = () => {
    setIsFadingOut(true);
    setTimeout(() => {
      onComplete();
    }, 750);
  };

  return (
    <AnimatePresence>
      {!isFadingOut && (
        <motion.div
          key="cinematic-video-overlay"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, transition: { duration: 0.75, ease: [0.16, 1, 0.3, 1] } }}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9990,
            background: '#020408',
            backgroundImage: 'radial-gradient(ellipse at 50% 25%, #0a172a 0%, #050b14 55%, #020408 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden',
          }}
        >
          {/* Fullscreen Video Stream */}
          <video
            ref={videoRef}
            src={videoSource}
            muted
            playsInline
            style={{
              width: '100vw',
              height: '100vh',
              objectFit: 'cover',
              pointerEvents: 'none',
            }}
          />

          {/* Discreet Minimal Skip Control */}
          <button
            onClick={triggerComplete}
            className="font-mono"
            style={{
              position: 'absolute',
              bottom: '2.5rem',
              right: '3rem',
              backgroundColor: 'rgba(5, 11, 20, 0.75)',
              border: '1px solid rgba(213, 224, 255, 0.25)',
              color: 'var(--text-secondary)',
              padding: '0.5rem 1.1rem',
              fontSize: '0.72rem',
              letterSpacing: '0.2em',
              borderRadius: '2px',
              cursor: 'pointer',
              backdropFilter: 'blur(10px)',
              transition: 'all 0.3s ease',
              zIndex: 9995,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'rgba(213, 224, 255, 0.65)';
              e.currentTarget.style.color = '#ffffff';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(213, 224, 255, 0.25)';
              e.currentTarget.style.color = 'var(--text-secondary)';
            }}
          >
            SKIP INTRO [ESC]
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
};
