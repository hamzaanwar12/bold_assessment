// Single switch for "should anything animate?". False under jsdom (no
// matchMedia) so tests stay deterministic, and false for users who ask the OS
// for reduced motion.
export function motionAllowed(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
