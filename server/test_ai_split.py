import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from app.services.task_splitter import split_project_into_tasks

description = (
    "Competition is a web platform for personal productivity through accountability and competition. "
    "Users create weekly goals and tasks, submit proof of completion, track progress, and compete in "
    "groups via dashboards, streaks, and leaderboards. "
    "Core concept: weekly productivity cycles — users create goals, goals contain tasks, tasks require "
    "proof of completion, progress is tracked daily, statistics are calculated, week ends and moves to history. "
    "Features: Dashboard with weekly progress cards (task-based and goal-based progress), goal progress cards, "
    "weekly activity timeline (day->goal->task drill-down), daily work volume tracking, streak system. "
    "Weekly Objectives: create goals, manage tasks with proof image uploads to Cloudinary. "
    "Week completion: both manual (Complete Week button) and automatic (Monday reset). "
    "History tab: frozen snapshots of each past week with stats and proof images. "
    "Group feature: member dashboards showing each user's weekly progress, daily activity graph, "
    "leaderboard ranked by completed weeks. "
    "Database entities: Users, Goals, Tasks, WeeklyRecords, Groups, GroupMembers, LeaderboardStats."
)

print("Testing DeepSeek R1 (NVIDIA NIM) task splitting...")
print("Project: Competition (Accountability Productivity Platform)")
print("Duration: 185 days | Difficulty: hard")
print("-" * 60)

t0 = time.time()
try:
    tasks = split_project_into_tasks(
        project_name="Competition (Accountability Productivity Platform)",
        description=description,
        total_days=185,
        difficulty_level="hard",
    )
    elapsed = time.time() - t0
    print(f"SUCCESS in {elapsed:.1f}s — {len(tasks)} AI-generated tasks:\n")
    total_days_accounted = 0
    for t in tasks:
        total_days_accounted += t.get("estimated_duration", 0)
        print(f"  [{t['order']}] {t['title']}")
        print(f"       Duration: {t['estimated_duration']}d | Difficulty: {t['difficulty_level']}")
        print(f"       Proof: {t['proof_types']}")
        print(f"       Instructions: {t['proof_instructions'][:100]}")
        print()
    print(f"Total days accounted for: {total_days_accounted} / 185")
except Exception as e:
    elapsed = time.time() - t0
    print(f"FAILED after {elapsed:.1f}s: {e}")
