import axios from "axios";

const AUTH_STORAGE_KEY = "lifequest.auth.session";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: {
    "Content-Type": "application/json",
  },
});

axiosInstance.interceptors.request.use((config) => {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    const token = raw ? JSON.parse(raw)?.token : "";
    if (token) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    // Ignore auth storage parse issues and continue unauthenticated.
  }
  return config;
});

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error?.response?.data?.detail;
    const detailMessage =
      typeof detail === "string"
        ? detail
        : typeof detail === "object" && detail?.message
        ? detail.message
        : undefined;

    const message =
      detailMessage ||
      error?.response?.data?.message ||
      error?.message ||
      "Unexpected network error";

    window.dispatchEvent(
      new CustomEvent("app:api-error", {
        detail: { message },
      }),
    );

    return Promise.reject(new Error(message));
  },
);

export default axiosInstance;
