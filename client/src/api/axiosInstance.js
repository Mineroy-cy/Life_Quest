import axios from "axios";

const axiosInstance = axios.create({
  baseURL: "http://127.0.0.1:8000",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
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
