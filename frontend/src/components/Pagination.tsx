import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  page: number;
  totalPages: number;
  total: number;
  onPrevious: () => void;
  onNext: () => void;
}

const button =
  "inline-flex h-10 items-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-medium text-white transition hover:border-bold-cyan/50 hover:bg-bold-cyan/10 disabled:pointer-events-none disabled:opacity-40";

export function Pagination({ page, totalPages, total, onPrevious, onNext }: PaginationProps) {
  return (
    <nav aria-label="Pagination" className="flex flex-col items-center justify-between gap-3 sm:flex-row">
      <span className="text-sm text-slate-400 tabular-nums">
        Page {page} of {totalPages} ({total} total)
      </span>
      <div className="flex gap-2">
        <button type="button" className={button} onClick={onPrevious} disabled={page <= 1}>
          <ChevronLeft aria-hidden="true" className="size-4" />
          Previous
        </button>
        <button type="button" className={button} onClick={onNext} disabled={page >= totalPages}>
          Next
          <ChevronRight aria-hidden="true" className="size-4" />
        </button>
      </div>
    </nav>
  );
}
