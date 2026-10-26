import type { ReactNode } from "react";

// Native <label> wrapping native controls: accessible names come for free and
// tests can keep finding controls by label text.
export function Field({ label, icon, children }: { label: string; icon?: ReactNode; children: ReactNode }) {
  return (
    <label className="group flex min-w-0 flex-1 flex-col gap-1.5">
      <span className="flex items-center gap-1.5 text-xs font-semibold tracking-wide text-slate-400 uppercase">
        {icon}
        {label}
      </span>
      {children}
    </label>
  );
}

export const controlClasses =
  "h-11 w-full rounded-xl border border-white/10 bg-white/5 px-3.5 text-sm text-white placeholder:text-slate-500 transition-colors hover:border-white/20 focus:border-bold-cyan/60 focus:bg-white/[0.07] focus:outline-none [&>option]:bg-bold-navy";
