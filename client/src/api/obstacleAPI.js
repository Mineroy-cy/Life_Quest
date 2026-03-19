import axiosInstance from "./axiosInstance";

export const obstacleAPI = {
  create: async (payload) => {
    const { data } = await axiosInstance.post("/obstacles/", payload);
    return data;
  },

  listByTask: async (taskId) => {
    const { data } = await axiosInstance.get(`/obstacles/${taskId}`);
    return data;
  },

  updateSuggestion: async (obstacleId, payload) => {
    const { data } = await axiosInstance.patch(
      `/obstacles/${obstacleId}/suggestion`,
      payload,
    );
    return data;
  },
};
