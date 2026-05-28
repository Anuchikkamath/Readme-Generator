"""
FastAPI Backend Entry Point
README Generator API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.project_routes import router as project_router
from app.api.auth_routes import router as auth_router

app = FastAPI(
    title="README Generator API",
    description="API for syncing emails, managing projects, and generating README files",
    version="1.0.0",
    tags_metadata=[
        {
            "name": "authentication",
            "description": "OAuth authentication and session management.",
        },
        {
            "name": "projects",
            "description": "Operations related to project management, syncing, and README generation.",
        },
    ]
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(project_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "README Generator API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
