import React, { useState, useEffect } from 'react';
import { IVRESSHeader } from './components/IVRESSHeader';
import { IVRESSVerticalText } from './components/IVRESSVerticalText';
import { IVRESSChapterDisplay } from './components/IVRESSChapterDisplay';
import { ChapterRail } from './components/ChapterRail';
import { FilmGrainOverlay } from './components/FilmGrainOverlay';
import { ExperienceCanvas } from './three/ExperienceCanvas';
import { CHAPTERS, ChapterMeta } from './core/StateManager';
import { scrollManager } from './core/ScrollManager';
import { audioManager } from './core/AudioManager';

// Cinematic Flow Components
import { CinematicPreloader } from './components/CinematicPreloader';
import { CinematicIntroVideo } from './components/CinematicIntroVideo';

// Chapters
import { PreloadGate } from './chapters/00_PreloadGate';
import { UnknownSignal } from './chapters/01_UnknownSignal';
import { CameraFrustum } from './chapters/02_CameraFrustum';
import { SearchScan } from './chapters/03_SearchScan';
import { Acquisition } from './chapters/04_Acquisition';
import { TrackingTelemetry } from './chapters/05_TrackingTelemetry';
import { DisturbanceLab } from './chapters/06_DisturbanceLab';
import { LockLoss } from './chapters/07_LockLoss';
import { Reacquisition } from './chapters/08_Reacquisition';
import { SystemArchitecture } from './chapters/09_SystemArchitecture';
import { BenchmarkProof } from './chapters/10_BenchmarkProof';
import { ClosingEpilogue } from './chapters/11_ClosingEpilogue';

export const App: React.FC = () => {
  const [flowState, setFlowState] = useState<'preloading' | 'video' | 'entered'>('preloading');
  const [activeChapter, setActiveChapter] = useState<ChapterMeta>(CHAPTERS[0]);
  const [isAudioActive, setIsAudioActive] = useState<boolean>(false);
  const [scrollProgress, setScrollProgress] = useState<number>(0);

  useEffect(() => {
    const unsubscribe = scrollManager.subscribeProgress((p) => {
      setScrollProgress(p);
      const current =
        CHAPTERS.find((c) => p >= c.progressStart && p <= c.progressEnd) ||
        (p >= 1.0 ? CHAPTERS[CHAPTERS.length - 1] : CHAPTERS[0]);
      setActiveChapter(current);
    });
    return unsubscribe;
  }, []);

  const handlePreloaderComplete = () => {
    setFlowState('video');
  };

  const handleVideoComplete = () => {
    setFlowState('entered');
    audioManager.init();
    const active = audioManager.toggleMute();
    setIsAudioActive(active);

    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior });
  };

  const handleToggleAudio = () => {
    const active = audioManager.toggleMute();
    setIsAudioActive(active);
  };

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        minHeight: '100vh',
        background: '#020408',
        backgroundImage: 'radial-gradient(ellipse at 50% 25%, #0a172a 0%, #050b14 55%, #020408 100%)',
        backgroundAttachment: 'fixed',
      }}
    >
      {/* 1. Cinematic Block Pixel Preloader (0-100% -> HORIZON convergence) */}
      {flowState === 'preloading' && (
        <CinematicPreloader onComplete={handlePreloaderComplete} />
      )}

      {/* 2. Cinematic MP4 Intro Video (Plays 6s to 15s trimmed uninterrupted) */}
      {flowState === 'video' && (
        <CinematicIntroVideo onComplete={handleVideoComplete} />
      )}

      {/* 3. Persistent 3D Architectural Viaduct Canvas behind DOM */}
      <ExperienceCanvas progress={scrollProgress} />

      {/* 4. Subtle Oval Border Vignette & Film Grain Overlay (Narrative Chapters Only) */}
      {scrollProgress > 0.08 && (
        <>
          <div className="vignette-overlay" />
          <FilmGrainOverlay />
        </>
      )}

      {/* 5. IVRESS Minimalist Header */}
      <IVRESSHeader
        isAudioActive={isAudioActive}
        onToggleAudio={handleToggleAudio}
      />



      {/* 7. Bottom-Left Giant Cormorant Garamond 01 / 11 Numerals */}
      <IVRESSChapterDisplay activeChapter={activeChapter} totalChapters="11" />

      {/* 8. Right-hand Vertical Chapter Rail */}
      <ChapterRail activeChapterId={activeChapter.id} />

      {/* 9. Main Narrative Scrollytelling DOM Chapters */}
      <main id="scrolly-container">
        <PreloadGate
          onEnter={() => handleVideoComplete()}
          isEntered={flowState === 'entered'}
          loadProgress={100}
        />
        <UnknownSignal isActive={activeChapter.id === 'unknown'} />
        <CameraFrustum isActive={activeChapter.id === 'camera'} />
        <SearchScan isActive={activeChapter.id === 'search'} />
        <Acquisition isActive={activeChapter.id === 'acquire'} />
        <TrackingTelemetry isActive={activeChapter.id === 'track'} />
        <DisturbanceLab isActive={activeChapter.id === 'disturbance'} />
        <LockLoss isActive={activeChapter.id === 'loss'} />
        <Reacquisition isActive={activeChapter.id === 'reacquire'} />
        <SystemArchitecture isActive={activeChapter.id === 'system'} />
        <BenchmarkProof isActive={activeChapter.id === 'proof'} />
        <ClosingEpilogue isActive={activeChapter.id === 'closing'} />
      </main>
    </div>
  );
};

export default App;
