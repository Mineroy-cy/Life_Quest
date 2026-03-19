import { difficultyTone, normalizeProofTypes } from "../../utils/difficultyHelpers";

export default function ChallengeCard({ challenge, actions }) {
  if (!challenge) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-5 text-sm text-slate-500">
        No challenge selected.
      </section>
    );
  }

  const proofTypes = normalizeProofTypes(challenge.proof_types).filter((p) => ["text", "image"].includes(p));

  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-display text-lg font-semibold text-slate-900">Daily Challenge</h3>
          <p className="text-sm text-slate-600">{challenge.challenge_description || challenge.description}</p>
        </div>
        <span className={`rounded-full px-2 py-1 text-xs ${difficultyTone(challenge.difficulty_applied || "medium")}`}>
          {challenge.difficulty_applied || "adaptive"}
        </span>
      </div>
      <p className="mt-3 whitespace-pre-line text-sm text-slate-700">{challenge.description}</p>
      <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
        <span className="rounded-full bg-slate-100 px-2 py-1">
          Duration: {challenge.recommended_duration_minutes || challenge.recommended_duration || 30} minute(s)
        </span>
        <span className="rounded-full bg-slate-100 px-2 py-1">Bundle Size: {challenge.bundle_size || 1}</span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {proofTypes.map((proof) => (
          <span key={proof} className="rounded-full bg-emerald-100 px-2 py-1 text-xs text-emerald-800">
            Proof: {proof}
          </span>
        ))}
      </div>
      {actions ? <div className="mt-4 flex flex-wrap gap-2">{actions}</div> : null}
    </article>
  );
}
