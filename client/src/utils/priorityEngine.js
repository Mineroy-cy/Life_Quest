export const rankProjects = (projects = []) => {
  const now = Date.now();
  const difficultyWeight = { easy: 0, medium: 10, hard: 20 };

  return [...projects]
    .map((project) => {
      const deadlineMs = new Date(project.deadline).getTime();
      const daysLeft = Math.max(Math.ceil((deadlineMs - now) / (1000 * 60 * 60 * 24)), 1);
      const progress = Number(project.progress_percentage || 0);
      const priority = Number(project.priority || 1);
      const diffScore = difficultyWeight[project.difficulty_level] ?? 0;

      const urgencyScore = priority * 30 + (100 - progress) + Math.max(30 - daysLeft, 0) * 2 + diffScore;
      return { ...project, urgencyScore, daysLeft };
    })
    .sort((a, b) => b.urgencyScore - a.urgencyScore);
};
