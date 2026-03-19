import axiosInstance from "./axiosInstance";

export const evidenceAPI = {
  submit: async (payload) => {
    const { data } = await axiosInstance.post("/evidence/", payload);
    return data;
  },

  listByTask: async (taskId) => {
    const { data } = await axiosInstance.get(`/evidence/${taskId}`);
    return data;
  },

  listByChallenge: async (challengeId) => {
    const { data } = await axiosInstance.get(`/evidence/challenge/${challengeId}`);
    return data;
  },
};
