import { createContext, useContext, useEffect, useMemo, useState } from "react";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);

  const push = (message, type = "error") => {
    const id = `${Date.now()}-${Math.random()}`;
    setItems((prev) => [...prev, { id, message, type }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((item) => item.id !== id));
    }, 3500);
  };

  const value = useMemo(() => ({ push }), []);

  useEffect(() => {
    const onApiError = (event) => {
      const message = event?.detail?.message || "Unexpected network error";
      push(message, "error");
    };

    window.addEventListener("app:api-error", onApiError);
    return () => window.removeEventListener("app:api-error", onApiError);
  }, []);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-50 space-y-2">
        {items.map((item) => (
          <div
            key={item.id}
            className={`rounded-lg px-4 py-2 text-sm text-white shadow-lg ${
              item.type === "success" ? "bg-emerald-600" : "bg-rose-600"
            }`}
          >
            {item.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used inside ToastProvider");
  }
  return ctx;
}
