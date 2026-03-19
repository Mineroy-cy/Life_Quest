import { useEffect, useState } from "react";
import { challengeAPI } from "../api/challengeAPI";

export function useChallenges(projectId, availableMinutes) {
  const [dailyChallenge, setDailyChallenge] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!projectId) return;

    const run = async () => {
      try {
        setLoading(true);
        setError("");
        const data = await challengeAPI.getDailyByProject(projectId, availableMinutes);
        setDailyChallenge(data?.challenge || null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    run();
  }, [projectId, availableMinutes]);

  return { dailyChallenge, setDailyChallenge, loading, error };
}
