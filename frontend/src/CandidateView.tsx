import { lazy, Suspense, useState } from "react";
import { EmptyState, ErrorBanner } from "./components/Notices";
import { Pagination } from "./components/Pagination";
import { StatsBar } from "./components/StatsBar";
import { TableSkeleton } from "./components/TableSkeleton";
import { Toolbar } from "./components/Toolbar";
import { RECRUITERS } from "./recruiters";
import { useCandidates } from "./useCandidates";
import { useDebouncedValue } from "./useDebouncedValue";

const STATUSES = ["active", "screening", "interviewing", "withdrawn"];
const PAGE_SIZE = 25;

// The table (and the motion code it animates with) is its own chunk; the shell
// and controls paint first behind a static skeleton.
const CandidateTable = lazy(() =>
  import("./components/CandidateTable").then((m) => ({ default: m.CandidateTable })),
);

export function CandidateView() {
  const [recruiterId, setRecruiterId] = useState(RECRUITERS[0].id);
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const search = useDebouncedValue(searchInput, 300);

  const result = useCandidates({
    recruiterId,
    search,
    status,
    page,
    pageSize: PAGE_SIZE,
  });

  const handleRecruiterChange = (id: string) => {
    setRecruiterId(id);
    setPage(1);
  };

  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    setPage(1);
  };

  const handleStatusChange = (value: string) => {
    setStatus(value);
    setPage(1);
  };

  const recruiter = RECRUITERS.find((r) => r.id === recruiterId) ?? RECRUITERS[0];
  const isError = result.state === "error";
  const isLoading = result.state === "loading";
  const data = result.state === "ready" ? result.data : null;
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <section aria-labelledby="candidates-heading" className="space-y-6">
      <div className="flex items-end justify-between gap-4">
        <h2 id="candidates-heading" className="font-display text-2xl font-bold text-white">
          Candidates
        </h2>
        {isLoading && (
          <p aria-live="polite" className="flex items-center gap-2 text-sm text-bold-cyan">
            <span aria-hidden="true" className="size-2 animate-ping rounded-full bg-bold-cyan" />
            Loading Candidates...
          </p>
        )}
      </div>

      <StatsBar recruiter={recruiter} total={data?.total ?? null} />

      <div className="rounded-2xl border border-white/10 bg-bold-navy/40 p-4 shadow-glow backdrop-blur-md sm:p-5">
        <Toolbar
          recruiters={RECRUITERS}
          recruiterId={recruiterId}
          onRecruiterChange={handleRecruiterChange}
          search={searchInput}
          onSearchChange={handleSearchChange}
          statuses={STATUSES}
          status={status}
          onStatusChange={handleStatusChange}
        />
      </div>

      {isError && <ErrorBanner forbidden={result.status === 403} />}

      {!isError && (
        <Suspense fallback={<TableSkeleton />}>
          <CandidateTable items={data?.items ?? null} loading={isLoading} />
        </Suspense>
      )}

      {!isError && data && data.items.length === 0 && !isLoading && <EmptyState />}

      {!isError && data && (
        <Pagination
          page={data.page}
          totalPages={totalPages}
          total={data.total}
          onPrevious={() => setPage((p) => Math.max(1, p - 1))}
          onNext={() => setPage((p) => Math.min(totalPages, p + 1))}
        />
      )}
    </section>
  );
}
