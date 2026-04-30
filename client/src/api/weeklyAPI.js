import axiosInstance from "./axiosInstance";

export const weeklyAPI = {
  getActive: async (refreshIfStale = true) => {
    const { data } = await axiosInstance.get("/weekly/active", {
      params: { refresh_if_stale: refreshIfStale },
    });
    return data;
  },

  startWeek: async (payload = { goal_count: 3, challenges_per_goal: 6 }) => {
    const { data } = await axiosInstance.post("/weekly/start", payload);
    return data;
  },

  endWeek: async () => {
    const { data } = await axiosInstance.post("/weekly/end");
    return data;
  },

  refreshWeek: async () => {
    const { data } = await axiosInstance.post("/weekly/refresh");
    return data;
  },

  updateChallengeStatus: async (payload) => {
    const { data } = await axiosInstance.patch("/weekly/challenge-status", payload);
    return data;
  },
};
