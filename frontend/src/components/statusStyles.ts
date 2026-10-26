const STYLES: Record<string, string> = {
  active: "bg-emerald-400/10 text-emerald-300 ring-emerald-400/30",
  screening: "bg-bold-sky/10 text-bold-sky ring-bold-sky/30",
  interviewing: "bg-bold-cyan/10 text-bold-cyan ring-bold-cyan/30",
  withdrawn: "bg-slate-400/10 text-slate-400 ring-slate-400/30",
};

// Unknown statuses get a neutral badge rather than a crash or a blank cell:
// the server owns the enum, and a new value should still render.
export const NEUTRAL_STATUS = "bg-white/5 text-slate-300 ring-white/15";

export function statusClasses(status: string): string {
  return STYLES[status] ?? NEUTRAL_STATUS;
}
