from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.project_routes import router as project_router
from app.routes.task_routes import router as task_router
from app.routes.challenge_routes import router as challenge_router
from app.routes.evidence_routes import router as evidence_router
from app.routes.obstacle_routes import router as obstacle_router

app = FastAPI(title="Life Quest Agent")

app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://localhost:5173",
		"http://127.0.0.1:5173",
		"http://localhost:5174",
		"http://127.0.0.1:5174",
	],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Register routes
app.include_router(project_router, prefix="/projects", tags=["Projects"])
app.include_router(task_router, prefix="/tasks", tags=["Tasks"])
app.include_router(challenge_router, prefix="/challenges", tags=["Challenges"])
app.include_router(evidence_router, prefix="/evidence", tags=["Evidence"])
app.include_router(obstacle_router, prefix="/obstacles", tags=["Obstacles"])