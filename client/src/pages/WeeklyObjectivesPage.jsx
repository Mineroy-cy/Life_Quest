import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import PageContainer from "../components/layout/PageContainer";
import { weeklyAPI } from "../api/weeklyAPI";

function tierStyle(tier) {
  if (tier === "critical") return "border-rose-200 bg-rose-50 text-rose-800";
  if (tier === "warning") return "border-amber-200 bg-amber-50 text-amber-800";
  return "border-emerald-200 bg-emerald-50 text-emerald-800";
}

export default function WeeklyObjectivesPage() {
  const [weekly, setWeekly] = useState(null);
  const [loading, setLoading] = useState(false);
  const [updatingChallengeKey, setUpdatingChallengeKey] = useState("");
  const [error, setError] = useState("");
  const [goalCount, setGoalCount] = useState(3);
  const [challengesPerGoal, setChallengesPerGoal] = useState(6);

  const load = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await weeklyAPI.getActive(true);
      setWeekly(data?.weekly || null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!weekly) return;
    setGoalCount(Number(weekly.goal_count) || 3);
    setChallengesPerGoal(Number(weekly.challenges_per_goal) || 6);
  }, [weekly]);

  const startWeek = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await weeklyAPI.startWeek({
        goal_count: Math.max(Number(goalCount) || 1, 1),
        challenges_per_goal: Math.max(Number(challengesPerGoal) || 1, 1),
      });
      setWeekly(data?.weekly || null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const endWeek = async () => {
    try {
      setLoading(true);
      setError("");
      await weeklyAPI.endWeek();
      setWeekly(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const refreshWeek = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await weeklyAPI.refreshWeek();
      setWeekly(data?.weekly || null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleChallengeStatus = async (goal, challenge) => {
    if (!weekly?._id) return;
    const challengeKey = `${goal.project_id}-${challenge.index}`;

    try {
      setUpdatingChallengeKey(challengeKey);
      setError("");
      const data = await weeklyAPI.updateChallengeStatus({
        week_id: weekly._id,
        project_id: goal.project_id,
        challenge_index: challenge.index,
        done: challenge.status !== "done",
      });
      if (data?.weekly) {
        setWeekly(data.weekly);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdatingChallengeKey("");
    }
  };

  return (
    <PageContainer
      title="Weekly Objectives"
      subtitle="AI-generated weekly goals from top priority projects. These six-per-goal challenges are display-only; execution remains in Challenges tab."
    >
      {error ? <p className="text-sm text-rose-700">{error}</p> : null}

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="grid gap-2 md:grid-cols-2">
          <label className="text-sm text-slate-700">
            Goals this week
            <input
              type="number"
              min="1"
              max="8"
              className="input mt-1"
              value={goalCount}
              onChange={(e) => setGoalCount(e.target.value)}
            />
          </label>
          <label className="text-sm text-slate-700">
            Display challenges per goal
            <input
              type="number"
              min="1"
              max="14"
              className="input mt-1"
              value={challengesPerGoal}
              onChange={(e) => setChallengesPerGoal(e.target.value)}
            />
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={startWeek}
            disabled={loading}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            Start Week
          </button>
          <button
            onClick={refreshWeek}
            disabled={loading || !weekly}
            className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            Refresh Week
          </button>
          <button
            onClick={endWeek}
            disabled={loading || !weekly}
            className="rounded-lg bg-rose-700 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            End Week
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Ending week clears current weekly objectives; starting week creates new 6-day display challenges per goal.
        </p>
      </section>

      {loading ? <p className="text-sm text-slate-600">Loading weekly objectives...</p> : null}

      {!loading && !weekly ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-600 shadow-sm">
          No active weekly objective set. Click Start Week to generate goals from top-priority projects.
        </section>
      ) : null}

      {weekly ? (
        <section className="space-y-4">
          <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="font-display text-lg font-semibold text-slate-900">Current Week</h3>
            <p className="mt-1 text-sm text-slate-600">
              {weekly.week_start} to {weekly.week_end} · {weekly.goal_count} goals
            </p>
          </article>

          {(weekly.goals || []).map((goal) => {
            const warn = goal.warning || {};
            return (
              <article key={goal.project_id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h3 className="font-display text-lg font-semibold text-slate-900">{goal.project_name}</h3>
                    <p className="text-xs text-slate-500">
                      P{goal.priority} · Deadline {goal.deadline} · Criteria: {goal.criteria}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/challenges?projectId=${encodeURIComponent(goal.project_id)}`}
                      className="rounded-lg border border-slate-300 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                    >
                      Work in Challenges
                    </Link>
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${tierStyle(warn.warning_tier)}`}>
                      {String(warn.warning_tier || "on_track").replace("_", " ")}
                    </span>
                  </div>
                </div>

                <div className="mt-3 grid gap-2 text-sm md:grid-cols-2">
                  <p className="rounded-lg bg-slate-100 px-3 py-2">
                    Today recommendation: <strong>{warn.recommended_today_minutes || 0} min</strong>
                    {" "}({warn.recommended_today_hours || 0} hrs)
                  </p>
                  <p className="rounded-lg bg-slate-100 px-3 py-2">
                    On-track daily: <strong>{warn.recommended_daily_minutes || 0} min</strong>
                    {" "}({warn.recommended_daily_hours || 0} hrs)
                  </p>
                  <p className="rounded-lg bg-slate-100 px-3 py-2 md:col-span-2">
                    Buffer rule: {warn.buffer_rule || "-"}
                  </p>
                </div>

                <ol className="mt-3 space-y-2">
                  {(goal.challenges || []).map((challenge) => (
                    <li
                      key={`${goal.project_id}-${challenge.index}-${challenge.source_task_id}`}
                      className="flex items-start justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2"
                    >
                      <div>
                        <p className="text-sm font-medium text-slate-900">{challenge.title}</p>
                        <p className="text-xs text-slate-600">{challenge.description || "No description"}</p>
                      </div>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          challenge.status === "done"
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-slate-200 text-slate-700"
                        }`}
                      >
                        {challenge.status === "done" ? "Done" : "Display"}
                      </span>
                      <button
                        type="button"
                        onClick={() => toggleChallengeStatus(goal, challenge)}
                        disabled={updatingChallengeKey === `${goal.project_id}-${challenge.index}`}
                        className="rounded-full bg-slate-900 px-2 py-0.5 text-xs font-medium text-white disabled:opacity-50"
                      >
                        {challenge.status === "done" ? "Mark Pending" : "Mark Done"}
                      </button>
                    </li>
                  ))}
                </ol>
              </article>
            );
          })}
        </section>
      ) : null}
    </PageContainer>
  );
}
