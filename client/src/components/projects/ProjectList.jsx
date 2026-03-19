import ProjectCard from "./ProjectCard";

export default function ProjectList({ projects = [], onDelete }) {
  if (!projects.length) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
        No projects yet. Create one to begin AI task splitting.
      </section>
    );
  }

  return (
    <section className="grid gap-4">
      {projects.map((project) => (
        <ProjectCard key={project._id} project={{ ...project, onDelete }} />
      ))}
    </section>
  );
}
