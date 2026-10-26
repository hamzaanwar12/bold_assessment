export function RegionChip({ code }: { code: string }) {
  return (
    <span className="inline-flex items-center rounded-md bg-bold-blue/15 px-2 py-0.5 font-mono text-xs font-medium text-bold-sky ring-1 ring-bold-blue/30 ring-inset">
      {code}
    </span>
  );
}
