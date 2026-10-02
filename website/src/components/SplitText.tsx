import React, { useState, useEffect, useRef } from 'react';
import clsx from 'clsx';

interface SplitTextProps {
  text: string;
  className?: string;
  isVisible?: boolean;
  baseDelay?: number;
  charDelay?: number;
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'span' | 'div';
  once?: boolean;
}

export const SplitText: React.FC<SplitTextProps> = ({
  text,
  className,
  isVisible,
  baseDelay = 0,
  charDelay = 22,
  as: Component = 'span',
  once = false,
}) => {
  const containerRef = useRef<HTMLElement | null>(null);
  const [isInViewport, setIsInViewport] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    // Use IntersectionObserver so the animation triggers every time it scrolls into view
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsInViewport(true);
          } else {
            if (!once) {
              setIsInViewport(false);
            }
          }
        });
      },
      {
        threshold: 0.12,
        rootMargin: '0px 0px -30px 0px',
      }
    );

    observer.observe(el);

    return () => {
      observer.disconnect();
    };
  }, [once]);

  // Trigger when entering viewport (or explicit isVisible override)
  const isTriggered = isVisible !== undefined ? (isVisible || isInViewport) : isInViewport;

  const words = text.split(' ');
  let charCounter = 0;

  return (
    <Component
      ref={containerRef as any}
      className={clsx('split-text-root', isTriggered && 'is-visible', className)}
    >
      {words.map((word, wIdx) => {
        const chars = Array.from(word);
        return (
          <span key={wIdx} className="split-word">
            {chars.map((char, cIdx) => {
              const idx = charCounter++;
              return (
                <span key={cIdx} className="split-char-wrap">
                  <span
                    className="split-char"
                    style={
                      {
                        '--char-index': idx,
                        '--base-delay': `${baseDelay}ms`,
                        transitionDelay: isTriggered ? `${idx * charDelay + baseDelay}ms` : '0ms',
                      } as React.CSSProperties
                    }
                  >
                    {char}
                  </span>
                </span>
              );
            })}
            {wIdx < words.length - 1 && (
              <span className="split-char-wrap">
                <span className="split-char split-space">&nbsp;</span>
              </span>
            )}
          </span>
        );
      })}
    </Component>
  );
};
