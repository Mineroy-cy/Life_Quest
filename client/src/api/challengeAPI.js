import axiosInstance from "./axiosInstance";

export const challengeAPI = {
  create: async (payload) => {
    const { data } = await axiosInstance.post("/challenges/", payload);
    return data;
  },

  getDailyByProject: async (projectId, availableMinutes) => {
    const params =
      availableMinutes && Number(availableMinutes) > 0
        ? { available_minutes: Number(availableMinutes) }
        : undefined;

    const { data } = await axiosInstance.get(`/challenges/project/${projectId}/daily`, {
      params,
    });
    return data;
  },

  updateProofConfig: async (challengeId, payload) => {
    const { data } = await axiosInstance.patch(
      `/challenges/${challengeId}/proof-config`,
      payload,
    );
    return data;
  },

  getDailyPriority: async (availableMinutes) => {
    const { data } = await axiosInstance.get("/challenges/daily-priority", {
      params: { available_minutes: Number(availableMinutes) },
    });
    return data;
  },

  accept: async (challengeId, payload) => {
    const { data } = await axiosInstance.patch(`/challenges/${challengeId}/accept`, payload);
    return data;
  },

  activeByProject: async () => {
    const { data } = await axiosInstance.get("/challenges/active-by-project");
    return data;
  },

  updateTaskStatus: async (challengeId, payload) => {
    const { data } = await axiosInstance.patch(`/challenges/${challengeId}/tasks-status`, payload);
    return data;
  },
};
