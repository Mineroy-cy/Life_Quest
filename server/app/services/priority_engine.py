def rank_projects(projects: list):
    return sorted(projects, key=lambda p: p["priority"], reverse=True)