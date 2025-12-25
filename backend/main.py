from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import auth_routes, wager_routes, odds_routes, daily_routes, leaderboard_routes
from backend.scheduler import start_scheduler, shutdown_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title="CardinalCast API",
    description="Weather wager backend",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_routes.router)
app.include_router(wager_routes.router)
app.include_router(odds_routes.router)
app.include_router(daily_routes.router)
app.include_router(leaderboard_routes.router)


@app.get("/health")
def health():
    return {"status": "ok"}
