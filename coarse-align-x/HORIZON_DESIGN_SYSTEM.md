# HORIZON Design System Specification (As-Built)

## 1. Design System Philosophy & Principles

The HORIZON Design System is engineered for mission-critical optical satellite tracking and Free-Space Optical Communications (FSOC) pointing applications. The aesthetic language prioritizes immediate visual clarity, high telemetry legibility, and restraint.

### Key Principles:
1. **Instrument-Grade Neutral Base**: Replaces stock dark theme blue tints with true neutral dark surfaces (`#0A0A0B`, `#16161A`, `#202024`) to eliminate visual fatigue during extended operations.
2. **Restricted Semantic Palette**: Colors carry strict functional meanings. Color is never used purely for decoration.
3. **Multi-Sensory Accessibility**: Every state transition (SEARCH, ACQUIRE, TRACK, DEGRADED, REACQUIRE) is communicated through color **and** explicit text labels, icons, or shape differences.
4. **Strict Telemetry & Unit Scoping**: Monospace fonts (`JetBrains Mono`) appear exclusively on dynamic telemetry metrics. Grounded physical units (`rad`, `µrad`, `px`, `Hz`, `dB`, `ms`) are rendered adjacent to all numerical readouts.
5. **Fixed Layout & Spacing**: Built on a strict 8px spatial grid (`SPACING_4` through `SPACING_64`) to prevent visual drift across screens.

---

## 2. Color System & Semantic Tokens

### Neutral Surfaces
| Token | Hex Value | Intended Usage |
| :--- | :--- | :--- |
| `COLOR_VOID` | `#0A0A0B` | Canvas base background, true neutral dark |
| `COLOR_FIELD` | `#16161A` | Primary container & panel background |
| `COLOR_FIELD_RAISED` | `#202024` | Elevated controls, popovers, active selection states |
| `COLOR_HAIRLINE_BORDER` | `rgba(255,255,255,0.08)` / `#26262B` | Hairline panel boundaries (1px) |

### Neutral Text
| Token | Hex Value | Intended Usage |
| :--- | :--- | :--- |
| `COLOR_TEXT_PRIMARY` | `#F2F2F4` | Primary titles, value readouts, key labels |
| `COLOR_TEXT_SECONDARY` | `#8E8E96` | Subtitles, field labels, units, muted metadata |

### Semantic State Colors
| Token | Hex Value | Intended Usage | Multi-Sensory Accompaniment |
| :--- | :--- | :--- | :--- |
| `COLOR_LOCK_CYAN` | `#7FD4E8` | Engineering focus, active selection, normal telemetry | Icon: `[+]` / Target Reticle |
| `COLOR_CONFIRM_GREEN` | `#6FE8A8` | Confirmed TRACK state, pass verification | Icon: `[✓]` / Solid Border |
| `COLOR_DISTURBANCE_AMBER` | `#E8A15C` | DEGRADED state, active disturbance, warning | Icon: `[!]` / Dashed Border |
| `COLOR_LOST_RED` | `#E86F7F` | SEARCH state, track lost, error condition | Icon: `[✕]` / Pulsing Outline |

---

## 3. Typography & Scoping Rules

### Font Families
- **Headline Font**: `'Space Grotesk'`, `'Bricolage Grotesque'`, `sans-serif` (Screen titles, section headers, mode names)
- **Telemetry Font**: `'JetBrains Mono'`, `'Space Mono'`, `'Courier New'`, `monospace` (Numerical values, matrices, coordinates, timestamps)
- **Body Font**: `'General Sans'`, `sans-serif` (Field labels, descriptions, table contents)

### Type Scale
| Token | Size | Application |
| :--- | :--- | :--- |
| `TYPE_SCALE_MICRO` | `12px` | Badges, status tags, unit labels, table headers |
| `TYPE_SCALE_BODY` | `14px` | Standard UI text, list items, configuration labels |
| `TYPE_SCALE_EMPHASIZED` | `16px` | Interactive buttons, mode tabs, key metrics |
| `TYPE_SCALE_SECTION` | `20px` | Panel headers, card title bars |
| `TYPE_SCALE_TITLE` | `28px` | Screen primary headers |
| `TYPE_SCALE_HERO` | `40px` | Live hero metric counters (e.g. tracking error RMS) |

---

## 4. Spacing Scale & Layout Grid

All padding, margins, and gaps must strictly use approved 8px spatial multiples:

```
SPACING_4  =  4px  (Tight internal element gaps)
SPACING_8  =  8px  (Standard element padding / row gap)
SPACING_12 = 12px  (Control internal padding)
SPACING_16 = 16px  (Container inner padding)
SPACING_24 = 24px  (Inter-card layout spacing)
SPACING_32 = 32px  (Section separator margins)
SPACING_48 = 48px  (Major structural divisions)
SPACING_64 = 64px  (Screen-level hero spacing)
```

---

## 5. Motion Tokens & Easing

Transition durations are strictly timed to maintain application responsiveness:

| Token | Duration | Purpose |
| :--- | :--- | :--- |
| `DURATION_MICRO_MS` | `120ms` | Value tickers, hover highlights, micro-label shifts |
| `DURATION_COMPONENT_MS` | `200ms` | Panel collapse/expand, status state badge transitions |
| `DURATION_SCREEN_MS` | `320ms` | Screen mode switching across the Application Shell |

- **Easing Function**: Decelerating cubic-bezier curve (`QEasingCurve.OutCubic` / `cubic-bezier(0.4, 0.0, 0.2, 1)`) applied to all Qt animations.

---

## 6. Shared Component Primitives

The design system provides standardized shared widgets (`simulator/ui/components/`):

1. `CardWidget`: Container frame with neutral dark background (`#16161A`), hairline border (`rgba(255,255,255,0.08)`), and standardized padding.
2. `MetricBadge`: High-density telemetry readout widget with explicit primary label, monospace numerical value, and explicit physical unit.
3. `PATStateIndicator`: Multi-sensory PAT state indicator pairing state color with state badge text and state icon glyph.
4. `StatusBadge`: General purpose state badge with accessibility icon and color.
5. `PrimaryButton` & `SecondaryButton`: Styled buttons adhering to accessibility focus states (`focusInEvent` / `focusOutEvent` styling).
