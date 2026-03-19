import { useMemo, useState } from "react";
import PageContainer from "../components/layout/PageContainer";
import { useChallengeContext } from "../contexts/ChallengeContext";
import { challengeAPI } from "../api/challengeAPI";
import { obstacleAPI } from "../api/obstacleAPI";
import DailyPlanner from "../components/challenges/DailyPlanner";
import ChallengeCard from "../components/challenges/ChallengeCard";
import ChallengeTimer from "../components/challenges/ChallengeTimer";

const proofOptions = ["text", "image"];

export default function ChallengesPage() {
  const { activeChallenge, setActiveChallenge, dailyMinutes } = useChallengeContext();
  const [projectItems, setProjectItems] = useState([]);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [proofTypes, setProofTypes] = useState(["text"]);
  const [challengeDescription, setChallengeDescription] = useState("");
  const [proofInstructions, setProofInstructions] = useState("");
  const [proofScheme, setProofScheme] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(30);
  const [suggestionSkills, setSuggestionSkills] = useState({});

  const selectedItem = useMemo(
    () => projectItems.find((item) => item.project._id === selectedProjectId),
    [projectItems, selectedProjectId],
  );

  const selectedChallenge = selectedItem?.challenge || null;

  // Index of the first queue item not yet completed (used for "Up Next" badge)
  const firstPendingIndex = useMemo(
    () => projectItems.findIndex((item) => item.challenge?.status !== "completed"),
    [projectItems],
  );

  const initializeEditor = (challenge, allocatedMinutes) => {
    setProofTypes(challenge?.proof_types?.length ? challenge.proof_types : ["text"]);
    setChallengeDescription(challenge?.challenge_description || challenge?.description || "");
    setProofInstructions(challenge?.proof_instructions || "");
    setProofScheme(challenge?.proof_scheme || "");
    const recommended = Number(
      challenge?.recommended_duration_minutes || challenge?.recommended_duration || 30,
    );
    const allocated = Number(allocatedMinutes || 0);
    const status = String(challenge?.status || "pending").toLowerCase();
    const hasAcceptedState = ["active", "partial_completed", "completed", "obstacle_logged"].includes(status);

    if (hasAcceptedState) {
      setDurationMinutes(recommended > 0 ? recommended : 30);
    } else {
      setDurationMinutes(allocated > 0 ? allocated : recommended > 0 ? recommended : 30);
    }

    const map = {};
    (challenge?.pending_suggestions || []).forEach((suggestion) => {
      map[suggestion.obstacle_id] = suggestion.suggested_skill_category || "other";
    });
    setSuggestionSkills(map);
  };

  const runPlanner = async (minutes) => {
    try {
      setLoading(true);
      setError("");
      const data = await challengeAPI.getDailyPriority(minutes);
      const items = data?.items || [];

      // Keep local active challenge in sync with backend active list.
      if (
        activeChallenge &&
        !items.some(
          (item) =>
            item.challenge?._id === activeChallenge._id &&
            ["active", "partial_completed"].includes(item.challenge?.status),
        )
      ) {
        setActiveChallenge(null);
      }

      setProjectItems(items);
      const keepSelected =
        selectedProjectId && items.some((item) => item.project?._id === selectedProjectId)
          ? selectedProjectId
          : null;
      setSelectedProjectId(keepSelected);
      if (keepSelected) {
        const selected = items.find((item) => item.project?._id === keepSelected);
        if (selected?.challenge) {
          initializeEditor(selected.challenge, selected.allocated_minutes);
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const selectProject = (projectId) => {
    setSelectedProjectId(projectId);
    const item = projectItems.find((row) => row.project._id === projectId);
    if (item?.challenge) {
      initializeEditor(item.challenge, item.allocated_minutes);
    }
  };

  const toggleProofType = (value) => {
    setProofTypes((prev) => {
      if (prev.includes(value)) {
        const next = prev.filter((item) => item !== value);
        return next.length ? next : ["text"];
      }
      return [...prev, value];
    });
  };

  const acceptChallenge = async () => {
    if (!selectedChallenge?._id) return;
    try {
      setError("");

      for (const suggestion of selectedChallenge.pending_suggestions || []) {
        const skillCategory =
          suggestionSkills[suggestion.obstacle_id] ||
          suggestion.suggested_skill_category ||
          "other";
        await obstacleAPI.updateSuggestion(suggestion.obstacle_id, {
          approved: true,
          skill_category: skillCategory,
        });
      }

      const accepted = await challengeAPI.accept(selectedChallenge._id, {
        proof_types: proofTypes,
        proof_scheme: proofScheme,
        challenge_description: challengeDescription,
        proof_instructions: proofInstructions,
        recommended_duration_minutes: Number(durationMinutes),
      });

      setActiveChallenge(accepted.challenge);

      // Rebalance queue after acceptance: reserve accepted time first, then keep
      // highest-priority queued projects that still fit remaining daily budget.
      const acceptedId = accepted.challenge?._id;
      const acceptedMinutes = Number(
        accepted.challenge?.recommended_duration_minutes ||
          accepted.challenge?.recommended_duration ||
          durationMinutes ||
          0,
      );
      const totalBudget = Math.max(Number(dailyMinutes) || 0, 0);
      const remaining = Math.max(totalBudget - Math.max(acceptedMinutes, 0), 0);

      const acceptedRow = projectItems.find((item) => item.challenge?._id === acceptedId);
      const others = projectItems.filter((item) => item.challenge?._id !== acceptedId);
      const keptOthers = [];
      let used = 0;
      for (const row of others) {
        const alloc = Math.max(Number(row.allocated_minutes) || 0, 0);
        if (used + alloc <= remaining) {
          keptOthers.push(row);
          used += alloc;
        }
      }

      const nextItems = acceptedRow ? [{ ...acceptedRow, challenge: accepted.challenge }, ...keptOthers] : keptOthers;
      setProjectItems(nextItems);
      if (nextItems.length && !nextItems.some((item) => item.project._id === selectedProjectId)) {
        setSelectedProjectId(nextItems[0].project._id);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <PageContainer
      title="Challenges"
      subtitle="Plan in minutes, choose project by priority, and accept with customized proof settings."
    >
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}
      <DailyPlanner onPlan={runPlanner} />
      {loading ? (
        <p className="text-sm text-slate-600">Generating priority challenge list...</p>
      ) : null}

      {projectItems.length > 0 && (
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="font-display text-lg font-semibold text-slate-900">Today&apos;s Queue</h3>

          {activeChallenge && (
            <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Challenge in progress &mdash; complete and verify it before accepting the next one.
            </div>
          )}

          <ol className="mt-3 space-y-2">
            {projectItems.map((item, index) => {
              const isDone = item.challenge?.status === "completed";
              const isActive =
                !isDone && !!activeChallenge && item.challenge?._id === activeChallenge._id;
              const isLocked = !isDone && !isActive && !!activeChallenge;
              const isNext = !isDone && !activeChallenge && index === firstPendingIndex;
              const isSelected = selectedProjectId === item.project._id;

              const badge = isDone
                ? { label: "Done", cls: "bg-emerald-100 text-emerald-700" }
                : isActive
                  ? { label: "In Progress", cls: "bg-blue-100 text-blue-700" }
                  : isNext
                    ? { label: "Up Next", cls: "bg-sky-100 text-sky-700" }
                    : isLocked
                      ? { label: "Locked", cls: "bg-slate-100 text-slate-400" }
                      : { label: "Queued", cls: "bg-slate-100 text-slate-500" };

              return (
                <li key={item.project._id}>
                  <button
                    className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left text-sm transition ${
                      isSelected
                        ? "bg-slate-900 text-white"
                        : isLocked
                          ? "cursor-not-allowed bg-slate-50 text-slate-400"
                          : "bg-slate-50 text-slate-800 hover:bg-slate-100"
                    }`}
                    onClick={() => selectProject(item.project._id)}
                    disabled={isLocked}
                  >
                    <span
                      className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                        isSelected ? "bg-white text-slate-900" : "bg-slate-200 text-slate-700"
                      }`}
                    >
                      {index + 1}
                    </span>
                    <span className="flex-1 truncate font-medium">{item.project.name}</span>
                    <span className={`text-xs ${isSelected ? "opacity-60" : "text-slate-400"}`}>
                      P{item.project.priority}
                    </span>
                    <span className={`text-xs ${isSelected ? "opacity-60" : "text-slate-400"}`}>
                      {item.allocated_minutes}m
                    </span>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${badge.cls}`}
                    >
                      {badge.label}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        </section>
      )}

      {projectItems.length > 0 && !selectedChallenge ? (
        <section className="rounded-2xl border border-sky-200 bg-sky-50 p-4 text-sm text-sky-900 shadow-sm">
          Pick a project from Today&apos;s Queue to review and accept its challenge.
        </section>
      ) : null}

      <ChallengeCard challenge={selectedChallenge} />

      {selectedChallenge ? (
        <section className="grid gap-4 md:grid-cols-2">
          <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="font-display text-lg font-semibold text-slate-900">
              Pre-Accept Customization
            </h3>
            <label className="mt-3 block text-sm text-slate-700">Challenge Description</label>
            <textarea
              className="input mt-1 min-h-20"
              value={challengeDescription}
              onChange={(e) => setChallengeDescription(e.target.value)}
            />
            <label className="mt-3 block text-sm text-slate-700">Proof Instructions</label>
            <textarea
              className="input mt-1 min-h-20"
              value={proofInstructions}
              onChange={(e) => setProofInstructions(e.target.value)}
            />
            <label className="mt-3 block text-sm text-slate-700">Proof Evaluation Scheme</label>
            <textarea
              className="input mt-1 min-h-16"
              value={proofScheme}
              onChange={(e) => setProofScheme(e.target.value)}
            />
            <label className="mt-3 block text-sm text-slate-700">Duration (minutes)</label>
            <input
              type="number"
              min="1"
              className="input mt-1 max-w-40"
              value={durationMinutes}
              onChange={(e) => setDurationMinutes(e.target.value)}
            />
            <p className="mt-1 text-xs text-slate-500">
              Queue allocation: {selectedItem?.allocated_minutes || "-"} minute(s). You can override before accepting.
            </p>
            {selectedChallenge?.ai_suggested_duration_minutes ? (
              <p className="mt-1 text-xs text-slate-500">
                AI suggested: {selectedChallenge.ai_suggested_duration_minutes} minute(s).
              </p>
            ) : null}
            <div className="mt-3 flex flex-wrap gap-2">
              {proofOptions.map((option) => (
                <button
                  type="button"
                  key={option}
                  onClick={() => toggleProofType(option)}
                  className={`rounded-full px-3 py-1 text-sm ${
                    proofTypes.includes(option)
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-800"
                  }`}
                >
                  {option}
                </button>
              ))}
            </div>
            <button
              onClick={acceptChallenge}
              className="mt-4 rounded-lg bg-emerald-700 px-4 py-2 text-sm font-medium text-white"
            >
              Accept Challenge
            </button>
          </article>

          <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="font-display text-lg font-semibold text-slate-900">
              Skill Improvement Suggestions
            </h3>
            {(selectedChallenge.pending_suggestions || []).length === 0 ? (
              <p className="mt-2 text-sm text-slate-500">No pending obstacle suggestions.</p>
            ) : (
              <ul className="mt-3 space-y-2">
                {(selectedChallenge.pending_suggestions || []).map((suggestion) => (
                  <li key={suggestion.obstacle_id} className="rounded-xl bg-slate-100 p-3">
                    <p className="text-sm text-slate-800">{suggestion.ai_suggestion}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Obstacle: {suggestion.description || "-"}
                    </p>
                    <label className="mt-2 block text-xs text-slate-600">Skill Category</label>
                    <input
                      className="input mt-1"
                      value={suggestionSkills[suggestion.obstacle_id] || ""}
                      onChange={(e) =>
                        setSuggestionSkills((prev) => ({
                          ...prev,
                          [suggestion.obstacle_id]: e.target.value,
                        }))
                      }
                    />
                  </li>
                ))}
              </ul>
            )}
          </article>
        </section>
      ) : null}

      <ChallengeTimer endTime={activeChallenge?.countdown_end} />
    </PageContainer>
  );
}