import { useEffect, useMemo, useState } from "react";
import { formatCountdown, msUntil } from "../utils/timeUtils";

export function useTimer(endTime) {
  const [remainingMs, setRemainingMs] = useState(() => msUntil(endTime));

  useEffect(() => {
    setRemainingMs(msUntil(endTime));
    if (!endTime) return undefined;

    const tick = () => setRemainingMs(msUntil(endTime));
    tick();
    const id = window.setInterval(tick, 1000);

    return () => window.clearInterval(id);
  }, [endTime]);

  const isExpired = remainingMs <= 0;
  const formatted = useMemo(() => formatCountdown(remainingMs), [remainingMs]);

  return { remainingMs, isExpired, formatted };
}
