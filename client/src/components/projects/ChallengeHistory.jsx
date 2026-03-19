export default function ChallengeHistory({ challenge }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-semibold text-slate-900">Challenge History</h3>
      {!challenge ? (
        <p className="mt-2 text-sm text-slate-500">No curated challenge yet for this project today.</p>
      ) : (
        <div className="mt-2 text-sm text-slate-700">
          <p>{challenge.challenge_description || challenge.description}</p>
          <p className="mt-1 text-xs text-slate-500">Date: {challenge.daily_date || "today"}</p>
          <p className="mt-1 text-xs text-slate-500">Status: {challenge.status || "pending"}</p>
        </div>
      )}
    </section>
  );
}
