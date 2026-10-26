import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";
import { NEUTRAL_STATUS, statusClasses } from "./statusStyles";

describe("StatusBadge", () => {
  it("gives each canonical status its own style", () => {
    const styles = ["active", "screening", "interviewing", "withdrawn"].map(statusClasses);
    expect(new Set(styles).size).toBe(4);
    expect(styles).not.toContain(NEUTRAL_STATUS);
  });

  it("falls back to a neutral badge for a status the UI doesn't know", () => {
    expect(statusClasses("on_hold")).toBe(NEUTRAL_STATUS);
    render(<StatusBadge status="on_hold" />);
    expect(screen.getByText("on_hold")).toBeInTheDocument();
  });
});
