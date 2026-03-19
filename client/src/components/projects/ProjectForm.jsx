import { useState } from "react";
import { projectAPI } from "../../api/projectAPI";
import { toIsoDate } from "../../utils/timeUtils";

const defaultForm = {
  name: "",
  description: "",
  priority: 3,
  start_date: toIsoDate(new Date()),
  deadline: toIsoDate(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)),
  difficulty_level: "medium",
  status: "active",
};

export default function ProjectForm({ onCreated }) {
  const [form, setForm] = useState(defaultForm);
  const [durationValue, setDurationValue] = useState("");
  const [durationUnit, setDurationUnit] = useState("days");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Auto-calculate deadline when duration or start_date changes
  const calcDeadline = (startDate, value, unit) => {
    const numericValue = Number(value);
    if (!startDate || !value || !Number.isFinite(numericValue) || numericValue <= 0) return null;

    const d = new Date(startDate);
    if (unit === "hours") {
      d.setHours(d.getHours() + numericValue);
    } else if (unit === "minutes") {
      d.setMinutes(d.getMinutes() + numericValue);
    } else {
      d.setDate(d.getDate() + numericValue);
    }
    return toIsoDate(d);
  };

  const handleStartDateChange = (value) => {
    const newDeadline = calcDeadline(value, durationValue, durationUnit);
    setForm((s) => ({ ...s, start_date: value, ...(newDeadline ? { deadline: newDeadline } : {}) }));
  };

  const handleDurationValueChange = (value) => {
    setDurationValue(value);
    const newDeadline = calcDeadline(form.start_date, value, durationUnit);
    if (newDeadline) setForm((s) => ({ ...s, deadline: newDeadline }));
  };

  const handleDurationUnitChange = (value) => {
    setDurationUnit(value);
    const newDeadline = calcDeadline(form.start_date, durationValue, value);
    if (newDeadline) setForm((s) => ({ ...s, deadline: newDeadline }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError("");
      await projectAPI.create({
        ...form,
        priority: Number(form.priority),
        duration_value: durationValue ? Number(durationValue) : null,
        duration_unit: durationValue ? durationUnit : null,
        progress_percentage: 0,
      });
      setForm(defaultForm);
      setDurationValue("");
      setDurationUnit("days");
      if (onCreated) onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="font-display text-lg font-semibold text-slate-900">Create Project</h2>
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <input className="input" placeholder="Name" value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} required />
      <textarea className="input min-h-24" placeholder="Description" value={form.description} onChange={(e) => setForm((s) => ({ ...s, description: e.target.value }))} required />
      <div className="grid gap-3 md:grid-cols-2">
        <label className="grid gap-1 text-sm">Priority
          <input className="input" type="number" min="1" max="5" value={form.priority} onChange={(e) => setForm((s) => ({ ...s, priority: e.target.value }))} required />
        </label>
        <label className="grid gap-1 text-sm">Difficulty
          <select className="input" value={form.difficulty_level} onChange={(e) => setForm((s) => ({ ...s, difficulty_level: e.target.value }))}>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </label>
        <label className="grid gap-1 text-sm">Start Date
          <input className="input" type="date" value={form.start_date} onChange={(e) => handleStartDateChange(e.target.value)} required />
        </label>
        <label className="grid gap-1 text-sm">
          Duration (optional)
          <div className="grid grid-cols-[2fr_1fr] gap-2">
            <input
              className="input"
              type="number"
              min="1"
              step="any"
              placeholder="e.g. 30"
              value={durationValue}
              onChange={(e) => handleDurationValueChange(e.target.value)}
            />
            <select
              className="input"
              value={durationUnit}
              onChange={(e) => handleDurationUnitChange(e.target.value)}
            >
              <option value="days">days</option>
              <option value="hours">hours</option>
              <option value="minutes">minutes</option>
            </select>
          </div>
        </label>
        <label className="grid gap-1 text-sm">Deadline
          <input className="input" type="date" value={form.deadline} onChange={(e) => setForm((s) => ({ ...s, deadline: e.target.value }))} required />
        </label>
      </div>
      {durationValue && (
        <p className="text-xs text-slate-500">
          Deadline auto-set to {form.deadline} ({durationValue} {durationUnit} from start). You can override it above.
        </p>
      )}
      <button disabled={loading} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
        {loading ? "Creating..." : "Create Project"}
      </button>
    </form>
  );
}
