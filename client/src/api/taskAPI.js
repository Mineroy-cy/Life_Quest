import axiosInstance from "./axiosInstance";

export const taskAPI = {
  listByProject: async (projectId) => {
    const { data } = await axiosInstance.get(`/tasks/${projectId}`);
    return data;
  },

  groupedByProject: async () => {
    const { data } = await axiosInstance.get("/tasks/grouped");
    return data;
  },

  getTimeAllocation: async (availableMinutes) => {
    const { data } = await axiosInstance.post("/tasks/time-allocation", {
      available_minutes: Number(availableMinutes),
    });
    return data;
  },

  toggleCompletion: async (taskId, completed) => {
    const { data } = await axiosInstance.patch(`/tasks/${taskId}/completion`, { completed });
    return data;
  },
};
