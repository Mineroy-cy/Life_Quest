import { useState } from "react";
import { obstacleAPI } from "../../api/obstacleAPI";

const categories = ["time constraint", "overwhelm", "technical issue", "skill issue"];

export default function ObstacleForm({ challenge, onLogged }) {
  const [category, setCategory] = useState(categories[0]);
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!challenge) return;

    try {
      setLoading(true);
      setError("");
      const result = await obstacleAPI.create({
        challenge_id: challenge._id,
        task_id: challenge.task_id || challenge.task_ids?.[0],
        project_id: challenge.project_id,
        category,
        description,
      });
      setDescription("");
      onLogged?.(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={submit} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-semibold text-slate-900">Obstacle Logging</h3>
      {error ? <p className="mt-1 text-sm text-rose-700">{error}</p> : null}
      <select className="input mt-3" value={category} onChange={(e) => setCategory(e.target.value)}>
        {categories.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
      <textarea
        className="input mt-3 min-h-20"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Explain what blocked completion"
        required
      />
      <button disabled={loading || !challenge} className="mt-3 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50">
        {loading ? "Logging..." : "Log Obstacle"}
      </button>
    </form>
  );
}
