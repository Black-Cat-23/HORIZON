import React from 'react';

export const HorizonTransitionDivider: React.FC = () => {
  return (
    <div
      aria-hidden="true"
      style={{
        position: 'relative',
        width: '100%',
        zIndex: 25,
        pointerEvents: 'none',
        display: 'block',
        marginTop: '0',
        marginBottom: '0',
      }}
    >
      {/* Exact Image 1: 3D Curled Silk Ribbon / Paper-Peel Wave Horizon */}
      <svg
        viewBox="0 0 1920 360"
        preserveAspectRatio="none"
        style={{
          width: '100%',
          height: 'clamp(180px, 24vw, 360px)',
          display: 'block',
          overflow: 'visible',
        }}
      >
        <defs>
          {/* Luminous White to Icy-Cyan Curled Ribbon Highlight */}
          <linearGradient id="ribbon-glow-edge" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#bfdbfe" stopOpacity="0.9" />
            <stop offset="8%" stopColor="#ffffff" stopOpacity="1" />
            <stop offset="25%" stopColor="#93c5fd" stopOpacity="0.95" />
            <stop offset="45%" stopColor="#dbeafe" stopOpacity="1" />
            <stop offset="68%" stopColor="#60a5fa" stopOpacity="0.95" />
            <stop offset="88%" stopColor="#ffffff" stopOpacity="1" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.85" />
          </linearGradient>

          {/* 3D Curled Underside Soft Deep Shadow */}
          <linearGradient id="ribbon-curl-shade" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#1e3a8a" stopOpacity="0.8" />
            <stop offset="30%" stopColor="#0f172a" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#020408" stopOpacity="1" />
          </linearGradient>

          {/* Deep Space Body Fill */}
          <linearGradient id="space-body-fill" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#050b14" stopOpacity="0.98" />
            <stop offset="100%" stopColor="#020408" stopOpacity="1" />
          </linearGradient>

          <filter id="ribbon-glow" x="-10%" y="-30%" width="120%" height="160%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* 1. Deep Shadow Cast Underneath the Curled Lip */}
        <path
          d="M0,125 
             C180,80 340,165 520,135 
             C700,105 880,195 1100,175 
             C1320,155 1520,70 1720,150 
             C1820,190 1880,180 1920,175 
             L1920,360 
             L0,360 Z"
          fill="url(#ribbon-curl-shade)"
        />

        {/* 2. Main 3D Undulating Silk / Paper-Peel Wave Body */}
        <path
          d="M0,118 
             C180,72 340,158 520,128 
             C700,98 880,188 1100,168 
             C1320,148 1520,62 1720,142 
             C1820,182 1880,172 1920,168 
             L1920,360 
             L0,360 Z"
          fill="url(#space-body-fill)"
        />

        {/* 3. Luminous Glowing Curled Ribbon Upper Lip Rim (Exact Image 1 Crest) */}
        <path
          d="M0,118 
             C180,72 340,158 520,128 
             C700,98 880,188 1100,168 
             C1320,148 1520,62 1720,142 
             C1820,182 1880,172 1920,168"
          fill="none"
          stroke="url(#ribbon-glow-edge)"
          strokeWidth="14"
          strokeLinecap="round"
          filter="url(#ribbon-glow)"
        />

        {/* 4. Fine Brilliant Core White Hairline Filament */}
        <path
          d="M0,118 
             C180,72 340,158 520,128 
             C700,98 880,188 1100,168 
             C1320,148 1520,62 1720,142 
             C1820,182 1880,172 1920,168"
          fill="none"
          stroke="#ffffff"
          strokeWidth="3.5"
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
};
