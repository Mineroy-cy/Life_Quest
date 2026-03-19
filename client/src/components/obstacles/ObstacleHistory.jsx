export default function ObstacleHistory({ records = [], onApprove, onReject }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-semibold text-slate-900">Obstacle History</h3>
      <ul className="mt-3 space-y-2">
        {records.length === 0 ? (
          <li className="text-sm text-slate-500">No obstacles logged yet.</li>
        ) : (
          records.map((item) => (
            <li key={item.obstacle_id || item._id} className="rounded-xl bg-slate-100 p-3 text-sm">
              <p className="font-medium text-slate-900">{item.category || "Obstacle"}</p>
              <p className="text-slate-600">{item.description || "No details"}</p>
              {item.ai_suggestion ? <p className="mt-1 text-xs text-indigo-700">Suggestion: {item.ai_suggestion}</p> : null}
              {item.suggestion_status === "pending_approval" ? (
                <div className="mt-2 flex gap-2">
                  <button className="rounded bg-emerald-600 px-2 py-1 text-xs text-white" onClick={() => onApprove?.(item)}>
                    Approve Adaptation
                  </button>
                  <button className="rounded bg-rose-600 px-2 py-1 text-xs text-white" onClick={() => onReject?.(item)}>
                    Reject
                  </button>
                </div>
              ) : null}
            </li>
          ))
        )}
      </ul>
    </section>
  );
}
