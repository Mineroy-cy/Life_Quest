import { useEffect, useState } from "react";
import { projectAPI } from "../../api/projectAPI";
import { toIsoDate } from "../../utils/timeUtils";

export default function ProjectEditPanel({ project, onUpdated }) {
  const [description, setDescription] = useState(project?.description || "");
  const [startDate, setStartDate] = useState(project?.start_date || toIsoDate(new Date()));
  const [deadline, setDeadline] = useState(project?.deadline || toIsoDate(new Date()));
  const [durationValue, setDurationValue] = useState(project?.duration_value ?? "");
  const [durationUnit, setDurationUnit] = useState(project?.duration_unit || "days");
  const [loadingDescription, setLoadingDescription] = useState(false);
  const [loadingTimeline, setLoadingTimeline] = useState(false);
  const [errorDescription, setErrorDescription] = useState("");
  const [errorTimeline, setErrorTimeline] = useState("");

  useEffect(() => {
    setDescription(project?.description || "");
    setStartDate(project?.start_date || toIsoDate(new Date()));
    setDeadline(project?.deadline || toIsoDate(new Date()));
    setDurationValue(project?.duration_value ?? "");
    setDurationUnit(project?.duration_unit || "days");
  }, [project]);

  const saveDescription = async () => {
    if (!project?._id) return;
    try {
      setLoadingDescription(true);
      setErrorDescription("");
      await projectAPI.updateDescription(project._id, description);
      onUpdated?.();
    } catch (err) {
      setErrorDescription(err.message);
    } finally {
      setLoadingDescription(false);
    }
  };

  const saveTimeline = async () => {
    if (!project?._id) return;
    try {
      setLoadingTimeline(true);
      setErrorTimeline("");

      const numericDuration = Number(durationValue);
      const payload = { start_date: startDate };
      if (durationValue !== "") {
        if (!Number.isFinite(numericDuration) || numericDuration <= 0) {
          throw new Error("Duration must be a positive number");
        }
        payload.duration_value = numericDuration;
        payload.duration_unit = durationUnit;
      } else {
        payload.deadline = deadline;
      }

      const updated = await projectAPI.updateTimeline(project._id, payload);
      setStartDate(updated?.start_date || startDate);
      setDeadline(updated?.deadline || deadline);
      setDurationValue(updated?.duration_value ?? durationValue);
      setDurationUnit(updated?.duration_unit || durationUnit);
      onUpdated?.();
    } catch (err) {
      setErrorTimeline(err.message);
    } finally {
      setLoadingTimeline(false);
    }
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-semibold text-slate-900">Project Edit Panel</h3>
      {errorDescription ? <p className="mt-1 text-sm text-rose-700">{errorDescription}</p> : null}
      <textarea
        className="input mt-3 min-h-24"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
      />
      <button
        onClick={saveDescription}
        disabled={loadingDescription}
        className="mt-3 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {loadingDescription ? "Updating..." : "Update Description"}
      </button>

      <div className="mt-5 border-t border-slate-200 pt-4">
        <h4 className="text-sm font-semibold text-slate-900">Timeline</h4>
        {errorTimeline ? <p className="mt-1 text-sm text-rose-700">{errorTimeline}</p> : null}
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <label className="grid gap-1 text-sm">Start Date
            <input className="input" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
          </label>
          <label className="grid gap-1 text-sm">Deadline
            <input className="input" type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
          </label>
          <label className="grid gap-1 text-sm md:col-span-2">
            Duration (optional)
            <div className="grid grid-cols-[2fr_1fr] gap-2">
              <input
                className="input"
                type="number"
                min="1"
                step="any"
                value={durationValue}
                onChange={(e) => setDurationValue(e.target.value)}
                placeholder="e.g. 90"
              />
              <select className="input" value={durationUnit} onChange={(e) => setDurationUnit(e.target.value)}>
                <option value="days">days</option>
                <option value="hours">hours</option>
                <option value="minutes">minutes</option>
              </select>
            </div>
          </label>
        </div>
        <button
          onClick={saveTimeline}
          disabled={loadingTimeline}
          className="mt-3 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {loadingTimeline ? "Saving..." : "Save Timeline"}
        </button>
      </div>
    </section>
  );
}
