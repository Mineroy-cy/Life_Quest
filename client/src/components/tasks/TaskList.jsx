import TaskCard from "./TaskCard";

export default function TaskList({ tasks = [] }) {
  if (!tasks.length) {
    return (
      <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
        No tasks found for this project yet.
      </section>
    );
  }

  return (
    <section className="grid gap-3">
      {tasks.map((task) => (
        <TaskCard key={task._id} task={task} />
      ))}
    </section>
  );
}
