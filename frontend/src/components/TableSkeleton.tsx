// Static (non-lazy) placeholder: shown as the Suspense fallback while the
// CandidateTable chunk loads, and by the table itself while data loads.
import { COLUMNS } from "./columns";

export function SkeletonRow() {
  return (
    <tr aria-hidden="true" className="max-sm:block max-sm:rounded-xl max-sm:border max-sm:border-white/10 max-sm:p-4">
      {COLUMNS.map((c) => (
        <td key={c} className="px-4 py-4 max-sm:block max-sm:px-0 max-sm:py-1.5">
          <span className="block h-3 w-full max-w-40 animate-pulse rounded bg-white/10" />
        </td>
      ))}
    </tr>
  );
}

export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03]">
      <table className="w-full max-sm:block">
        <tbody className="max-sm:block max-sm:space-y-3 max-sm:p-3">
          {Array.from({ length: rows }, (_, i) => (
            <SkeletonRow key={i} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
