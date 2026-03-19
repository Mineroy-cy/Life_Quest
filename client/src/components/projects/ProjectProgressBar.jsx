export default function ProjectProgressBar({ percentage = 0 }) {
  const value = Math.max(0, Math.min(100, Number(percentage || 0)));

  return (
    <div className="w-full">
      <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
        <span>Progress</span>
        <span>{value.toFixed(0)}%</span>
      </div>
      <div className="h-2.5 rounded-full bg-slate-200">
        <div
          className="h-2.5 rounded-full bg-gradient-to-r from-teal-500 to-cyan-500 transition-all"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  );
}
