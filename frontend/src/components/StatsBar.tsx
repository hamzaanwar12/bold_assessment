import { AnimatePresence, m } from "motion/react";
import type { ReactNode } from "react";
import { CountUp } from "./CountUp";
import type { RecruiterOption } from "../recruiters";
import { RegionChip } from "./RegionChip";

interface StatsBarProps {
  recruiter: RecruiterOption;
  total: number | null;
}

export function StatsBar({ recruiter, total }: StatsBarProps) {
  return (
    <dl className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <Stat label="Matching candidates">
        <span className="font-display text-3xl font-extrabold text-white tabular-nums">
          {total === null ? "—" : <CountUp value={total} />}
        </span>
      </Stat>
      <Stat label="Visible regions">
        {recruiter.regions === "all" ? (
          <span className="font-display text-lg font-bold text-bold-cyan">All regions · Admin</span>
        ) : (
          <span className="flex flex-wrap gap-1.5">
            {recruiter.regions.map((r) => (
              <RegionChip key={r} code={r} />
            ))}
          </span>
        )}
      </Stat>
      <Stat label="Viewing as">
        <AnimatePresence mode="wait" initial={false}>
          <m.span
            key={recruiter.id}
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -12 }}
            transition={{ duration: 0.2 }}
            className="font-display text-lg font-bold text-white"
          >
            {recruiter.name}
          </m.span>
        </AnimatePresence>
      </Stat>
    </dl>
  );
}

function Stat({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 backdrop-blur-sm transition duration-300 hover:-translate-y-0.5 hover:border-bold-cyan/30 hover:shadow-glow">
      <dt className="text-xs font-semibold tracking-wide text-slate-400 uppercase">{label}</dt>
      <dd className="mt-2 flex min-h-9 items-center">{children}</dd>
    </div>
  );
}
