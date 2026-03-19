import PageContainer from "../components/layout/PageContainer";
import ProjectForm from "../components/projects/ProjectForm";
import ProjectList from "../components/projects/ProjectList";
import { useProjectContext } from "../contexts/ProjectContext";
import { projectAPI } from "../api/projectAPI";

export default function ProjectsPage() {
  const { projects, loading, error, refetch } = useProjectContext();

  const onDelete = async (project) => {
    const ok = window.confirm(`Delete project \"${project.name}\" and all related tasks/challenges?`);
    if (!ok) return;
    await projectAPI.remove(project._id);
    await refetch();
  };

  return (
    <PageContainer title="Projects" subtitle="Manage long-term goals and generated task plans.">
      <ProjectForm onCreated={refetch} />
      {loading ? <p className="text-sm text-slate-600">Loading projects...</p> : null}
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <ProjectList projects={projects} onDelete={onDelete} />
    </PageContainer>
  );
}
