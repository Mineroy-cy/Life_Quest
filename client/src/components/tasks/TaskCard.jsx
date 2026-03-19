import { difficultyTone } from "../../utils/difficultyHelpers";

export default function TaskCard({ task }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-medium text-slate-900">{task.title || "Untitled Task"}</h3>
        <span className={`rounded-full px-2 py-1 text-xs ${difficultyTone(task.difficulty_level)}`}>
          {task.difficulty_level || "medium"}
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-600">{task.description}</p>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
        <span className="rounded-full bg-slate-100 px-2 py-1">Order {task.order || "-"}</span>
        <span className="rounded-full bg-slate-100 px-2 py-1">
          Est. {task.estimated_duration || 0} unit(s)
        </span>
        <span className="rounded-full bg-slate-100 px-2 py-1">
          {task.completed || task.completion_status === "done" ? "Completed" : "Pending"}
        </span>
      </div>
    </article>
  );
}
