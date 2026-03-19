import axiosInstance from "./axiosInstance";

export const authAPI = {
  register: async (payload) => {
    const { data } = await axiosInstance.post("/auth/register", payload);
    return data;
  },

  login: async (payload) => {
    const { data } = await axiosInstance.post("/auth/login", payload);
    return data;
  },
};
