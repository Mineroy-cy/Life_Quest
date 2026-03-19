import { rankProjects } from "../../utils/priorityEngine";

export default function PriorityOverview({ projects = [], dailyMinutes }) {
  const ranked = rankProjects(projects).slice(0, 5);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-semibold text-slate-900">Priority Overview</h3>
      {dailyMinutes > 0 && (
        <p className="mt-1 text-xs text-slate-500">Ranked by urgency · {dailyMinutes} min available</p>
      )}
      <ul className="mt-3 space-y-2">
        {ranked.length === 0 ? (
          <li className="text-sm text-slate-500">No project data.</li>
        ) : (
          ranked.map((project) => (
            <li key={project._id} className="flex items-center justify-between rounded-xl bg-slate-100 px-3 py-2 text-sm">
              <span className="font-medium">{project.name}</span>
              <span className="flex gap-2 text-xs text-slate-600">
                <span>{project.daysLeft}d left</span>
                <span className="capitalize text-slate-400">{project.difficulty_level || "medium"}</span>
                <span className="font-semibold text-slate-700">Score {Math.round(project.urgencyScore)}</span>
              </span>
            </li>
          ))
        )}
      </ul>
    </section>
  );
}
