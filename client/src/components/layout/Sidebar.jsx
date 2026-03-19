import { useProjectContext } from "../../contexts/ProjectContext";
import { rankProjects } from "../../utils/priorityEngine";

export default function Sidebar() {
  const { projects } = useProjectContext();
  const top = rankProjects(projects).slice(0, 4);

  return (
    <aside className="space-y-4">
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <h2 className="font-display text-lg font-semibold text-slate-900">Priority Pulse</h2>
        <p className="mt-1 text-xs text-slate-500">Highest urgency projects right now.</p>
        <ul className="mt-3 space-y-2">
          {top.length === 0 && <li className="text-sm text-slate-500">No projects yet.</li>}
          {top.map((project) => (
            <li key={project._id} className="rounded-xl bg-slate-100 px-3 py-2 text-sm">
              <p className="font-medium text-slate-900">{project.name}</p>
              <p className="text-xs text-slate-600">
                Score {Math.round(project.urgencyScore)} | {project.daysLeft} day(s) left
              </p>
            </li>
          ))}
        </ul>
      </section>
    </aside>
  );
}
