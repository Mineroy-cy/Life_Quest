import { useEffect, useState } from "react";
import PageContainer from "../components/layout/PageContainer";
import { taskAPI } from "../api/taskAPI";

export default function TasksPage() {
  const [groups, setGroups] = useState([]);
  const [openProjectId, setOpenProjectId] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      const data = await taskAPI.groupedByProject();
      setGroups(data || []);
      if (data?.length && !openProjectId) {
        setOpenProjectId(data[0].project?._id);
      }
      setLoading(false);
    };

    load();
  }, []);

  return (
    <PageContainer title="Tasks" subtitle="AI split tasks (planning units), not commitment units.">
      {loading ? <p className="text-sm text-slate-600">Loading tasks...</p> : null}
      <section className="space-y-3">
        {groups.map((group) => {
          const isOpen = openProjectId === group.project._id;
          return (
            <article key={group.project._id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <button
                className="flex w-full items-center justify-between text-left"
                onClick={() => setOpenProjectId(isOpen ? null : group.project._id)}
              >
                <span className="font-display text-lg font-semibold text-slate-900">
                  {group.project.name}
                </span>
                <span className="text-xs text-slate-600">
                  {group.completed_count}/{group.task_count} done
                </span>
              </button>

              {isOpen ? (
                <ul className="mt-3 space-y-2">
                  {group.tasks.map((task) => (
                    <li
                      key={task._id}
                      className="rounded-xl bg-slate-100 px-3 py-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-medium text-slate-900">{task.title || "Untitled Task"}</p>
                        <span
                          className={`rounded-full px-2 py-1 text-xs ${
                            task.is_done ? "bg-emerald-200 text-emerald-800" : "bg-amber-200 text-amber-900"
                          }`}
                        >
                          {task.is_done ? "Done" : "Pending"}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-slate-600">{task.description}</p>
                    </li>
                  ))}
                </ul>
              ) : null}
            </article>
          );
        })}
      </section>
    </PageContainer>
  );
}
