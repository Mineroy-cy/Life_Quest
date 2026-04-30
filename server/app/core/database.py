from pymongo import MongoClient
from app.core.config import MONGODB_URI, DB_NAME

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

# Collections
users_collection = db.users
projects_collection = db.projects
tasks_collection = db.tasks
challenges_collection = db.challenges
evidence_collection = db.evidence
obstacles_collection = db.obstacles
weekly_objectives_collection = db.weekly_objectives

# Indexes
try:
	users_collection.create_index("username_key", unique=True, name="uniq_username_key")
	users_collection.create_index("email_key", unique=True, name="uniq_email_key")
	weekly_objectives_collection.create_index([("status", 1), ("created_at", -1)], name="weekly_status_created_idx")
except Exception:
	# Keep app startup resilient even if index creation temporarily fails.
	pass