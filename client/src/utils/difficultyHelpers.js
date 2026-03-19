export const difficultyTone = (difficulty = "medium") => {
  const level = String(difficulty).toLowerCase();
  if (level === "hard") return "bg-rose-100 text-rose-800";
  if (level === "easy") return "bg-emerald-100 text-emerald-800";
  return "bg-amber-100 text-amber-900";
};

export const normalizeProofTypes = (value) => {
  if (Array.isArray(value)) return value;
  if (!value) return ["text"];
  return [String(value)];
};
