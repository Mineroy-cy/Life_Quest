import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import PageContainer from "../components/layout/PageContainer";
import { projectAPI } from "../api/projectAPI";
import { taskAPI } from "../api/taskAPI";
import { challengeAPI } from "../api/challengeAPI";
import ProjectProgressBar from "../components/projects/ProjectProgressBar";
import TaskList from "../components/tasks/TaskList";
import ChallengeHistory from "../components/projects/ChallengeHistory";
import ProjectEditPanel from "../components/projects/ProjectEditPanel";
import { formatProjectDuration } from "../utils/timeUtils";

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [challenge, setChallenge] = useState(null);
  const [descriptionExpanded, setDescriptionExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const maxDescriptionLength = 260;
  const { detailDescription, canToggleDescription } = useMemo(() => {
    const raw = String(project?.description || "").trim();
    if (!raw) {
      return { detailDescription: "No description provided.", canToggleDescription: false };
    }
    if (raw.length <= maxDescriptionLength || descriptionExpanded) {
      return { detailDescription: raw, canToggleDescription: raw.length > maxDescriptionLength };
    }
    return {
      detailDescription: `${raw.slice(0, maxDescriptionLength).trimEnd()}...`,
      canToggleDescription: true,
    };
  }, [project?.description, descriptionExpanded]);

  const load = async () => {
    if (!projectId) return;
    try {
      setLoading(true);
      setError("");
      const [projectData, taskData, challengeData] = await Promise.all([
        projectAPI.getById(projectId),
        taskAPI.listByProject(projectId),
        challengeAPI.getDailyByProject(projectId),
      ]);
      setProject(projectData);
      setTasks(taskData || []);
      setChallenge(challengeData?.challenge || null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [projectId]);

  useEffect(() => {
    setDescriptionExpanded(false);
  }, [projectId, project?.description]);

  return (
    <PageContainer title={project?.name || "Project Detail"} subtitle="Deep view of project trajectory and adaptive task history.">
      <button
        type="button"
        onClick={() => navigate("/projects")}
        className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700"
      >
        <span aria-hidden="true">&larr;</span>
        <span>Back to Projects</span>
      </button>
      {loading ? <p className="text-sm text-slate-600">Loading project detail...</p> : null}
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      {project ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <p className="text-sm text-slate-600">{detailDescription}</p>
          {canToggleDescription ? (
            <button
              type="button"
              className="mt-1 text-xs font-medium text-slate-800 underline underline-offset-2"
              onClick={() => setDescriptionExpanded((s) => !s)}
            >
              {descriptionExpanded ? "See less" : "See more"}
            </button>
          ) : null}
          <div className="mt-2 grid gap-2 text-xs text-slate-500 md:grid-cols-4">
            <p>Start: {project.start_date}</p>
            <p>Deadline: {project.deadline}</p>
            <p>Duration: {formatProjectDuration(project)}</p>
            <p>Difficulty: {project.difficulty_level}</p>
          </div>
          <div className="mt-3">
            <ProjectProgressBar percentage={project.progress_percentage} />
          </div>
        </section>
      ) : null}
      <ProjectEditPanel project={project} onUpdated={load} />
      <ChallengeHistory challenge={challenge} />
      <TaskList tasks={tasks} />
    </PageContainer>
  );
}
