import { useState } from "react";
import { challengeAPI } from "../../api/challengeAPI";

const options = ["text", "image", "audio", "video"];

export default function ProofSelector({ challenge, onUpdated }) {
  const [proofTypes, setProofTypes] = useState(challenge?.proof_types || ["text"]);
  const [scheme, setScheme] = useState(challenge?.proof_scheme || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  if (!challenge?._id) return null;

  const toggle = (value) => {
    setProofTypes((prev) =>
      prev.includes(value) ? prev.filter((x) => x !== value) : [...prev, value],
    );
  };

  const save = async () => {
    try {
      setSaving(true);
      setError("");
      const payload = {
        proof_types: proofTypes.length ? proofTypes : ["text"],
        proof_scheme: scheme,
      };
      await challengeAPI.updateProofConfig(challenge._id, payload);
      onUpdated?.({ ...challenge, ...payload });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-semibold text-slate-900">Proof Selector</h3>
      {error ? <p className="mt-1 text-sm text-rose-700">{error}</p> : null}
      <div className="mt-3 flex flex-wrap gap-2">
        {options.map((option) => {
          const selected = proofTypes.includes(option);
          return (
            <button
              key={option}
              type="button"
              onClick={() => toggle(option)}
              className={`rounded-full px-3 py-1 text-sm ${
                selected ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-800"
              }`}
            >
              {option}
            </button>
          );
        })}
      </div>
      <textarea
        className="input mt-3 min-h-20"
        value={scheme}
        onChange={(e) => setScheme(e.target.value)}
        placeholder="Proof grading scheme"
      />
      <button
        disabled={saving}
        type="button"
        onClick={save}
        className="mt-3 rounded-lg bg-slate-900 px-3 py-1.5 text-sm text-white disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save Proof Config"}
      </button>
    </section>
  );
}
