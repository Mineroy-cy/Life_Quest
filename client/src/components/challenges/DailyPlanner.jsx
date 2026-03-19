import { useState } from "react";
import { useChallengeContext } from "../../contexts/ChallengeContext";
import { minutesToHoursMinutes, toTotalMinutes } from "../../utils/timeUtils";

export default function DailyPlanner({ onPlan }) {
  const { dailyMinutes, setDailyMinutes } = useChallengeContext();
  const initial = minutesToHoursMinutes(dailyMinutes || 60);
  const [hours, setHours] = useState(initial.hours);
  const [minutes, setMinutes] = useState(initial.minutes);

  const submit = (e) => {
    e.preventDefault();
    const totalMinutes = Math.max(toTotalMinutes(hours, minutes), 1);
    setDailyMinutes(totalMinutes);
    if (onPlan) onPlan(totalMinutes);
  };

  return (
    <form onSubmit={submit} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-semibold text-slate-900">Daily Time Input</h3>
      <p className="mt-1 text-sm text-slate-600">Enter available hours and minutes to prioritize today.</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <input
          type="number"
          min="0"
          className="input max-w-32"
          value={hours}
          onChange={(e) => setHours(e.target.value)}
        />
        <span className="self-center text-sm text-slate-600">hr</span>
        <input
          type="number"
          min="0"
          max="59"
          className="input max-w-32"
          value={minutes}
          onChange={(e) => setMinutes(e.target.value)}
        />
        <span className="self-center text-sm text-slate-600">min</span>
        <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white">Save</button>
      </div>
    </form>
  );
}
