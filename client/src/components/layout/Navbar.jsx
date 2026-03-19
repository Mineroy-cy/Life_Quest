import { NavLink } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";

const links = [
  ["/", "Dashboard"],
  ["/projects", "Projects"],
  ["/tasks", "Tasks"],
  ["/challenges", "Challenges"],
  ["/evidence", "Evidence"],
  ["/settings", "Settings"],
];

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3">
        <div>
          <p className="font-display text-xl font-semibold text-slate-900">Life Quest</p>
          <p className="text-xs text-slate-500">AI Adaptive Productivity System</p>
        </div>
        <nav className="flex flex-wrap items-center gap-1">
          {links.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `rounded-full px-3 py-1 text-sm transition ${
                  isActive
                    ? "bg-slate-900 text-white"
                    : "text-slate-700 hover:bg-slate-200"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
          {user?.username ? (
            <span className="ml-2 rounded-full bg-slate-100 px-3 py-1 text-sm text-slate-700">
              {user.username}
            </span>
          ) : null}
          <button
            type="button"
            onClick={logout}
            className="rounded-full bg-rose-100 px-3 py-1 text-sm text-rose-700 hover:bg-rose-200"
          >
            Logout
          </button>
        </nav>
      </div>
    </header>
  );
}
