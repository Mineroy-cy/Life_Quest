import { useTimer } from "../../hooks/useTimer";

export default function ChallengeTimer({ endTime }) {
  const { formatted, isExpired, remainingMs } = useTimer(endTime);

  if (!endTime) {
    return null;
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-semibold text-slate-900">Challenge Timer</h3>
      <p className="mt-1 text-sm text-slate-600">Runs from acceptance until proof is submitted. Persists across page reloads.</p>
      <p className={`mt-3 font-mono text-4xl tracking-widest ${isExpired ? "text-rose-700" : "text-slate-900"}`}>
        {formatted}
      </p>
      {isExpired ? (
        <p className="mt-2 text-sm text-rose-700">Time window ended — submit evidence or log an obstacle.</p>
      ) : (
        <p className="mt-2 text-sm text-emerald-700">
          Stay focused. You are in active commitment mode ({Math.ceil(remainingMs / 60000)} min left).
        </p>
      )}
    </section>
  );
}
