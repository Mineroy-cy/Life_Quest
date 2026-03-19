import { useEffect, useMemo, useState } from "react";
import PageContainer from "../components/layout/PageContainer";
import { challengeAPI } from "../api/challengeAPI";
import { evidenceAPI } from "../api/evidenceAPI";
import { obstacleAPI } from "../api/obstacleAPI";
import { taskAPI } from "../api/taskAPI";
import ChallengeTimer from "../components/challenges/ChallengeTimer";
import { useChallengeContext } from "../contexts/ChallengeContext";

const obstacleCategories = ["time constraint", "overwhelm", "technical issue", "skill issue"];
const mediaMethods = new Set(["image"]);
const acceptedTypes = {
  image: "image/*",
};

const toDataUrl = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Failed to read image file"));
    reader.readAsDataURL(file);
  });

export default function EvidencePage() {
  const { setActiveChallenge } = useChallengeContext();
  const [rows, setRows] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [projectTasks, setProjectTasks] = useState([]);
  const [selectedDoneTaskIds, setSelectedDoneTaskIds] = useState([]);
  const [proofEntries, setProofEntries] = useState({});
  const [proofFiles, setProofFiles] = useState({});
  const [proofSummary, setProofSummary] = useState("");
  const [obstacleCategory, setObstacleCategory] = useState(obstacleCategories[0]);
  const [obstacleDescription, setObstacleDescription] = useState("");
  const [latestResult, setLatestResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [toggleLoading, setToggleLoading] = useState({});

  const selectedRow = useMemo(
    () => rows.find((row) => row.project._id === selectedProjectId),
    [rows, selectedProjectId],
  );
  const activeChallenge = selectedRow?.challenge || null;

  const loadRows = async () => {
    setLoading(true);
    const data = await challengeAPI.activeByProject();
    setRows(data || []);
    setLoading(false);
  };

  useEffect(() => {
    loadRows();
  }, []);

  // Auto-select first project when rows load
  useEffect(() => {
    if (!selectedProjectId && rows.length) {
      setSelectedProjectId(rows[0].project._id);
    }
  }, [rows]);

  useEffect(() => {
    const loadTasks = async () => {
      if (!activeChallenge?.project_id) {
        setProjectTasks([]);
        setSelectedDoneTaskIds([]);
        return;
      }

      const tasks = await taskAPI.listByProject(activeChallenge.project_id);
      const targetIds = new Set((activeChallenge.task_ids || [activeChallenge.task_id]).map(String));
      const filtered = (tasks || []).filter((task) => targetIds.has(String(task._id)));
      setProjectTasks(filtered);
      const alreadyDone = filtered
        .filter((task) => task.completed || task.completion_status === "done")
        .map((task) => String(task._id));
      setSelectedDoneTaskIds(alreadyDone);

      const methods = (activeChallenge.proof_types || ["text"])
        .map((m) => String(m).toLowerCase())
        .filter((m) => ["text", "image"].includes(m));
      const effectiveMethods = methods.length ? methods : ["text"];

      const entries = {};
      effectiveMethods.forEach((method) => {
        entries[method] = "";
      });
      setProofEntries(entries);
      setProofFiles({});
    };

    loadTasks();
  }, [activeChallenge?._id]);

  // Toggle task selected for submission
  const toggleTaskDone = (taskId) => {
    const id = String(taskId);
    setSelectedDoneTaskIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    );
  };

  // Manually mark/unmark a task directly via API (post-submission)
  const manualToggleTaskCompletion = async (task) => {
    const id = String(task._id);
    const newState = !(task.completed || task.completion_status === "done");
    setToggleLoading((prev) => ({ ...prev, [id]: true }));
    try {
      await taskAPI.toggleCompletion(id, newState);
      setProjectTasks((prev) =>
        prev.map((t) =>
          String(t._id) === id
            ? { ...t, completed: newState, completion_status: newState ? "done" : "pending" }
            : t,
        ),
      );
      setSelectedDoneTaskIds((prev) =>
        newState ? [...prev.filter((x) => x !== id), id] : prev.filter((x) => x !== id),
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setToggleLoading((prev) => ({ ...prev, [id]: false }));
    }
  };

  const submitEvidence = async () => {
    if (!activeChallenge?._id) return;
    try {
      setError("");
      const hasAnyTextProof =
        Object.values(proofEntries).some((value) => String(value || "").trim()) ||
        String(proofSummary || "").trim();
      const hasAnyFileProof = Object.values(proofFiles).some((files) => (files || []).length > 0);
      const hasAnyProof = hasAnyTextProof || hasAnyFileProof;
      if (!hasAnyProof) {
        setError("Provide at least one proof entry, or use 'No Evidence' and log obstacle.");
        return;
      }

      const fileMetadata = [];
      const normalizedEntries = { ...proofEntries };
      for (const [method, files] of Object.entries(proofFiles)) {
        if (!files?.length) continue;
        const lines = files.map(
          (f) => `[Uploaded ${method}: ${f.name} | ${f.type || "unknown"} | ${f.size} bytes]`,
        );
        normalizedEntries[method] = [String(normalizedEntries[method] || "").trim(), ...lines]
          .filter(Boolean)
          .join("\n");

        for (const f of files) {
          let dataUrl = "";
          if (method === "image" && (f.size || 0) <= 4 * 1024 * 1024) {
            try {
              dataUrl = await toDataUrl(f);
            } catch (_err) {
              dataUrl = "";
            }
          }

          fileMetadata.push({
            method,
            name: f.name,
            mime_type: f.type || "",
            size_bytes: f.size,
            last_modified: f.lastModified,
            ...(dataUrl ? { data_url: dataUrl } : {}),
          });
        }
      }

      const providedMethods = new Set();
      Object.entries(normalizedEntries).forEach(([method, value]) => {
        if (String(value || "").trim()) providedMethods.add(method);
      });
      if (String(proofSummary || "").trim()) {
        providedMethods.add("text");
      }

      const result = await evidenceAPI.submit({
        challenge_id: activeChallenge._id,
        task_id: activeChallenge.task_id,
        completed: true,
        proof_content: proofSummary,
        proof_entries: normalizedEntries,
        proof_files: fileMetadata,
        evidence_type: Array.from(providedMethods).filter((m) => ["text", "image"].includes(String(m).toLowerCase())),
        completed_task_ids: selectedDoneTaskIds,
      });
      setLatestResult(result);
      if (result?.task_completed) {
        setActiveChallenge(null);
      }
      setProofFiles({});
      await loadRows();
    } catch (err) {
      setError(err.message);
    }
  };

  const onMediaFilesChange = (method, list) => {
    const files = Array.from(list || []);
    setProofFiles((prev) => ({
      ...prev,
      [method]: files,
    }));
  };

  // Obstacles can always be logged — challenge or not
  const submitObstacle = async (noEvidence = false) => {
    if (noEvidence && !String(obstacleDescription || "").trim()) {
      setError("Obstacle description is required.");
      return;
    }
    if (!String(obstacleDescription || "").trim()) {
      setError("Obstacle description is required.");
      return;
    }
    try {
      setError("");
      await obstacleAPI.create({
        challenge_id: activeChallenge?._id || null,
        task_id: activeChallenge?.task_id || null,
        project_id: activeChallenge?.project_id || selectedProjectId || null,
        category: obstacleCategory,
        description: obstacleDescription,
        completed_task_ids: selectedDoneTaskIds,
      });

      if (noEvidence) {
        if (!activeChallenge?._id) {
          throw new Error("No active challenge selected for no-evidence submission.");
        }
        const result = await evidenceAPI.submit({
          challenge_id: activeChallenge._id,
          task_id: activeChallenge.task_id,
          completed: false,
          proof_content: "",
          no_evidence: true,
          evidence_type: [],
          completed_task_ids: [],
        });
        setLatestResult({
          ...result,
          verification_status: "no_evidence_obstacle_logged",
          verification_reason:
            result?.verification_reason ||
            "No evidence submitted. Obstacle was logged and the challenge was closed.",
        });
        setActiveChallenge(null);
      } else {
        setLatestResult({ verification_status: "obstacle_logged" });
      }
      setObstacleDescription("");
      await loadRows();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <PageContainer title="Evidence" subtitle="Select an active project challenge, track timer, submit proof or log obstacle.">
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-600">Loading active challenges...</p> : null}

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="font-display text-lg font-semibold text-slate-900">Active Projects with Active Challenges</h3>
        <div className="mt-3 flex flex-wrap gap-2">
          {rows.map((row) => (
            <button
              key={row.project._id}
              className={`rounded-full px-3 py-1 text-sm ${
                selectedProjectId === row.project._id
                  ? "bg-slate-900 text-white"
                  : "bg-slate-100 text-slate-800"
              }`}
              onClick={() => setSelectedProjectId(row.project._id)}
            >
              {row.project.name} (P{row.project.priority})
            </button>
          ))}
        </div>
      </section>

      {activeChallenge ? (
        <section className="grid gap-4 md:grid-cols-2">
          <article className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="font-display text-lg font-semibold text-slate-900">Challenge & Timer</h3>
            <p className="text-sm text-slate-600">{activeChallenge.challenge_description || activeChallenge.description}</p>
            <ChallengeTimer endTime={activeChallenge.countdown_end} />
          </article>

          <article className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="font-display text-lg font-semibold text-slate-900">Tasks in this Challenge</h3>
            <p className="text-xs text-slate-500">Check tasks you completed before submitting. Use the toggle button to manually mark/unmark a task at any time.</p>
            {projectTasks.length === 0 ? (
              <p className="text-sm text-slate-500">No tasks found for this challenge.</p>
            ) : (
              projectTasks.map((task) => {
                const isDone = task.completed || task.completion_status === "done";
                const id = String(task._id);
                return (
                  <div key={id} className="flex items-center justify-between gap-2 rounded-lg bg-slate-100 px-3 py-2 text-sm">
                    <label className="flex flex-1 items-center gap-2">
                      <input
                        type="checkbox"
                        checked={selectedDoneTaskIds.includes(id)}
                        onChange={() => toggleTaskDone(task._id)}
                      />
                      <span className={isDone ? "line-through text-slate-400" : ""}>{task.title || "Task"}</span>
                    </label>
                    <button
                      onClick={() => manualToggleTaskCompletion(task)}
                      disabled={toggleLoading[id]}
                      className={`rounded px-2 py-0.5 text-xs font-medium ${isDone ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}`}
                    >
                      {toggleLoading[id] ? "..." : isDone ? "Unmark" : "Mark done"}
                    </button>
                  </div>
                );
              })
            )}
          </article>
        </section>
      ) : null}

      {activeChallenge ? (
        <section className="grid gap-4 md:grid-cols-2">
          <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="font-display text-lg font-semibold text-slate-900">Evidence Submission</h3>
            <p className="mt-1 text-xs text-slate-500">
              Proof instructions: {activeChallenge.proof_instructions || "—"}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Selected proof methods: {(activeChallenge.proof_types || ["text"])
                .map((m) => String(m).toLowerCase())
                .filter((m) => ["text", "image"].includes(m))
                .join(", ") || "text"}
            </p>
            {((activeChallenge.proof_types || ["text"])
              .map((m) => String(m).toLowerCase())
              .filter((m) => ["text", "image"].includes(m)).length
              ? (activeChallenge.proof_types || ["text"])
                  .map((m) => String(m).toLowerCase())
                  .filter((m) => ["text", "image"].includes(m))
              : ["text"]).map((method) => (
              <div key={method} className="mt-3">
                <label className="text-sm text-slate-700">{method}</label>
                {mediaMethods.has(method) ? (
                  <>
                    <input
                      className="input mt-1"
                      type="file"
                      accept={acceptedTypes[method]}
                      multiple
                      onChange={(e) => onMediaFilesChange(method, e.target.files)}
                    />
                    {(proofFiles[method] || []).length > 0 ? (
                      <p className="mt-1 text-xs text-slate-500">
                        {(proofFiles[method] || []).length} file(s) selected for {method}.
                      </p>
                    ) : null}
                    <textarea
                      className="input mt-2 min-h-12"
                      value={proofEntries[method] || ""}
                      onChange={(e) =>
                        setProofEntries((prev) => ({
                          ...prev,
                          [method]: e.target.value,
                        }))
                      }
                      placeholder={`Optional ${method} notes/context`}
                    />
                  </>
                ) : (
                  <textarea
                    className="input mt-1 min-h-16"
                    value={proofEntries[method] || ""}
                    onChange={(e) =>
                      setProofEntries((prev) => ({
                        ...prev,
                        [method]: e.target.value,
                      }))
                    }
                    placeholder={`Enter ${method} proof details`}
                  />
                )}
              </div>
            ))}
            <label className="mt-3 block text-sm text-slate-700">General summary</label>
            <textarea
              className="input mt-1 min-h-16"
              value={proofSummary}
              onChange={(e) => setProofSummary(e.target.value)}
              placeholder="Optional overall completion summary"
            />
            <button
              onClick={submitEvidence}
              className="mt-3 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white"
            >
              Submit Evidence
            </button>
          </article>

          <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="font-display text-lg font-semibold text-slate-900">Log Obstacle</h3>
            <p className="mt-1 text-sm text-slate-600">
              Log an obstacle anytime — with or without evidence. Obstacles affect difficulty calibration and suggest skill improvements.
            </p>
            <select
              className="input mt-3"
              value={obstacleCategory}
              onChange={(e) => setObstacleCategory(e.target.value)}
            >
              {obstacleCategories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
            <textarea
              className="input mt-3 min-h-20"
              value={obstacleDescription}
              onChange={(e) => setObstacleDescription(e.target.value)}
              placeholder="Describe the obstacle you encountered"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                onClick={() => submitObstacle(false)}
                className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white"
              >
                Log Obstacle Only
              </button>
              <button
                onClick={() => submitObstacle(true)}
                className="rounded-lg bg-rose-700 px-4 py-2 text-sm font-medium text-white"
              >
                No Evidence - Log Obstacle
              </button>
            </div>
          </article>
        </section>
      ) : null}

      {latestResult ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm text-sm">
          <h3 className="font-display text-lg font-semibold text-slate-900">Latest Result</h3>
          <p className="mt-1 text-slate-700">
            Status:{" "}
            <span
              className={`font-medium ${
                latestResult.verification_status === "approved"
                  ? "text-emerald-700"
                  : latestResult.verification_status === "rejected"
                  ? "text-rose-700"
                  : "text-slate-600"
              }`}
            >
              {latestResult.verification_status || "unknown"}
            </span>
          </p>
          {latestResult.task_completed && (
            <p className="mt-1 text-emerald-700">
              ✓ {latestResult.completed_task_ids?.length || 0} task(s) marked as done.
            </p>
          )}
          {latestResult.verification_reason ? (
            <p className="mt-1 text-slate-700">
              Reason: {latestResult.verification_reason}
            </p>
          ) : null}
          {latestResult.progress?.progress_percentage !== undefined && (
            <p className="mt-1 text-slate-600">
              Project progress: {latestResult.progress.progress_percentage?.toFixed(1)}%
            </p>
          )}
        </section>
      ) : null}
    </PageContainer>
  );
}
