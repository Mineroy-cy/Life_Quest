import { useState } from "react";
import { useProjectContext } from "../contexts/ProjectContext";
import { useChallengeContext } from "../contexts/ChallengeContext";
import { challengeAPI } from "../api/challengeAPI";
import PageContainer from "../components/layout/PageContainer";
import DailyTimeInput from "../components/dashboard/DailyTimeInput";
import ActiveChallenges from "../components/dashboard/ActiveChallenges";
import PriorityOverview from "../components/dashboard/PriorityOverview";
import ProgressDashboard from "../components/dashboard/ProgressDashboard";
import ChallengeTimer from "../components/challenges/ChallengeTimer";

export default function DashboardPage() {
  const { projects } = useProjectContext();
  const { activeChallenge, dailyMinutes } = useChallengeContext();
  const [recommendedItems, setRecommendedItems] = useState([]);

  const onPlan = async (minutes) => {
    try {
      const data = await challengeAPI.getDailyPriority(minutes);
      setRecommendedItems(data.items || []);
    } catch (_err) {
      setRecommendedItems([]);
    }
  };

  return (
    <PageContainer title="Dashboard" subtitle="Control center for planning, urgency, and challenge execution.">
      <div className="grid gap-4 md:grid-cols-2">
        <DailyTimeInput onPlan={onPlan} />
        <ActiveChallenges challenge={activeChallenge} />
      </div>
      {activeChallenge?.countdown_end && (
        <ChallengeTimer endTime={activeChallenge.countdown_end} />
      )}
      <div className="grid gap-4 md:grid-cols-2">
        <PriorityOverview projects={projects} dailyMinutes={dailyMinutes} />
        <ProgressDashboard projects={projects} />
      </div>
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <h3 className="font-display text-lg font-semibold text-slate-900">Recommended Challenges</h3>
        <p className="mt-1 text-xs text-slate-500">
          {dailyMinutes > 0 ? `Based on ${dailyMinutes} min available today.` : "Run daily planning to see recommendations."}
        </p>
        <ul className="mt-3 space-y-2">
          {recommendedItems.length === 0 ? (
            <li className="text-sm text-slate-500">Run daily planning to see recommendations.</li>
          ) : (
            recommendedItems.map((item, index) => (
              <li
                key={item.project?._id || `${item.project?.name}-${index}`}
                className="flex items-center justify-between rounded-xl bg-slate-100 px-3 py-2 text-sm"
              >
                <p className="font-medium text-slate-900">{index + 1}. {item.project?.name}</p>
                <p className="text-slate-600">
                  P{item.project?.priority ?? "-"} · {item.allocated_minutes ?? 0}m
                </p>
              </li>
            ))
          )}
        </ul>
      </section>
    </PageContainer>
  );
}
