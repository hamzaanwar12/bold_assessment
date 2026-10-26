import type { ReactNode } from "react";
import { BrandMark } from "./BrandMark";

const TAGLINE = ["Talent.", "Speed.", "Intelligence."];

/**
 * Page chrome modelled on the Bold Business landing page: navy-to-blue hero,
 * cyan accents, a faint grid. Purely presentational -- all data and state live
 * in CandidateView.
 */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative isolate min-h-dvh overflow-x-clip">
      <Backdrop />

      <header className="sticky top-0 z-30 border-b border-white/5 bg-bold-ink/70 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <BrandMark />
          <span className="hidden rounded-full border border-bold-cyan/30 bg-bold-cyan/10 px-3 py-1 text-xs font-medium text-bold-cyan sm:inline">
            Recruiter workspace
          </span>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 pt-12 pb-8 sm:px-6 sm:pt-16 lg:px-8">
        <p className="font-display text-xs font-semibold tracking-[0.25em] text-bold-cyan uppercase">
          TechForce · Recruiting operations
        </p>
        <h1 className="mt-4 max-w-3xl font-display text-4xl leading-[1.05] font-extrabold text-balance text-white sm:text-5xl lg:text-6xl">
          Your candidates, <span className="bg-gradient-to-r from-bold-cyan to-bold-sky bg-clip-text text-transparent">scoped to your regions.</span>
        </h1>
        <p className="mt-5 flex flex-wrap gap-x-3 font-display text-lg font-semibold text-slate-300 sm:text-xl">
          {TAGLINE.map((word) => (
            <span key={word}>{word}</span>
          ))}
        </p>
      </section>

      <main className="mx-auto max-w-7xl px-4 pb-16 sm:px-6 lg:px-8">{children}</main>

      <footer className="border-t border-white/5 py-6 text-center text-xs text-slate-500">
        TechForce take-home · Region scoping is enforced by PostgreSQL Row-Level Security, not this UI.
      </footer>
    </div>
  );
}

function Backdrop() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,var(--color-bold-deep)_0%,var(--color-bold-navy)_35%,var(--color-bold-ink)_75%)]" />
      <div className="absolute inset-0 bg-[linear-gradient(to_right,rgb(255_255_255/0.04)_1px,transparent_1px),linear-gradient(to_bottom,rgb(255_255_255/0.04)_1px,transparent_1px)] bg-[size:56px_56px] [mask-image:radial-gradient(ellipse_at_top,black_30%,transparent_75%)]" />
      <div data-orb className="absolute -top-40 -left-32 size-[28rem] rounded-full bg-bold-blue/40 blur-3xl" />
      <div data-orb className="absolute top-10 -right-40 size-[24rem] rounded-full bg-bold-cyan/20 blur-3xl" />
    </div>
  );
}
