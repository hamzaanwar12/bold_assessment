import { useState } from "react";
import { RECRUITERS } from "./recruiters";
import { useCandidates } from "./useCandidates";
import { useDebouncedValue } from "./useDebouncedValue";

const STATUSES = ["active", "screening", "interviewing", "withdrawn"];
const PAGE_SIZE = 25;

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

  const isError = result.state === "error";
  const isLoading = result.state === "loading";
  const data = result.state === "ready" ? result.data : null;
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <section aria-labelledby="candidates-heading">
      <h2 id="candidates-heading">Candidates</h2>

      <div className="controls">
        <label>
          Recruiter
          <select
            value={recruiterId}
            onChange={(e) => handleRecruiterChange(e.target.value)}
          >
            {RECRUITERS.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </label>

        <label>
          Search
          <input
            type="text"
            value={searchInput}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Name, email, role..."
          />
        </label>

        <label>
          Status
          <select value={status} onChange={(e) => handleStatusChange(e.target.value)}>
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
      </div>

      {isError && (
        <p role="alert" className="error-banner">
          {result.status === 403
            ? "Not authorized: this Recruiter cannot view these Candidates."
            : "Something went wrong loading Candidates."}
        </p>
      )}

      {isLoading && <p aria-live="polite">Loading Candidates...</p>}

      {!isError && (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Region</th>
              <th>Desired role</th>
              <th>Status</th>
              <th>Applied date</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((c) => (
              <tr key={c.id}>
                <td>
                  {c.first_name} {c.last_name}
                </td>
                <td>{c.email}</td>
                <td>{c.region_code}</td>
                <td>{c.desired_role}</td>
                <td>{c.status}</td>
                <td>{c.applied_date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {!isError && data && data.items.length === 0 && !isLoading && (
        <p>No Candidates match the current search and filters.</p>
      )}

      {!isError && data && (
        <div className="pagination">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
          >
            Previous
          </button>
          <span>
            Page {data.page} of {totalPages} ({data.total} total)
          </span>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
          >
            Next
          </button>
        </div>
      )}
    </section>
  );
}
