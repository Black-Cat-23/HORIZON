import React from 'react';
import clsx from 'clsx';

interface SplitTextProps {
  text: string;
  className?: string;
  isVisible?: boolean;
  baseDelay?: number;
  charDelay?: number;
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'span' | 'div';
}

export const SplitText: React.FC<SplitTextProps> = ({
  text,
  className,
  isVisible = true,
  baseDelay = 0,
  charDelay = 26,
  as: Component = 'span',
}) => {
  const words = text.split(' ');
  let charCounter = 0;

  return (
    <Component className={clsx('split-text-root', isVisible && 'is-visible', className)}>
      {words.map((word, wIdx) => {
        const chars = Array.from(word);
        return (
          <span key={wIdx} className="inline-block whitespace-nowrap">
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
                        transitionDelay: `${idx * charDelay + baseDelay}ms`,
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
