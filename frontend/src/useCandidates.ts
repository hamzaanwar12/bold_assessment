import { useEffect, useRef, useState } from "react";

export interface Candidate {
  // The server's stable row identity. Key lists on this, never on
  // legacy_candidate_id: the source data reuses one legacy id across two
  // different people (ADR 0001), so it collides.
  id: number;
  legacy_candidate_id: string | null;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  region_code: string;
  desired_role: string;
  salary_expectation: number;
  applied_date: string;
  status: string;
  source: string;
  notes: string;
}

export interface CandidatesResponse {
  items: Candidate[];
  total: number;
  page: number;
  page_size: number;
}

export interface UseCandidatesParams {
  recruiterId: string;
  search: string;
  status: string;
  page: number;
  pageSize: number;
}

export type UseCandidatesResult =
  | { state: "loading" }
  | { state: "error"; status: number }
  | { state: "ready"; data: CandidatesResponse };

/**
 * The single data-fetching hook for the Candidate view. Uses `fetch` with an
 * AbortController so that switching Recruiter (or search/status/page) while a
 * request is in flight cannot let a stale response paint over newer state: each
 * call aborts the previous in-flight request before issuing the next.
 */
export function useCandidates(params: UseCandidatesParams): UseCandidatesResult {
  const { recruiterId, search, status, page, pageSize } = params;
  const [result, setResult] = useState<UseCandidatesResult>({ state: "loading" });
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setResult({ state: "loading" });

    const qs = new URLSearchParams();
    if (search) qs.set("search", search);
    if (status) qs.set("status", status);
    qs.set("page", String(page));
    qs.set("page_size", String(pageSize));

    fetch(`/api/v1/candidates?${qs.toString()}`, {
      headers: { "X-Recruiter-Id": recruiterId },
      signal: controller.signal,
    })
      .then(async (res) => {
        if (controller.signal.aborted) return;
        if (!res.ok) {
          setResult({ state: "error", status: res.status });
          return;
        }
        const data: CandidatesResponse = await res.json();
        // Re-check AFTER the await. Parsing the body yields control, and a
        // newer request can abort this controller in that window -- so a
        // check made only before the await still lets a superseded response
        // paint. That renders the PREVIOUS recruiter's Candidates, which is
        // indistinguishable from an authorization bug.
        if (controller.signal.aborted) return;
        setResult({ state: "ready", data });
      })
      .catch((err) => {
        if (controller.signal.aborted || err?.name === "AbortError") return;
        setResult({ state: "error", status: 0 });
      });

    return () => {
      controller.abort();
    };
  }, [recruiterId, search, status, page, pageSize]);

  return result;
}
