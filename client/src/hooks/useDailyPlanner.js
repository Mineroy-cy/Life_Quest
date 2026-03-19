import { useState } from "react";
import { taskAPI } from "../api/taskAPI";

export function useDailyPlanner() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const getRecommendations = async (availableMinutes) => {
    try {
      setLoading(true);
      setError("");
      return await taskAPI.getTimeAllocation(availableMinutes);
    } catch (err) {
      setError(err.message);
      return { tasks: [] };
    } finally {
      setLoading(false);
    }
  };

  return { getRecommendations, loading, error };
}
