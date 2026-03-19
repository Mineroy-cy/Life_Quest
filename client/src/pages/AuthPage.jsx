import { useMemo, useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const usernameRegex = /^[A-Za-z0-9_]{3,24}$/;
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validateInputs({ username, email, password, confirmPassword }, mode) {
  const user = (username || "").trim();
  const mail = (email || "").trim().toLowerCase();
  const pass = password || "";

  if (!usernameRegex.test(user)) {
    return "Username must be 3-24 chars, letters/numbers/underscore only.";
  }
  if (!emailRegex.test(mail)) {
    return "Please enter a valid email address.";
  }
  if (pass.length < 8 || pass.length > 128) {
    return "Password must be between 8 and 128 characters.";
  }
  if (mode === "register") {
    if (!/[A-Za-z]/.test(pass) || !/\d/.test(pass)) {
      return "Password must contain at least one letter and one number.";
    }
    if ((confirmPassword || "") !== pass) {
      return "Password confirmation does not match.";
    }
  }
  return "";
}

export default function AuthPage() {
  const { isAuthenticated, login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ username: "", email: "", password: "", confirmPassword: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const title = useMemo(() => (mode === "login" ? "Login" : "Create account"), [mode]);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (e) => {
    e.preventDefault();
    const validationError = validateInputs(form, mode);
    if (validationError) {
      setError(validationError);
      return;
    }

    try {
      setLoading(true);
      setError("");
      const payload = {
        username: form.username.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
        ...(mode === "register" ? { confirm_password: form.confirmPassword } : {}),
      };
      if (mode === "login") {
        await login(payload);
      } else {
        await register(payload);
      }
    } catch (err) {
      setError(err.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-app-pattern px-4 py-10 text-slate-800">
      <div className="mx-auto w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="font-display text-2xl font-semibold text-slate-900">Life Quest</h1>
        <p className="mt-1 text-sm text-slate-600">{title} with username, email, and password.</p>

        <div className="mt-4 flex rounded-xl bg-slate-100 p-1">
          <button
            type="button"
            onClick={() => setMode("login")}
            className={`w-1/2 rounded-lg px-3 py-1.5 text-sm ${
              mode === "login" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600"
            }`}
          >
            Login
          </button>
          <button
            type="button"
            onClick={() => setMode("register")}
            className={`w-1/2 rounded-lg px-3 py-1.5 text-sm ${
              mode === "register" ? "bg-white text-slate-900 shadow-sm" : "text-slate-600"
            }`}
          >
            Register
          </button>
        </div>

        <form className="mt-4 space-y-3" onSubmit={onSubmit}>
          <div>
            <label className="text-sm text-slate-700">Username</label>
            <input
              className="input mt-1"
              value={form.username}
              onChange={(e) => setForm((prev) => ({ ...prev, username: e.target.value }))}
              placeholder="your_username"
              autoComplete="username"
            />
          </div>
          <div>
            <label className="text-sm text-slate-700">Email</label>
            <input
              className="input mt-1"
              value={form.email}
              onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
              placeholder="you@example.com"
              autoComplete="email"
            />
          </div>
          <div>
            <label className="text-sm text-slate-700">Password</label>
            <input
              type="password"
              className="input mt-1"
              value={form.password}
              onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
              placeholder="********"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </div>
          {mode === "register" ? (
            <div>
              <label className="text-sm text-slate-700">Confirm Password</label>
              <input
                type="password"
                className="input mt-1"
                value={form.confirmPassword}
                onChange={(e) => setForm((prev) => ({ ...prev, confirmPassword: e.target.value }))}
                placeholder="********"
                autoComplete="new-password"
              />
            </div>
          ) : null}

          {error ? <p className="text-sm text-rose-700">{error}</p> : null}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {loading ? "Please wait..." : mode === "login" ? "Login" : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}
