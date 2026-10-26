import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CandidateView } from "./CandidateView";

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
    ...init,
  });
}

const emptyPage = { items: [], total: 0, page: 1, page_size: 25 };

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("CandidateView recruiter switcher", () => {
  it("sends the switched recruiter's id as the X-Recruiter-Id header", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue(jsonResponse(emptyPage));

    const user = userEvent.setup();
    render(<CandidateView />);

    await waitFor(() => expect(fetchMock).toHaveBeenCalled());

    const initialCall = fetchMock.mock.calls.at(-1)!;
    const initialHeaders = (initialCall[1] as RequestInit).headers as Record<
      string,
      string
    >;
    expect(initialHeaders["X-Recruiter-Id"]).toBe("R-101");

    const select = screen.getByLabelText(/recruiter/i);
    await user.selectOptions(select, "R-103");

    await waitFor(() => {
      const lastCall = fetchMock.mock.calls.at(-1)!;
      const headers = (lastCall[1] as RequestInit).headers as Record<
        string,
        string
      >;
      expect(headers["X-Recruiter-Id"]).toBe("R-103");
    });
  });
});

describe("CandidateView 403 handling", () => {
  it("renders an error banner above a cleared table, not an empty-results message", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue(
      jsonResponse({ detail: "forbidden" }, { status: 403 }),
    );

    render(<CandidateView />);

    expect(await screen.findByText(/not authorized/i)).toBeInTheDocument();
    expect(screen.queryByRole("row", { name: /./ })).not.toBeInTheDocument();
  });
});

describe("CandidateView rendering", () => {
  it("renders candidate rows including accented and non-Latin names", async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValue(
      jsonResponse({
        items: [
          {
            legacy_candidate_id: "C-1",
            first_name: "Nguyễn",
            last_name: "Thị Hoa",
            email: "hoa@example.com",
            phone: "555-0100",
            region_code: "US-NE",
            desired_role: "Engineer",
            salary_expectation: 90000,
            applied_date: "2026-01-01",
            status: "active",
            source: "referral",
            notes: "",
          },
          {
            legacy_candidate_id: "C-2",
            first_name: "Jürgen",
            last_name: "Müller",
            email: "jurgen@example.com",
            phone: "555-0101",
            region_code: "US-NE",
            desired_role: "Analyst",
            salary_expectation: 80000,
            applied_date: "2026-01-02",
            status: "screening",
            source: "referral",
            notes: "",
          },
        ],
        total: 2,
        page: 1,
        page_size: 25,
      }),
    );

    render(<CandidateView />);

    expect(await screen.findByText(/Nguyễn Thị Hoa/)).toBeInTheDocument();
    expect(screen.getByText(/Jürgen Müller/)).toBeInTheDocument();
  });
});
