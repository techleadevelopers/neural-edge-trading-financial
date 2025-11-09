from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import health, data, model, backtest
from routers import regime

app = FastAPI(title="Signals API", version="0.1.0")

# CORS para frontend (localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(data.router, prefix="/data", tags=["data"])
app.include_router(model.router, prefix="/model", tags=["model"])
app.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
app.include_router(regime.router, prefix="/regime", tags=["regime"])
