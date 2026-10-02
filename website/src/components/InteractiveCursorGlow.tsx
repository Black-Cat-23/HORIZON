import React, { useEffect, useRef, useState } from 'react';

export const InteractiveCursorGlow: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  
  const cursorDotRef = useRef<HTMLDivElement>(null);
  const cursorGlowRef = useRef<HTMLDivElement>(null);
  const spotlightRef = useRef<HTMLDivElement>(null);

  const mousePos = useRef({ x: -100, y: -100 });
  const glowPos = useRef({ x: -100, y: -100 });
  const spotlightPos = useRef({ x: -100, y: -100 });
  const rafId = useRef<number | null>(null);

  useEffect(() => {
    // Check if device is touch or reduced motion
    const isTouch = window.matchMedia('(pointer: coarse)').matches;
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (isTouch || prefersReducedMotion) return;

    const handleMouseMove = (e: MouseEvent) => {
      mousePos.current = { x: e.clientX, y: e.clientY };
      if (!isVisible) setIsVisible(true);

      // Check if hovering over interactive element
      const target = e.target as HTMLElement | null;
      if (target) {
        const isInteractive = Boolean(
          target.closest('button, a, input, [role="button"], .beveled-glass-card, .interactive-target, table tr')
        );
        setIsHovering(isInteractive);
      }
    };

    const handleMouseLeave = () => {
      setIsVisible(false);
    };

    const handleMouseEnter = () => {
      setIsVisible(true);
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    document.addEventListener('mouseleave', handleMouseLeave);
    document.addEventListener('mouseenter', handleMouseEnter);

    // Smooth Lerp Animation Loop
    const animate = () => {
      // Lerp glow position
      const glowLerpFactor = 0.18;
      glowPos.current.x += (mousePos.current.x - glowPos.current.x) * glowLerpFactor;
      glowPos.current.y += (mousePos.current.y - glowPos.current.y) * glowLerpFactor;

      // Slower ambient spotlight lerp factor (deep fluid trailing light)
      const spotLerpFactor = 0.08;
      spotlightPos.current.x += (mousePos.current.x - spotlightPos.current.x) * spotLerpFactor;
      spotlightPos.current.y += (mousePos.current.y - spotlightPos.current.y) * spotLerpFactor;

      if (cursorDotRef.current) {
        cursorDotRef.current.style.transform = `translate3d(${mousePos.current.x}px, ${mousePos.current.y}px, 0)`;
      }

      if (cursorGlowRef.current) {
        cursorGlowRef.current.style.transform = `translate3d(${glowPos.current.x}px, ${glowPos.current.y}px, 0)`;
      }

      if (spotlightRef.current) {
        spotlightRef.current.style.transform = `translate3d(${spotlightPos.current.x}px, ${spotlightPos.current.y}px, 0)`;
      }

      rafId.current = requestAnimationFrame(animate);
    };

    rafId.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
      document.removeEventListener('mouseenter', handleMouseEnter);
      if (rafId.current) cancelAnimationFrame(rafId.current);
    };
  }, [isVisible]);

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        pointerEvents: 'none',
        zIndex: 9999,
        overflow: 'hidden',
        opacity: isVisible ? 1 : 0,
        transition: 'opacity 0.4s ease-out',
      }}
      aria-hidden="true"
    >
      {/* 1. Large Ambient Spotlight (segerman.dev style trailing luminous aura) */}
      <div
        ref={spotlightRef}
        style={{
          position: 'absolute',
          top: -350,
          left: -350,
          width: 700,
          height: 700,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(56, 189, 248, 0.08) 0%, rgba(30, 58, 138, 0.03) 45%, transparent 70%)',
          willChange: 'transform',
        }}
      />

      {/* 2. Micro Reticle / Halo Glow */}
      <div
        ref={cursorGlowRef}
        style={{
          position: 'absolute',
          top: -24,
          left: -24,
          width: 48,
          height: 48,
          borderRadius: '50%',
          border: isHovering ? '1.5px solid rgba(56, 189, 248, 0.75)' : '1px solid rgba(255, 255, 255, 0.25)',
          background: isHovering ? 'rgba(56, 189, 248, 0.12)' : 'rgba(255, 255, 255, 0.02)',
          boxShadow: isHovering ? '0 0 20px rgba(56, 189, 248, 0.35)' : 'none',
          transform: 'translate3d(-100px, -100px, 0)',
          transition: 'width 0.25s cubic-bezier(0.16, 1, 0.3, 1), height 0.25s cubic-bezier(0.16, 1, 0.3, 1), border 0.25s ease, background 0.25s ease, box-shadow 0.25s ease',
          willChange: 'transform',
        }}
      />

      {/* 3. Ultra-sharp Core Laser Dot */}
      <div
        ref={cursorDotRef}
        style={{
          position: 'absolute',
          top: -3,
          left: -3,
          width: 6,
          height: 6,
          borderRadius: '50%',
          backgroundColor: isHovering ? '#38bdf8' : '#ffffff',
          boxShadow: isHovering ? '0 0 8px #38bdf8' : '0 0 4px rgba(255, 255, 255, 0.8)',
          willChange: 'transform',
          transition: 'background-color 0.2s ease, box-shadow 0.2s ease',
        }}
      />
    </div>
  );
};
