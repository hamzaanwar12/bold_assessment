// Fixture roster — matches data/recruiters.csv. No Recruiter management endpoint
// exists; this list drives the switcher only. `regions` is display-only context
// for the switcher: the server never reads it, and scoping is enforced by RLS
// whatever this file says.
export interface RecruiterOption {
  id: string;
  name: string;
  regions: string[] | "all";
}

export const RECRUITERS: RecruiterOption[] = [
  { id: "R-101", name: "Dana Whitmore", regions: "all" },
  { id: "R-102", name: "Caleb Nguyen", regions: ["US-MW", "US-NE"] },
  { id: "R-103", name: "Marisol Vega", regions: ["PH-MNL", "CO-BOG"] },
  { id: "R-104", name: "Jordan Blake", regions: ["US-W", "US-SE"] },
  { id: "R-105", name: "Tessa Iqbal", regions: ["US-NE"] },
];
