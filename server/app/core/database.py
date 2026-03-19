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

# Indexes
try:
	users_collection.create_index("username_key", unique=True, name="uniq_username_key")
	users_collection.create_index("email_key", unique=True, name="uniq_email_key")
except Exception:
	# Keep app startup resilient even if index creation temporarily fails.
	pass