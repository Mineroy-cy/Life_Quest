import ProjectProgressBar from "../projects/ProjectProgressBar";

export default function ProgressDashboard({ projects = [] }) {
  const total = projects.length;
  const avg = total
    ? projects.reduce((sum, p) => sum + Number(p.progress_percentage || 0), 0) / total
    : 0;

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-semibold text-slate-900">Progress Dashboard</h3>
      <p className="mt-1 text-sm text-slate-600">Average progress: {avg.toFixed(1)}%</p>
      <div className="mt-4 space-y-3">
        {projects.slice(0, 4).map((project) => (
          <div key={project._id}>
            <p className="mb-1 text-xs text-slate-600">{project.name}</p>
            <ProjectProgressBar percentage={project.progress_percentage} />
          </div>
        ))}
      </div>
    </section>
  );
}
