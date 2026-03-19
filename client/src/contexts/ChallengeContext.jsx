import { createContext, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "life-quest-active-challenge";
const DAILY_TIME_KEY = "life-quest-daily-minutes";

const ChallengeContext = createContext(null);

function loadJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (_err) {
    return fallback;
  }
}

export function ChallengeProvider({ children }) {
  const [activeChallenge, setActiveChallengeState] = useState(() =>
    loadJson(STORAGE_KEY, null),
  );
  const [dailyMinutes, setDailyMinutesState] = useState(() =>
    loadJson(DAILY_TIME_KEY, 60),
  );

  const setActiveChallenge = (challenge) => {
    setActiveChallengeState(challenge);
    try {
      if (!challenge) {
        localStorage.removeItem(STORAGE_KEY);
      } else {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(challenge));
      }
    } catch (_err) {
      // Ignore storage failures.
    }
  };

  const setDailyMinutes = (minutes) => {
    const normalized = Number(minutes) || 0;
    setDailyMinutesState(normalized);
    try {
      localStorage.setItem(DAILY_TIME_KEY, JSON.stringify(normalized));
    } catch (_err) {
      // Ignore storage failures.
    }
  };

  useEffect(() => {
    const handleStorage = (event) => {
      if (event.key === STORAGE_KEY) {
        setActiveChallengeState(loadJson(STORAGE_KEY, null));
      }
      if (event.key === DAILY_TIME_KEY) {
        setDailyMinutesState(loadJson(DAILY_TIME_KEY, 60));
      }
    };

    window.addEventListener("storage", handleStorage);
    return () => window.removeEventListener("storage", handleStorage);
  }, []);

  const value = useMemo(
    () => ({
      activeChallenge,
      setActiveChallenge,
      dailyMinutes,
      setDailyMinutes,
    }),
    [activeChallenge, dailyMinutes],
  );

  return (
    <ChallengeContext.Provider value={value}>{children}</ChallengeContext.Provider>
  );
}

export function useChallengeContext() {
  const ctx = useContext(ChallengeContext);
  if (!ctx) {
    throw new Error("useChallengeContext must be used inside ChallengeProvider");
  }
  return ctx;
}
