export function BrandMark() {
  return (
    <a href="/" className="flex items-center gap-2.5" aria-label="TechForce home">
      <svg viewBox="0 0 32 32" className="size-8" aria-hidden="true">
        <rect width="32" height="32" rx="8" className="fill-bold-cyan/10 stroke-bold-cyan/40" />
        <path d="M9 8h9a5 5 0 0 1 2.6 9.3A5.2 5.2 0 0 1 18.4 24H9z" className="fill-bold-cyan" />
        <path
          d="M13 12v3h4.5a1.5 1.5 0 0 0 0-3zm0 6v2.5h5a1.25 1.25 0 0 0 0-2.5z"
          className="fill-bold-ink"
        />
      </svg>
      <span className="font-display text-lg font-extrabold tracking-tight text-white">
        Tech<span className="text-bold-cyan">Force</span>
      </span>
    </a>
  );
}
