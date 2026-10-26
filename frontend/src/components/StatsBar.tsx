import type { ReactNode } from "react";
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
          {total ?? "—"}
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
        <span className="font-display text-lg font-bold text-white">{recruiter.name}</span>
      </Stat>
    </dl>
  );
}

function Stat({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 backdrop-blur-sm">
      <dt className="text-xs font-semibold tracking-wide text-slate-400 uppercase">{label}</dt>
      <dd className="mt-2 flex min-h-9 items-center">{children}</dd>
    </div>
  );
}
