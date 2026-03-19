export default function EvidencePreview({ latestResult }) {
  if (!latestResult) return null;

  const status = latestResult.verification_status || "pending";
  const color = status === "approved" ? "text-emerald-700" : "text-rose-700";

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-semibold text-slate-900">Evidence Feedback</h3>
      <p className={`mt-2 text-sm ${color}`}>Verification: {status}</p>
      <p className="mt-1 text-xs text-slate-500">Evidence ID: {latestResult.evidence_id}</p>
      <p className="mt-1 text-xs text-slate-500">
        Completed Tasks: {(latestResult.completed_task_ids || []).join(", ") || "none"}
      </p>
    </section>
  );
}
