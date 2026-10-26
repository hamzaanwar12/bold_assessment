import { useEffect, useRef, useState } from "react";
import { motionAllowed } from "../motionPrefs";

const DURATION_MS = 600;

// Counts from the previous value to the new one with an ease-out curve;
// renders the final number immediately when motion is off.
export function CountUp({ value }: { value: number }) {
  const [shown, setShown] = useState(value);
  const from = useRef(value);

  useEffect(() => {
    const start = from.current;
    from.current = value;
    if (!motionAllowed() || start === value) return;

    let frame = 0;
    const t0 = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - t0) / DURATION_MS);
      setShown(Math.round(start + (value - start) * (1 - (1 - t) ** 3)));
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value]);

  return <>{motionAllowed() ? shown : value}</>;
}
