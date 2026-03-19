export default function ChallengePicker({ recommended = [], onSelect }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="font-display text-lg font-semibold text-slate-900">Challenge Picker</h3>
      <p className="mt-1 text-sm text-slate-600">Suggested tasks based on your available time.</p>
      <ul className="mt-3 space-y-2">
        {recommended.length === 0 ? (
          <li className="text-sm text-slate-500">No recommendations yet.</li>
        ) : (
          recommended.map((task) => (
            <li key={task._id} className="rounded-xl bg-slate-100 p-3">
              <p className="font-medium text-slate-900">{task.title}</p>
              <p className="text-sm text-slate-600">{task.description}</p>
              <button
                className="mt-2 rounded-md bg-white px-3 py-1 text-xs text-slate-900"
                onClick={() => onSelect?.(task)}
              >
                Focus This Task
              </button>
            </li>
          ))
        )}
      </ul>
    </section>
  );
}
