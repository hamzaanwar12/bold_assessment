import { SearchX, ShieldAlert } from "lucide-react";

export function ErrorBanner({ forbidden }: { forbidden: boolean }) {
  return (
    <p
      role="alert"
      className="flex items-start gap-3 rounded-2xl border border-rose-400/30 bg-rose-500/10 p-4 text-sm text-rose-200"
    >
      <ShieldAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-rose-300" />
      {forbidden
        ? "Not authorized: this Recruiter cannot view these Candidates."
        : "Something went wrong loading Candidates."}
    </p>
  );
}

export function EmptyState() {
  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-white/10 py-12 text-center">
      <SearchX aria-hidden="true" className="size-8 text-bold-sky" />
      <p className="text-sm text-slate-400">No Candidates match the current search and filters.</p>
    </div>
  );
}
