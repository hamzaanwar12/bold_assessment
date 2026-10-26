# 3. Tailwind for styling, Motion + GSAP for animation, both kept off the critical path

Date: 2026-10-26

## Status

Accepted

## Context

The recruiter view shipped with minimal CSS (the brief: "we're not grading CSS").
To demo it next to the Bold Business site, it needs that site's look: a navy/cyan
palette, landing-page hero, animation. The risks are:

- styling that only its author can maintain
- animation that slows first paint or makes tests flaky
- a restyle that quietly changes behaviour

## Decision

- **Tailwind v4** with the palette as `@theme` tokens. Design decisions live in one
  block; components use utilities only. No CSS-in-JS runtime, and no component
  library whose markup would replace our native, labelled controls.
- **Motion (Framer Motion)** for React-state-driven transitions (rows, banner,
  recruiter switch), loaded through `LazyMotion` so the engine is an async chunk.
- **GSAP** for the timeline-style hero intro and the scroll parallax, which are
  awkward to express as React state. Loaded via dynamic `import()` and only when
  the user allows motion. `@gsap/react` is not used, because `useGSAP` requires a
  static import.
- `CandidateTable` is `React.lazy` behind a static skeleton.
- Data flow (`useCandidates`, `CandidateView` state) is not touched by any of this.

## Consequences

Good:
- The palette lives in one place.
- Main chunk is 284 kB; animation code (~160 kB) loads after first paint.
- Reduced-motion users and the test environment get a static UI.
- All original tests pass unmodified.

Cost:
- Two animation libraries. This is acceptable because they don't overlap: GSAP
  owns the hero, Motion owns React state transitions. A third animation use goes
  to Motion unless it is a timeline.
- Long `className` strings. Repeated ones are hoisted into constants (`cell`,
  `controlClasses`, `button`) rather than abstracted into wrapper components.
