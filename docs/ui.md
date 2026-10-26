# Recruiter view — UI guide

How the frontend is styled and animated, and the rules that keep it testable.
Read this before changing anything under `frontend/src/components/`.

## Stack

| Concern | Tool | Where |
|---|---|---|
| Styling | Tailwind CSS v4 (`@tailwindcss/vite`) | utilities in components; tokens in `src/index.css` |
| Hero intro, background, parallax | GSAP + ScrollTrigger | `src/useHeroAnimation.ts` |
| List / banner / switcher transitions | Motion (Framer Motion) via `LazyMotion` + `m.*` | `App.tsx`, `components/*` |
| Icons | `lucide-react` | components |

There are no hand-written component stylesheets. `index.css` holds only the
`@theme` tokens and a small base layer. Why this stack: [ADR 0003](adr/0003-tailwind-motion-gsap.md).

## Design tokens

Lifted from the boldbusiness.com stylesheet so the view reads as part of the same
product family.

| Token | Value | Used for |
|---|---|---|
| `bold-navy` | `#001654` | panels, hero mid-tone |
| `bold-deep` | `#002079` | hero top |
| `bold-blue` | `#003BDF` | region chips, avatar gradient, orbs |
| `bold-sky` | `#789BFE` | secondary accent, "screening" |
| `bold-cyan` | `#06E5EC` | primary accent, focus ring, "interviewing" |
| `bold-ink` | `#0B1230` | page background |
| `font-display` | Montserrat | headings, numbers |
| `font-sans` | Inter | body |

Add a colour by adding a token, never a raw hex in a component.

## Component map

```
App                     LazyMotion + MotionConfig (reduced motion = user)
└─ AppShell             header, GSAP hero, backdrop, <main>, footer
   └─ CandidateView     ALL state + useCandidates (unchanged data layer)
      ├─ StatsBar       matching total (CountUp), recruiter regions, "viewing as"
      ├─ Toolbar        Recruiter / Search / Status (native controls in <label>)
      ├─ ErrorBanner    role="alert", 403 vs generic text
      ├─ CandidateTable lazy chunk; Suspense fallback = TableSkeleton
      ├─ EmptyState
      └─ Pagination
```

Presentational components take props and hold no fetch state. If a change needs
new data, it goes through `CandidateView` and `useCandidates`, not into a component.

## Responsive behaviour

- Breakpoint `sm` (640px) is the only layout switch.
- The candidate table is **one `<table>` at every width**. Below `sm`, `max-sm:`
  utilities turn rows into stacked cards, and each cell shows its column name from
  `data-label` via a `before:` pseudo-element.
- Do not add a second "mobile list". It would put every name in the DOM twice:
  screen readers would read it twice and `getByText` tests would find duplicates.

## Motion rules

- `motionAllowed()` (`src/motionPrefs.ts`) is the single switch. It is false for
  `prefers-reduced-motion: reduce` and under jsdom (no `matchMedia`), so tests
  never wait on animation.
- GSAP is imported with dynamic `import()` only when motion is allowed. Targets
  are `data-hero-*` / `data-orb` / `data-parallax` attributes, never class names.
- Use `m.*`, not `motion.*`. `<LazyMotion strict>` throws if a full `motion`
  component sneaks in and pulls the engine into the main bundle.
- Keep list staggers capped (`rowDelay`), so a full page settles in under a second.

## Bundle budget

Last measured with `npm run build`:

| Chunk | Size |
|---|---|
| main | 284 kB |
| `motionFeatures` | 47 kB |
| `gsap` | 70 kB |
| `ScrollTrigger` | 43 kB |
| `CandidateTable` | 3 kB |

If the main chunk grows noticeably, find out why before merging.

## Contract with the tests

These must survive any restyle, because `CandidateView.test.tsx` depends on them:

- labels `Recruiter`, `Search`, `Status` on native controls
- the 403 text "Not authorized: …" inside `role="alert"`
- the table is absent (no rows) in the error state
- each name rendered once, as one text run (`{first} {last}`)
