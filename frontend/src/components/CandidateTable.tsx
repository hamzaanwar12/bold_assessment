import type { Candidate } from "../useCandidates";
import { RegionChip } from "./RegionChip";
import { StatusBadge } from "./StatusBadge";

const COLUMNS = ["Name", "Email", "Region", "Desired role", "Status", "Applied date"];
const SKELETON_ROWS = 6;

// One <table> for every viewport. Below `sm` it restyles into stacked cards
// (each cell labels itself via data-label) instead of rendering a second card
// list -- two copies of every name would confuse screen readers and tests.
const cell = "px-4 py-3 align-middle max-sm:flex max-sm:items-center max-sm:justify-between max-sm:gap-4 max-sm:px-0 max-sm:py-1.5 max-sm:before:text-xs max-sm:before:font-semibold max-sm:before:text-slate-500 max-sm:before:uppercase max-sm:before:content-[attr(data-label)]";

interface CandidateTableProps {
  items: Candidate[] | null;
  loading: boolean;
}

export function CandidateTable({ items, loading }: CandidateTableProps) {
  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-sm">
      <table className="w-full text-left text-sm max-sm:block">
        <thead className="border-b border-white/10 bg-white/[0.03] max-sm:sr-only">
          <tr>
            {COLUMNS.map((c) => (
              <th key={c} scope="col" className="px-4 py-3 text-xs font-semibold tracking-wide text-slate-400 uppercase">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5 max-sm:block max-sm:space-y-3 max-sm:divide-y-0 max-sm:p-3">
          {loading && !items
            ? Array.from({ length: SKELETON_ROWS }, (_, i) => <SkeletonRow key={i} />)
            : items?.map((c) => <CandidateRow key={c.id} candidate={c} />)}
        </tbody>
      </table>
    </div>
  );
}

export function CandidateRow({ candidate: c }: { candidate: Candidate }) {
  return (
    <tr className="transition-colors hover:bg-bold-cyan/[0.04] max-sm:block max-sm:rounded-xl max-sm:border max-sm:border-white/10 max-sm:bg-white/[0.03] max-sm:p-4">
      <td data-label="Name" className={`${cell} max-sm:before:hidden`}>
        <span className="flex items-center gap-3">
          <Initials first={c.first_name} last={c.last_name} />
          <span className="font-medium text-white">
            {c.first_name} {c.last_name}
          </span>
        </span>
      </td>
      <td data-label="Email" className={`${cell} text-slate-300 max-sm:break-all`}>{c.email}</td>
      <td data-label="Region" className={cell}>
        <RegionChip code={c.region_code} />
      </td>
      <td data-label="Desired role" className={`${cell} text-slate-300`}>{c.desired_role}</td>
      <td data-label="Status" className={cell}>
        <StatusBadge status={c.status} />
      </td>
      <td data-label="Applied date" className={`${cell} text-slate-400 tabular-nums`}>{c.applied_date}</td>
    </tr>
  );
}

// Array.from splits by code point, so names outside the BMP don't produce a
// broken half surrogate pair.
function Initials({ first, last }: { first: string; last: string }) {
  const text = (Array.from(first)[0] ?? "") + (Array.from(last)[0] ?? "");
  return (
    <span
      aria-hidden="true"
      className="grid size-9 shrink-0 place-items-center rounded-full bg-gradient-to-br from-bold-blue to-bold-cyan/70 font-display text-xs font-bold text-white"
    >
      {text.toUpperCase()}
    </span>
  );
}

function SkeletonRow() {
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
