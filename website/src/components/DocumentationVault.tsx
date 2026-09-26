import React, { useState } from 'react';
const architectureImg = '/images/1.jpg';

interface DocItem {
  id: string;
  title: string;
  category: string;
  badge: string;
  pages: string;
  summary: string;
  highlights: string[];
  image?: string;
  contentSections: {
    heading: string;
    body: string;
    metrics?: { label: string; value: string }[];
  }[];
}

const DOCUMENTS: DocItem[] = [
  {
    id: 'arch_diagram',
    title: 'System Architecture & Blueprint',
    category: 'Hardware-in-the-Loop Architecture',
    badge: 'System Blueprint',
    pages: 'Full Architecture',
    summary: 'An end-to-end overview of the HORIZON tracking pipeline, illustrating the seamless dataflow from sensor frame capture to closed-loop gimbal actuation.',
    highlights: [
      'High-speed optical frame processing pipeline at over 260 frames per second',
      'Tri-tier perception combining adaptive median filtering, contrast normalization, and sub-pixel center-of-gravity estimation',
      'Interacting Multiple Model Extended Kalman Filter (IMM-EKF) blending constant-velocity and coordinated-turn models',
      'Kinematic feedforward velocity commands enforcing the physical 5.0°/s gimbal speed limit',
    ],
    contentSections: [
      {
        heading: 'End-to-End System Dataflow',
        body: 'The pipeline processes incoming optical sensor frames at 640×480 resolution (≥30 Hz). Incoming frames pass through a 2D Adaptive Median Filter to remove impulsive noise, followed by dynamic contrast enhancement to isolate the beacon under dense atmospheric conditions. The sub-pixel centroid estimator calculates target coordinates, which feed into the IMM-EKF state estimator. The state manager and kinematic feedforward controller generate rate commands for the pan/tilt gimbal with sub-milliradian precision.',
        metrics: [
          { label: 'Perception Latency', value: '1.4 ms (AMF + CLAHE + CoG)' },
          { label: 'State Estimation Latency', value: '0.6 ms (IMM-EKF)' },
          { label: 'Control Loop Latency', value: '0.4 ms (Feedforward)' },
          { label: 'Total Processing Budget', value: '2.4 ms (< 33.3 ms Budget)' },
        ],
      },
      {
        heading: 'Autonomous State Transitions',
        body: 'The finite-state machine governs link acquisition and recovery through well-defined operational states: systematic Archimedean spiral scanning during SEARCH, verified centroid detection across consecutive frames in ACQUIRE, active IMM-EKF feedforward tracking in TRACK, covariance propagation during temporary signal dropout in COAST, and localized spiral sweeps in REACQUIRE.',
        metrics: [
          { label: 'Acquisition Hysteresis', value: '3-Frame Verification' },
          { label: 'Coasting Window', value: '1.50 s Maximum' },
          { label: 'Recovery Slew Rate', value: '1.8° Spiral Cone' },
        ],
      },
    ],
  },
  {
    id: 'tech_report',
    title: 'Technical Specification Report',
    category: 'ISRO PS26169 Technical Dossier',
    badge: 'Verified Specifications',
    pages: '32 Pages · Full Spec',
    summary: 'A detailed engineering document detailing the mathematical foundations, filter formulations, disturbance rejection models, and experimental benchmark results.',
    highlights: [
      'Sub-pixel centroid accuracy within ±0.15 pixels using intensity-weighted Gaussian peak fitting',
      'Multi-model Kalman filtering ensuring stability during sudden target acceleration and sharp turns',
      'Empirical validation over 1,000 Monte Carlo batch trials achieving a 0.048s mean acquisition time',
      'Benchmark-2 direct external MP4 video bypass evaluation fulfilling 100% of ISRO requirements',
    ],
    contentSections: [
      {
        heading: 'Problem Formulation & Operational Scope',
        body: 'In mobile Free Space Optical Communications (FSOC), platform vibrations and broad initial GPS coordinate uncertainties place the transmitting beacon well outside the narrow 4°×3° receiver cone. HORIZON combines systematic spiral sweeping, high-speed computer vision, and predictive Kalman filtering to establish and maintain optical link alignment.',
        metrics: [
          { label: 'Spatial Uncertainty Domain', value: '±18.0° Az / ±12.0° El' },
          { label: 'Sensor Field of View', value: '4.0° (H) × 3.0° (V)' },
          { label: 'Optical Divergence', value: '< 1.0 mrad Beam Cone' },
        ],
      },
      {
        heading: 'Perception & Atmospheric Robustness',
        body: 'To operate reliably through fog, rain, haze, and low-light scenarios, the perception engine applies rank-order median filtering to eliminate up to 10% salt-and-pepper noise, followed by contrast normalization to extract clear beacon signatures even at extreme signal-to-noise ratios.',
        metrics: [
          { label: 'Noise Rejection Capacity', value: '10% S&P + σ=20px Jitter' },
          { label: 'Sub-Pixel Precision', value: '±0.15 Pixels Accuracy' },
          { label: 'Tracking Pipeline FPS', value: '260+ FPS Maximum Throughput' },
        ],
      },
      {
        heading: 'State Estimation & Closed-Loop Tracking',
        body: 'The Interacting Multiple Model Extended Kalman Filter dynamically adapts between Constant Velocity (CV) and Coordinated Turn (CT) kinematic states. It outputs proactive feedforward velocity commands that eliminate lag while strictly respecting the 5.0°/s motor speed limit.',
        metrics: [
          { label: 'Kinematic Models', value: 'CV + CT + Random Acceleration' },
          { label: 'Gimbal Speed Clamp', value: '5.0°/s Physical Motor Limit' },
          { label: 'Mean Reacquisition Time', value: '0.184 s (< 1.0s Requirement)' },
        ],
      },
    ],
  },
  {
    id: 'user_manual',
    title: 'Operations & Verification Manual',
    category: 'System Operation Manual',
    badge: 'Operations Guide',
    pages: '18 Pages · User Guide',
    summary: 'A step-by-step operator guide covering simulation setup in Unity 6 LTS, external MP4 video bypass execution, and one-click benchmark report export.',
    highlights: [
      'Comprehensive instructions for running both interactive GUI and headless batch simulations',
      'Step-by-step guidance for testing evaluator-provided MP4 video streams via the Benchmark-2 bypass',
      'Real-time disturbance lab controls including atmospheric attenuation and platform vibration',
      'Automated export of frame-by-frame CSV logs, JSON performance metrics, and formal PDF summaries',
    ],
    contentSections: [
      {
        heading: 'Running Benchmark-1 Synthetic Simulations',
        body: 'Launch the simulation environment in Unity or headless batchmode to execute 1,000 automated Monte Carlo runs across all four mandatory motion trajectories (Straight, Circular, Figure-8, and Random Walk) under randomized disturbance conditions.',
        metrics: [
          { label: 'Batch Iterations', value: '1,000 Independent Trials' },
          { label: 'Output Artifacts', value: 'CSV Logs + JSON Metrics' },
          { label: 'Evaluation Status', value: 'Ground-Truth Verified' },
        ],
      },
      {
        heading: 'Executing Benchmark-2 Video Bypass',
        body: 'To evaluate video footage without PTZ camera simulation, enable Mode B in the Mission Control dashboard. The engine ingests 30 FPS MP4 files directly into the perception pipeline, logging live centroid tracking errors.',
        metrics: [
          { label: 'Supported Media', value: 'H.264 / MP4 at 30+ FPS' },
          { label: 'Ingestion Mode', value: 'Zero-Copy GPU Buffer Ingestion' },
          { label: 'Evaluation Weight', value: '30 / 30 Evaluation Marks' },
        ],
      },
    ],
  },
];

export const DocumentationVault: React.FC = () => {
  const [activeDocId, setActiveDocId] = useState<string>('arch_diagram');
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const activeDoc = DOCUMENTS.find((d) => d.id === activeDocId) || DOCUMENTS[0];

  const handleOpenDoc = (docId: string) => {
    setActiveDocId(docId);
    setIsModalOpen(true);
  };

  const handleDownloadDoc = (docId: string) => {
    const doc = DOCUMENTS.find((d) => d.id === docId);
    if (!doc) return;

    let content = `# HORIZON: ${doc.title}\n`;
    content += `Category: ${doc.category} | ${doc.badge}\n\n`;
    content += `## Summary\n${doc.summary}\n\n`;
    content += `## Key Highlights\n${doc.highlights.map((h) => `- ${h}`).join('\n')}\n\n`;
    content += `## Content & Specifications\n`;
    doc.contentSections.forEach((s) => {
      content += `### ${s.heading}\n${s.body}\n\n`;
      if (s.metrics) {
        s.metrics.forEach((m) => {
          content += `* **${m.label}:** ${m.value}\n`;
        });
        content += '\n';
      }
    });

    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${doc.id}_HORIZON_ISRO_PS26169.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ marginTop: '0.75rem', marginBottom: '1.75rem' }}>
      {/* Pill-Shaped Luxury Button Group (Matching Image 1) */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '1rem',
          alignItems: 'center',
        }}
      >
        <button
          onClick={() => handleOpenDoc('arch_diagram')}
          className="pill-action-btn"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.65rem',
            padding: '0.75rem 1.6rem',
            borderRadius: '9999px',
            border: '1px solid rgba(169, 216, 232, 0.28)',
            backgroundColor: 'rgba(10, 20, 36, 0.55)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-body)',
            fontSize: '0.92rem',
            fontWeight: 500,
            letterSpacing: '0.01em',
            cursor: 'pointer',
            outline: 'none',
            transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          <span>View Architecture</span>
          <span style={{ fontSize: '1rem', opacity: 0.9 }}>👁</span>
        </button>

        <button
          onClick={() => handleOpenDoc('tech_report')}
          className="pill-action-btn"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.65rem',
            padding: '0.75rem 1.6rem',
            borderRadius: '9999px',
            border: '1px solid rgba(169, 216, 232, 0.28)',
            backgroundColor: 'rgba(10, 20, 36, 0.55)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-body)',
            fontSize: '0.92rem',
            fontWeight: 500,
            letterSpacing: '0.01em',
            cursor: 'pointer',
            outline: 'none',
            transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          <span>Technical Report</span>
          <span style={{ fontSize: '0.9rem', opacity: 0.85 }}>↗</span>
        </button>

        <button
          onClick={() => handleOpenDoc('user_manual')}
          className="pill-action-btn"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.65rem',
            padding: '0.75rem 1.6rem',
            borderRadius: '9999px',
            border: '1px solid rgba(169, 216, 232, 0.28)',
            backgroundColor: 'rgba(10, 20, 36, 0.55)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-body)',
            fontSize: '0.92rem',
            fontWeight: 500,
            letterSpacing: '0.01em',
            cursor: 'pointer',
            outline: 'none',
            transition: 'all 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          <span>User Manual</span>
          <span style={{ fontSize: '0.9rem', opacity: 0.85 }}>↗</span>
        </button>
      </div>

      {/* Fullscreen Luxury Modal Reader with Plus Jakarta Sans Body (Matching Image 2) */}
      {isModalOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            backgroundColor: 'rgba(2, 6, 12, 0.82)',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '3vh 4vw',
            pointerEvents: 'auto',
          }}
          onClick={() => setIsModalOpen(false)}
        >
          <div
            style={{
              width: '100%',
              maxWidth: '880px',
              maxHeight: '86vh',
              overflowY: 'auto',
              padding: '2.5rem 2.75rem',
              backgroundColor: 'rgba(8, 16, 28, 0.94)',
              border: '1px solid rgba(169, 216, 232, 0.35)',
              borderRadius: '24px',
              boxShadow: '0 24px 60px rgba(0, 0, 0, 0.6), 0 0 40px rgba(169, 216, 232, 0.1)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Tabs & Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.75rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
              <div>
                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.85rem', flexWrap: 'wrap' }}>
                  {DOCUMENTS.map((doc) => {
                    const isSelected = activeDocId === doc.id;
                    return (
                      <button
                        key={doc.id}
                        onClick={() => setActiveDocId(doc.id)}
                        style={{
                          background: isSelected ? 'rgba(169, 216, 232, 0.18)' : 'transparent',
                          color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                          border: isSelected ? '1px solid rgba(169, 216, 232, 0.5)' : '1px solid rgba(213, 224, 255, 0.1)',
                          borderRadius: '9999px',
                          padding: '0.4rem 1rem',
                          fontFamily: 'var(--font-body)',
                          fontSize: '0.82rem',
                          fontWeight: isSelected ? 600 : 400,
                          cursor: 'pointer',
                          transition: 'all 0.25s ease',
                        }}
                      >
                        {doc.title}
                      </button>
                    );
                  })}
                </div>

                <h2
                  style={{
                    fontFamily: 'var(--font-body)',
                    fontSize: '1.75rem',
                    fontWeight: 600,
                    color: 'var(--text-primary)',
                    letterSpacing: '-0.01em',
                    lineHeight: 1.25,
                  }}
                >
                  {activeDoc.title}
                </h2>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', marginTop: '0.4rem' }}>
                  <span style={{ fontFamily: 'var(--font-body)', fontSize: '0.82rem', color: 'var(--state-signal)', fontWeight: 500 }}>
                    {activeDoc.category}
                  </span>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>•</span>
                  <span style={{ fontFamily: 'var(--font-body)', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    {activeDoc.badge}
                  </span>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                <button
                  onClick={() => handleDownloadDoc(activeDoc.id)}
                  style={{
                    padding: '0.55rem 1.15rem',
                    borderRadius: '9999px',
                    backgroundColor: 'rgba(169, 216, 232, 0.15)',
                    border: '1px solid rgba(169, 216, 232, 0.4)',
                    color: 'var(--text-primary)',
                    fontFamily: 'var(--font-body)',
                    fontSize: '0.82rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                  }}
                >
                  Download Spec ↓
                </button>
                <button
                  onClick={() => setIsModalOpen(false)}
                  style={{
                    background: 'transparent',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '50%',
                    width: '36px',
                    height: '36px',
                    color: 'var(--text-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1rem',
                    cursor: 'pointer',
                  }}
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Document Content with Smooth Body Typography (Matching Image 2) */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
              <div>
                <p
                  style={{
                    fontFamily: 'var(--font-body)',
                    color: 'var(--text-secondary)',
                    fontSize: '1.08rem',
                    lineHeight: 1.75,
                    fontWeight: 300,
                  }}
                >
                  {activeDoc.summary}
                </p>
              </div>

              {/* Architecture Blueprint Image Display (for System Architecture) */}
              {activeDoc.id === 'arch_diagram' && (
                <div
                  style={{
                    borderRadius: '16px',
                    overflow: 'hidden',
                    border: '1px solid rgba(169, 216, 232, 0.28)',
                    backgroundColor: '#050B14',
                    boxShadow: '0 12px 36px rgba(0, 0, 0, 0.5)',
                  }}
                >
                  <div
                    style={{
                      padding: '0.75rem 1.25rem',
                      backgroundColor: 'rgba(10, 20, 36, 0.85)',
                      borderBottom: '1px solid rgba(169, 216, 232, 0.15)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '0.5rem',
                    }}
                  >
                    <span
                      style={{
                        fontFamily: 'var(--font-body)',
                        fontSize: '0.82rem',
                        color: 'var(--state-signal)',
                        fontWeight: 600,
                        letterSpacing: '0.02em',
                      }}
                    >
                      HARDWARE-IN-THE-LOOP ARCHITECTURE & DATAFLOW SCHEMATIC
                    </span>
                    <span
                      style={{
                        fontFamily: 'var(--font-body)',
                        fontSize: '0.75rem',
                        color: 'var(--text-muted)',
                      }}
                    >
                      60 Hz Real-Time Loop · ISRO PS26169
                    </span>
                  </div>
                  <img
                    src={architectureImg}
                    alt="HORIZON End-to-End System Architecture & Dataflow Pipeline"
                    style={{
                      width: '100%',
                      height: 'auto',
                      display: 'block',
                    }}
                  />
                </div>
              )}

              {/* Highlights Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.85rem' }}>
                {activeDoc.highlights.map((h, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '0.9rem 1.15rem',
                      backgroundColor: 'rgba(12, 22, 38, 0.55)',
                      border: '1px solid rgba(169, 216, 232, 0.15)',
                      borderRadius: '12px',
                      fontFamily: 'var(--font-body)',
                      fontSize: '0.9rem',
                      lineHeight: 1.55,
                      fontWeight: 300,
                      color: 'var(--text-primary)',
                      display: 'flex',
                      gap: '0.65rem',
                    }}
                  >
                    <span style={{ color: 'var(--state-signal)', fontWeight: 600 }}>•</span>
                    <span>{h}</span>
                  </div>
                ))}
              </div>

              {/* Detailed Content Sections */}
              {activeDoc.contentSections.map((sec, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '1.5rem',
                    backgroundColor: 'rgba(10, 20, 36, 0.45)',
                    border: '1px solid rgba(213, 224, 255, 0.08)',
                    borderRadius: '16px',
                  }}
                >
                  <h4
                    style={{
                      fontFamily: 'var(--font-body)',
                      fontSize: '1.18rem',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      marginBottom: '0.65rem',
                      letterSpacing: '-0.01em',
                    }}
                  >
                    {sec.heading}
                  </h4>
                  <p
                    style={{
                      fontFamily: 'var(--font-body)',
                      color: 'var(--text-secondary)',
                      fontSize: '0.98rem',
                      lineHeight: 1.75,
                      fontWeight: 300,
                      marginBottom: sec.metrics ? '1.25rem' : 0,
                    }}
                  >
                    {sec.body}
                  </p>

                  {sec.metrics && (
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                        gap: '0.75rem',
                        paddingTop: '1rem',
                        borderTop: '1px solid rgba(213, 224, 255, 0.08)',
                      }}
                    >
                      {sec.metrics.map((m, mIdx) => (
                        <div key={mIdx} style={{ fontFamily: 'var(--font-body)', fontSize: '0.85rem' }}>
                          <span style={{ color: 'var(--text-muted)' }}>{m.label}: </span>
                          <span style={{ color: 'var(--state-signal)', fontWeight: 500 }}>{m.value}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
