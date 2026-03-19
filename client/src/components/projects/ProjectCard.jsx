import { Link } from "react-router-dom";
import { useMemo, useState } from "react";
import ProjectProgressBar from "./ProjectProgressBar";
import { formatProjectDuration } from "../../utils/timeUtils";

export default function ProjectCard({ project }) {
  const durationLabel = formatProjectDuration(project);
  const [expanded, setExpanded] = useState(false);
  const maxDescriptionLength = 160;

  const { displayDescription, shouldTruncate } = useMemo(() => {
    const raw = String(project.description || "").trim();
    if (!raw) {
      return { displayDescription: "No description provided.", shouldTruncate: false };
    }
    if (raw.length <= maxDescriptionLength) {
      return { displayDescription: raw, shouldTruncate: false };
    }
    if (expanded) {
      return { displayDescription: raw, shouldTruncate: true };
    }
    return {
      displayDescription: `${raw.slice(0, maxDescriptionLength).trimEnd()}...`,
      shouldTruncate: true,
    };
  }, [project.description, expanded]);

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-lg font-semibold text-slate-900">{project.name}</h3>
          <p className="mt-1 text-sm text-slate-600">{displayDescription}</p>
          {shouldTruncate ? (
            <button
              type="button"
              className="mt-1 text-xs font-medium text-slate-800 underline underline-offset-2"
              onClick={() => setExpanded((s) => !s)}
            >
              {expanded ? "See less" : "See more"}
            </button>
          ) : null}
        </div>
        <span className="rounded-full bg-indigo-100 px-2 py-1 text-xs text-indigo-800">
          P{project.priority}
        </span>
      </div>

      <div className="mt-3 grid gap-2 text-xs text-slate-500 md:grid-cols-3">
        <p>Deadline: {project.deadline}</p>
        <p>Duration: {durationLabel}</p>
        <p>Status: {project.status || "active"}</p>
        <p>Difficulty: {project.difficulty_level || "medium"}</p>
      </div>

      <div className="mt-4">
        <ProjectProgressBar percentage={project.progress_percentage} />
      </div>

      <div className="mt-4 flex gap-2">
        <Link
          to={`/projects/${project._id}`}
          className="rounded-lg bg-slate-900 px-3 py-1.5 text-sm text-white"
        >
          Open Details
        </Link>
        {project.onDelete ? (
          <button
            onClick={() => project.onDelete(project)}
            className="rounded-lg bg-rose-600 px-3 py-1.5 text-sm text-white"
          >
            Delete
          </button>
        ) : null}
      </div>
    </article>
  );
}
