import axiosInstance from "./axiosInstance";

export const projectAPI = {
  list: async () => {
    const { data } = await axiosInstance.get("/projects/");
    return data;
  },

  create: async (payload) => {
    const { data } = await axiosInstance.post("/projects/", payload);
    return data;
  },

  getById: async (projectId) => {
    const { data } = await axiosInstance.get(`/projects/${projectId}`);
    return data;
  },

  getProgress: async (projectId) => {
    const { data } = await axiosInstance.get(`/projects/${projectId}/progress`);
    return data;
  },

  updateDescription: async (projectId, description) => {
    const { data } = await axiosInstance.patch(`/projects/${projectId}/description`, {
      description,
    });
    return data;
  },

  updateTimeline: async (projectId, payload) => {
    const { data } = await axiosInstance.patch(`/projects/${projectId}/timeline`, payload);
    return data;
  },

  getDifficultyScore: async (projectId) => {
    const { data } = await axiosInstance.get(`/projects/${projectId}/difficulty-score`);
    return data;
  },

  remove: async (projectId) => {
    const { data } = await axiosInstance.delete(`/projects/${projectId}`);
    return data;
  },
};
