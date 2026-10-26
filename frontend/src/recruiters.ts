// Fixture roster — matches data/recruiters.csv. No Recruiter management endpoint
// exists; this list drives the switcher only.
export interface RecruiterOption {
  id: string;
  name: string;
}

export const RECRUITERS: RecruiterOption[] = [
  { id: "R-101", name: "Dana Whitmore" },
  { id: "R-102", name: "Caleb Nguyen" },
  { id: "R-103", name: "Marisol Vega" },
  { id: "R-104", name: "Jordan Blake" },
  { id: "R-105", name: "Tessa Iqbal" },
];
