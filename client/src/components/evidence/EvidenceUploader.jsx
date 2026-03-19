import { useState } from "react";
import { evidenceAPI } from "../../api/evidenceAPI";

export default function EvidenceUploader({ challenge, onSubmitted }) {
  const [proofContent, setProofContent] = useState("");
  const [uploadFile, setUploadFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!challenge?.task_id && !challenge?.task_ids?.length) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-4 text-sm text-slate-500">
        Select an active challenge to submit evidence.
      </section>
    );
  }

  const taskId = challenge.task_id || challenge.task_ids?.[0];

  const submit = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setError("");

      let content = proofContent;
      if (uploadFile) {
        // Backend currently accepts JSON proof text, so files are represented by metadata.
        content = `${proofContent}\n[File: ${uploadFile.name} | ${uploadFile.type} | ${uploadFile.size} bytes]`;
      }

      const result = await evidenceAPI.submit({
        task_id: taskId,
        completed: true,
        proof_content: content,
        challenge_id: challenge._id,
        evidence_type: challenge.proof_types || ["text"],
      });

      onSubmitted?.(result);
      setProofContent("");
      setUploadFile(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-semibold text-slate-900">Evidence Uploader</h3>
      {error ? <p className="mt-1 text-sm text-rose-700">{error}</p> : null}
      <textarea
        className="input mt-3 min-h-24"
        placeholder="Describe what you completed"
        value={proofContent}
        onChange={(e) => setProofContent(e.target.value)}
        required
      />
      <input
        className="mt-3 block w-full text-sm text-slate-600"
        type="file"
        accept="image/*,audio/*,video/*"
        onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
      />
      <button
        disabled={submitting}
        className="mt-3 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {submitting ? "Submitting..." : "Submit Evidence"}
      </button>
    </form>
  );
}
