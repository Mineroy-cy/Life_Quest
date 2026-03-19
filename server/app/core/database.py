from pymongo import MongoClient
from app.core.config import MONGODB_URI, DB_NAME

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]

# Collections
projects_collection = db.projects
tasks_collection = db.tasks
challenges_collection = db.challenges
evidence_collection = db.evidence
obstacles_collection = db.obstacles